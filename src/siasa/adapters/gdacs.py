from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
from time import sleep
from typing import Callable
from urllib.request import urlopen

from .base import FetchResult, SourceAdapter


FetchText = Callable[[str], str]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]

_GDACS_NS = {"gdacs": "http://www.gdacs.org"}
_ALERT_LEVELS = {
    "green": 1.0,
    "orange": 2.0,
    "red": 3.0,
}


def _default_fetch_text(url: str) -> str:
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def _utc_now() -> datetime:
    return datetime.now(UTC)



def _retry_delay_seconds(exc: Exception, default_delay: float, now: datetime) -> float:
    code = getattr(exc, 'code', None)
    if code == 429:
        headers = getattr(exc, 'headers', None)
        if headers is not None:
            retry_after = headers.get('Retry-After') if hasattr(headers, 'get') else None
            if retry_after is not None:
                try:
                    return max(default_delay, float(retry_after))
                except (TypeError, ValueError):
                    try:
                        retry_at = parsedate_to_datetime(str(retry_after))
                    except (TypeError, ValueError, IndexError, OverflowError):
                        return default_delay
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=UTC)
                    seconds_until_retry = max(0.0, (retry_at - now).total_seconds())
                    return max(default_delay, seconds_until_retry)
    return default_delay


@dataclass
class GDACSAdapter(SourceAdapter):
    country_ids: set[str] | None = None
    source_id: str = "SRC-GDACS"
    domain: str = "B"
    rss_url: str = "https://www.gdacs.org/xml/rss.xml"
    fetch_text: FetchText = _default_fetch_text
    now_provider: NowProvider = _utc_now
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    retry_sleep: SleepFn = sleep
    # AP-30.1 (SwR-097): optional historical window via the GDACS archive feed; None -> live path unchanged.
    date_window: tuple[datetime, datetime] | None = None
    archive_url: str = "https://www.gdacs.org/rss.aspx"

    def fetch(self) -> FetchResult:
        try:
            payload = self._fetch_with_retry(self._resolve_url())
            records = self._parse_payload(payload)
            diagnostics = f"gdacs_fetch_ok countries={len(records)} records={len(records)}"
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except Exception as exc:
            return FetchResult(records=[], diagnostics=f"gdacs_fetch_failed: {exc}", is_success=False)

    def _resolve_url(self) -> str:
        if self.date_window is None:
            return self.rss_url
        start, end = self.date_window
        return (
            f"{self.archive_url}?profile=ARCHIVE&fromarchive=true"
            f"&from={start.strftime('%Y-%m-%d')}&to={end.strftime('%Y-%m-%d')}"
        )

    def _fetch_with_retry(self, url: str) -> str:
        if self.max_retries < 0:
            raise ValueError("GDACS adapter max_retries must be >= 0")
        if self.retry_backoff_seconds < 0:
            raise ValueError("GDACS adapter retry_backoff_seconds must be >= 0")

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_text(url)
            except Exception as exc:  # noqa: BLE001 - adapter should return failed FetchResult, not crash caller
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

    def _parse_payload(self, payload: str) -> list[dict[str, object]]:
        root = ET.fromstring(payload)
        channel = root.find("channel")
        if channel is None:
            raise ValueError("GDACS RSS payload must contain channel")

        selected: dict[str, tuple[float, datetime]] = {}
        now = self.now_provider()
        for item in channel.findall("item"):
            country_id = (item.findtext("gdacs:iso3", default="", namespaces=_GDACS_NS) or "").strip().upper()
            if not country_id:
                continue
            if self.country_ids is not None and country_id not in self.country_ids:
                continue
            is_current = (item.findtext("gdacs:iscurrent", default="true", namespaces=_GDACS_NS) or "true").strip().lower()
            if is_current != "true":
                continue
            alert_level_name = (item.findtext("gdacs:alertlevel", default="", namespaces=_GDACS_NS) or "").strip().lower()
            alert_level = _ALERT_LEVELS.get(alert_level_name)
            if alert_level is None:
                continue
            added_text = (item.findtext("gdacs:dateadded", default="", namespaces=_GDACS_NS) or item.findtext("pubDate", default="") or "").strip()
            if not added_text:
                raise ValueError("GDACS RSS items require gdacs:dateadded or pubDate")
            added_at = parsedate_to_datetime(added_text)
            if added_at.tzinfo is None:
                added_at = added_at.replace(tzinfo=UTC)
            else:
                added_at = added_at.astimezone(UTC)

            previous = selected.get(country_id)
            if previous is None or alert_level > previous[0] or (alert_level == previous[0] and added_at > previous[1]):
                selected[country_id] = (alert_level, added_at)

        records: list[dict[str, object]] = []
        for country_id in sorted(selected):
            value, added_at = selected[country_id]
            freshness_hours = max(0, int((now - added_at).total_seconds() // 3600))
            records.append(
                {
                    "country_id": country_id,
                    "timestamp": added_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "signal_key": "disaster_alert_level",
                    "value": value,
                    "expected_source_count": 1,
                    "freshness_hours": freshness_hours,
                    "quality_flag": "gdacs_rss",
                }
            )
        return records
