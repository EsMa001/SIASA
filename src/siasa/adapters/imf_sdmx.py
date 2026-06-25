"""IMF DataMapper adapter — macroeconomic signals for Domain D.

Source: https://www.imf.org/external/datamapper/api/v1/
Free, no auth. JSON format.
Fetches CPI inflation (PCPIPCH), GDP growth (NGDP_RPCH),
and current account balance (BCA_NGDPD).

Traceability: SwR-076, AP-15.1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import sleep
from typing import Any, Callable
import json
from urllib.request import Request, urlopen

from .base import FetchResult, SourceAdapter


FetchJson = Callable[[str], object]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]

_BASE_URL = "https://www.imf.org/external/datamapper/api/v1"

# IMF DataMapper indicators → signal keys
_INDICATORS: dict[str, str] = {
    "PCPIPCH": "imf_cpi_inflation_pct",
    "NGDP_RPCH": "imf_gdp_growth_pct",
    "BCA_NGDPD": "imf_current_account_pct_gdp",
}


def _parse_datamapper_response(
    payload: object,
    indicator: str,
) -> list[dict[str, Any]]:
    """Extract latest values from IMF DataMapper JSON response.

    DataMapper format:
      {"values": {"INDICATOR": {"ISO3": {"YEAR": value, ...}, ...}}}

    Returns list of dicts with keys: country_id, year, value.
    """
    if not isinstance(payload, dict):
        return []

    values = payload.get("values")
    if not isinstance(values, dict):
        return []

    indicator_data = values.get(indicator)
    if not isinstance(indicator_data, dict):
        return []

    results: list[dict[str, Any]] = []

    for country_code, year_values in indicator_data.items():
        if not isinstance(year_values, dict) or not year_values:
            continue

        # Find the latest year with a non-null numeric value
        latest_year: str | None = None
        latest_value: float | None = None

        for year_str, val in sorted(year_values.items(), reverse=True):
            if val is not None and isinstance(val, (int, float)):
                latest_year = year_str
                latest_value = float(val)
                break

        if latest_year is not None and latest_value is not None:
            results.append({
                "country_id": country_code,
                "year": latest_year,
                "value": latest_value,
            })

    return results


def _default_fetch_json(url: str) -> object:
    req = Request(url, headers={
        "User-Agent": "SIASA/1.0",
        "Accept": "application/json",
    })
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class IMFDataMapperAdapter(SourceAdapter):
    """Fetch CPI inflation, GDP growth, and current account from IMF DataMapper.

    Produces three signal types per country:
    - imf_cpi_inflation_pct: Consumer Price Index inflation (% change)
    - imf_gdp_growth_pct: Real GDP growth (% change)
    - imf_current_account_pct_gdp: Current account balance (% of GDP)
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-IMF-DATAMAPPER"
    domain: str = "D"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    freshness_hours: int = 720  # IMF updates ~monthly, 30 days

    def fetch(self) -> FetchResult:
        """Fetch macro indicators for configured countries."""
        if not self.country_ids:
            return FetchResult(
                records=[],
                diagnostics="imf_no_countries_configured",
                is_success=True,
            )

        all_records: list[dict[str, Any]] = []
        errors: list[str] = []

        for indicator, signal_key in _INDICATORS.items():
            try:
                records = self._fetch_indicator(indicator, signal_key)
                all_records.extend(records)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{indicator}:{exc}")

        if errors and not all_records:
            return FetchResult(
                records=[],
                diagnostics=f"imf_fetch_failed: {'; '.join(errors)}",
                is_success=False,
            )

        diagnostics = (
            f"imf_fetch_ok countries={len(self.country_ids)} "
            f"records={len(all_records)}"
        )
        if errors:
            diagnostics += f" partial_errors={len(errors)}"

        return FetchResult(
            records=all_records,
            diagnostics=diagnostics,
            is_success=True,
        )

    def _fetch_indicator(
        self,
        indicator: str,
        signal_key: str,
    ) -> list[dict[str, Any]]:
        """Fetch a single IMF indicator for all configured countries."""
        # Build URL with country codes
        countries_param = "+".join(sorted(self.country_ids))
        url = f"{_BASE_URL}/{indicator}/{countries_param}"

        payload = self._fetch_with_retry(url)
        parsed = _parse_datamapper_response(payload, indicator)

        # Filter to configured countries only
        configured_set = set(self.country_ids)
        records: list[dict[str, Any]] = []

        for item in parsed:
            country_id = item["country_id"]
            if country_id not in configured_set:
                continue
            records.append(self._make_record(
                country_id=country_id,
                signal_key=signal_key,
                value=item["value"],
                period=item["year"],
            ))

        return records

    def _make_record(
        self,
        country_id: str,
        signal_key: str,
        value: float,
        period: str,
    ) -> dict[str, Any]:
        return {
            "country_id": country_id,
            "period": period,
            "signal_key": signal_key,
            "value": value,
            "quality_flag": "imf_datamapper_api",
            "freshness_hours": self.freshness_hours,
            "freshness_horizon_hours": self.freshness_hours,
            "expected_source_count": 1,
        }

    def _fetch_with_retry(self, url: str) -> object:
        """Fetch URL with exponential backoff retry."""
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_json(url)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == self.max_retries:
                    break
                delay = min(
                    self.retry_backoff_seconds * (2 ** attempt),
                    self.max_retry_delay_seconds,
                )
                self.retry_sleep(delay)
        assert last_error is not None
        raise last_error
