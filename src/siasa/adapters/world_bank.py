from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import json
from time import sleep
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import urlopen

from .base import FetchResult, SourceAdapter


FetchJson = Callable[[str], object]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]


def _default_fetch_json(url: str) -> object:
    with urlopen(url, timeout=30) as response:
        return json.load(response)


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
class WorldBankIndicatorsAdapter(SourceAdapter):
    country_ids: tuple[str, ...]
    source_id: str = "WB-INDICATORS"
    domain: str = "D"
    base_url: str = "https://api.worldbank.org/v2/country"
    per_page: int = 1000
    mrv: int = 1
    annual_freshness_hours: int = 8760
    fetch_json: FetchJson = _default_fetch_json
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    indicators: dict[str, str] = field(
        default_factory=lambda: {
            "NY.GDP.MKTP.KD.ZG": "gdp_growth",
            "NE.EXP.GNFS.KD.ZG": "trade_volume_change",
        }
    )

    def fetch(self) -> FetchResult:
        try:
            records: list[dict[str, Any]] = []
            for indicator_id, signal_key in self.indicators.items():
                url = self._build_url(indicator_id)
                payload = self._fetch_with_retry(url)
                records.extend(self._parse_payload(payload, signal_key))
            diagnostics = (
                f"world_bank_fetch_ok countries={len(self.country_ids)} "
                f"indicators={len(self.indicators)} records={len(records)}"
            )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except (RuntimeError, ValueError, KeyError, TypeError, URLError) as exc:
            return FetchResult(records=[], diagnostics=f"world_bank_fetch_failed: {exc}", is_success=False)

    def _fetch_with_retry(self, url: str) -> object:
        if self.max_retries < 0:
            raise ValueError("World Bank adapter max_retries must be >= 0")
        if self.retry_backoff_seconds < 0:
            raise ValueError("World Bank adapter retry_backoff_seconds must be >= 0")

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_json(url)
            except Exception as exc:  # noqa: BLE001 - adapter should return failed FetchResult, not crash caller
                last_error = exc
                if attempt == self.max_retries:
                    break
                retry_delay = _retry_delay_seconds(
                    exc,
                    self.retry_backoff_seconds * (2**attempt),
                    self.now_provider(),
                )
                self.retry_sleep(retry_delay)
        assert last_error is not None
        raise last_error

    def _build_url(self, indicator_id: str) -> str:
        countries = ";".join(self.country_ids)
        return (
            f"{self.base_url}/{countries}/indicator/{indicator_id}"
            f"?format=json&per_page={self.per_page}&mrv={self.mrv}"
        )

    def _parse_payload(self, payload: object, signal_key: str) -> list[dict[str, Any]]:
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            raise ValueError("World Bank payload must be a two-element list with a data array")

        records: list[dict[str, Any]] = []
        for row in payload[1]:
            if not isinstance(row, dict):
                raise ValueError("World Bank data rows must be objects")
            value = row.get("value")
            if value is None:
                continue
            country = row.get("country") or {}
            country_id = str(row.get("countryiso3code") or country.get("id") or "").strip().upper()
            period = str(row.get("date") or "").strip()
            if not country_id or not period:
                raise ValueError("World Bank rows require country.id/countryiso3code and date")
            records.append(
                {
                    "country_id": country_id,
                    "period": period,
                    "signal_key": signal_key,
                    "value": float(value),
                    "expected_source_count": 1,
                    "freshness_hours": self.annual_freshness_hours,
                    "quality_flag": "world_bank_api",
                }
            )
        return records
