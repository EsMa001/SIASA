from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import io
import zipfile
from time import sleep
from typing import Callable
from urllib.request import urlopen

from .base import FetchResult, SourceAdapter
from .retry_utils import _retry_delay_seconds, is_retryable_error


FetchText = Callable[[str], str]
FetchBytes = Callable[[str], bytes]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]


def _default_fetch_text(url: str, timeout_seconds: float = 30.0) -> str:
    with urlopen(url, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8")


def _default_fetch_bytes(url: str, timeout_seconds: float = 30.0) -> bytes:
    with urlopen(url, timeout=timeout_seconds) as response:
        return response.read()


def _utc_now() -> datetime:
    return datetime.now(UTC)



@dataclass
class GDELTEventsAdapter(SourceAdapter):
    country_codes: dict[str, str]
    source_id: str = "SRC-GDELT-EVENTS"
    domain: str = "B"
    lastupdate_url: str = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    request_timeout_seconds: float = 30.0
    fetch_text: FetchText = _default_fetch_text
    fetch_bytes: FetchBytes = _default_fetch_bytes
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    recent_export_count: int = 1
    export_interval_minutes: int = 15

    def fetch(self) -> FetchResult:
        try:
            export_urls = self._discover_recent_export_urls()
            archive_bytes_list, degraded_exports = self._fetch_recent_archives(export_urls)
            records = self._build_records_from_exports(archive_bytes_list)
            diagnostics = (
                f"gdelt_events_fetch_ok countries={len(self.country_codes)} "
                f"exports={len(archive_bytes_list)} records={len(records)}"
            )
            if degraded_exports:
                diagnostics = (
                    f"{diagnostics} degraded_exports={len(degraded_exports)} "
                    f"degraded_reasons={' | '.join(str(reason) for reason in degraded_exports)}"
                )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except Exception as exc:
            return FetchResult(records=[], diagnostics=f"gdelt_events_fetch_failed: {exc}", is_success=False)

    def _discover_latest_export_url(self) -> str:
        payload = self.fetch_text(self.lastupdate_url)
        for line in payload.splitlines():
            parts = line.strip().split()
            if parts and parts[-1].endswith('.export.CSV.zip'):
                return parts[-1]
        raise ValueError("No export zip URL found in GDELT lastupdate feed")

    def _discover_recent_export_urls(self) -> list[str]:
        latest_export_url = self._discover_latest_export_url()
        return self._recent_export_urls_from_latest(latest_export_url)

    def _recent_export_urls_from_latest(self, latest_export_url: str) -> list[str]:
        if self.recent_export_count <= 0:
            raise ValueError("GDELT events adapter recent_export_count must be >= 1")
        if self.export_interval_minutes <= 0:
            raise ValueError("GDELT events adapter export_interval_minutes must be >= 1")
        if not latest_export_url.endswith('.export.CSV.zip'):
            raise ValueError("Latest GDELT export URL must end with .export.CSV.zip")

        stem = latest_export_url.rsplit('/', 1)[-1].removesuffix('.export.CSV.zip')
        latest_timestamp = datetime.strptime(stem, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        prefix = latest_export_url[: -len(stem + '.export.CSV.zip')]

        return [
            f"{prefix}{(latest_timestamp - timedelta(minutes=self.export_interval_minutes * offset)).strftime('%Y%m%d%H%M%S')}.export.CSV.zip"
            for offset in range(self.recent_export_count)
        ]

    def _fetch_bytes_with_retry(self, url: str) -> bytes:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_bytes(url)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == self.max_retries:
                    break
                retry_delay = _retry_delay_seconds(
                    exc,
                    self.retry_backoff_seconds * (2**attempt),
                    self.now_provider(),
                )
                retry_delay = min(retry_delay, self.max_retry_delay_seconds)
                self.retry_sleep(retry_delay)
        assert last_error is not None
        raise last_error

    def _fetch_recent_archives(self, export_urls: list[str]) -> tuple[list[bytes], list[str]]:
        archives: list[bytes] = []
        degraded_exports: list[str] = []
        for index, export_url in enumerate(export_urls):
            try:
                archives.append(self._fetch_bytes_with_retry(export_url))
            except Exception as exc:  # noqa: BLE001 - degraded recent-window fetches should not discard usable archives
                if index == 0:
                    raise
                degraded_exports.append(f"{export_url}: {exc}")
                continue
        if not archives:
            raise ValueError("No GDELT event exports could be fetched")
        return archives, degraded_exports

    def _build_records_from_exports(self, archives: list[bytes]) -> list[dict[str, object]]:
        counts: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        latest_seen: dict[str, datetime] = {}

        for archive_bytes in archives:
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
                name = archive.namelist()[0]
                with archive.open(name) as handle:
                    for raw_line in handle:
                        columns = raw_line.decode('utf-8', errors='replace').rstrip('\n').split('\t')
                        if len(columns) < 60:
                            continue
                        country_id = self._resolve_country(columns[53])
                        if country_id is None:
                            continue
                        event_root_code = columns[28]
                        quad_class = columns[29]
                        seen_at = datetime.strptime(columns[59], "%Y%m%d%H%M%S").replace(tzinfo=UTC)
                        latest_seen[country_id] = max(seen_at, latest_seen.get(country_id, seen_at))

                        if quad_class in {"3", "4"} and event_root_code != "14":
                            counts[country_id]["conflict_event_count"] += 1.0
                        if event_root_code == "14":
                            counts[country_id]["protest_event_count"] += 1.0
                        if quad_class == "4":
                            counts[country_id]["violent_event_count"] += 1.0

        now = self.now_provider()
        records: list[dict[str, object]] = []
        for country_id in sorted(counts):
            timestamp = latest_seen[country_id].strftime("%Y-%m-%dT%H:%M:%SZ")
            freshness_hours = max(0, int((now - latest_seen[country_id]).total_seconds() // 3600))
            for signal_key in ("conflict_event_count", "protest_event_count", "violent_event_count"):
                value = counts[country_id].get(signal_key, 0.0)
                if value <= 0:
                    continue
                records.append(
                    {
                        "country_id": country_id,
                        "timestamp": timestamp,
                        "signal_key": signal_key,
                        "value": value,
                        "expected_source_count": 1,
                        "freshness_hours": freshness_hours,
                        "quality_flag": "gdelt_events_export",
                    }
                )
        return records

    def _resolve_country(self, action_geo_country_code: str) -> str | None:
        for iso3, gdelt_code in self.country_codes.items():
            if gdelt_code == action_geo_country_code:
                return iso3
        return None
