"""HDX HAPI adapter — humanitarian data signals for Domain B.

Source: https://hapi.humdata.org/api/v2/
Free, requires app_identifier query param. OData-like JSON.
Fetches conflict events, humanitarian needs, and funding coverage.

Traceability: SwR-083
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

_BASE_URL = "https://hapi.humdata.org/api/v2"
_APP_IDENTIFIER = "siasa"


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
class HDXHAPIAdapter(SourceAdapter):
    """Fetch humanitarian data from HDX HAPI.

    Produces three signal types:
    - hdx_hapi_conflict_events: Number of conflict events
    - hdx_hapi_humanitarian_needs: Humanitarian needs indicator value
    - hdx_hapi_funding_coverage: Funding coverage percentage
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-HDX-HAPI"
    domain: str = "B"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    freshness_hours: int = 168  # weekly data

    def fetch(self) -> FetchResult:
        """Fetch humanitarian data for configured countries."""
        if not self.country_ids:
            return FetchResult(
                records=[],
                diagnostics="hdx_hapi_no_countries_configured",
                is_success=True,
            )

        all_records: list[dict[str, Any]] = []
        errors: list[str] = []

        # 1. Fetch conflict events
        try:
            records = self._fetch_conflict_events()
            all_records.extend(records)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"conflict_events:{exc}")

        # 2. Fetch humanitarian needs
        try:
            records = self._fetch_humanitarian_needs()
            all_records.extend(records)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"humanitarian_needs:{exc}")

        # 3. Fetch funding coverage
        try:
            records = self._fetch_funding()
            all_records.extend(records)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"funding:{exc}")

        if errors and not all_records:
            return FetchResult(
                records=[],
                diagnostics=f"hdx_hapi_fetch_failed: {'; '.join(errors)}",
                is_success=False,
            )

        diagnostics = (
            f"hdx_hapi_fetch_ok countries={len(self.country_ids)} "
            f"records={len(all_records)}"
        )
        if errors:
            diagnostics += f" partial_errors={len(errors)}"

        return FetchResult(
            records=all_records,
            diagnostics=diagnostics,
            is_success=True,
        )

    def _build_url(self, endpoint: str, location_code: str) -> str:
        """Build HAPI URL with app_identifier and location filter."""
        return (
            f"{_BASE_URL}/{endpoint}"
            f"?app_identifier={_APP_IDENTIFIER}"
            f"&location_code={location_code}"
        )

    def _extract_odata_values(self, payload: object) -> list[dict[str, Any]]:
        """Extract values from OData-like JSON response."""
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if isinstance(data, list):
            return data
        # Also try 'value' key (OData standard)
        value = payload.get("value")
        if isinstance(value, list):
            return value
        return []

    def _fetch_conflict_events(self) -> list[dict[str, Any]]:
        """Fetch conflict event counts per country."""
        records: list[dict[str, Any]] = []
        now_str = self.now_provider().strftime("%Y-%m-%d")

        for iso3 in sorted(self.country_ids):
            url = self._build_url("coordination-context/conflict-event", iso3)
            payload = self._fetch_with_retry(url)
            entries = self._extract_odata_values(payload)
            event_count = len(entries)

            records.append(self._make_record(
                country_id=iso3,
                signal_key="hdx_hapi_conflict_events",
                value=float(event_count),
                period=now_str,
            ))

        return records

    def _fetch_humanitarian_needs(self) -> list[dict[str, Any]]:
        """Fetch humanitarian needs data per country."""
        records: list[dict[str, Any]] = []
        now_str = self.now_provider().strftime("%Y-%m-%d")

        for iso3 in sorted(self.country_ids):
            url = self._build_url("affected-people/humanitarian-needs", iso3)
            payload = self._fetch_with_retry(url)
            entries = self._extract_odata_values(payload)

            total_in_need = 0.0
            for entry in entries:
                if isinstance(entry, dict):
                    val = entry.get("population_in_need")
                    if val is not None:
                        total_in_need += float(val)

            records.append(self._make_record(
                country_id=iso3,
                signal_key="hdx_hapi_humanitarian_needs",
                value=total_in_need,
                period=now_str,
            ))

        return records

    def _fetch_funding(self) -> list[dict[str, Any]]:
        """Fetch funding coverage data per country."""
        records: list[dict[str, Any]] = []
        now_str = self.now_provider().strftime("%Y-%m-%d")

        for iso3 in sorted(self.country_ids):
            url = self._build_url("coordination-context/funding", iso3)
            payload = self._fetch_with_retry(url)
            entries = self._extract_odata_values(payload)

            coverage = 0.0
            for entry in entries:
                if isinstance(entry, dict):
                    requirements = entry.get("requirements_usd")
                    funding = entry.get("funding_usd")
                    if requirements and funding and float(requirements) > 0:
                        coverage = float(funding) / float(requirements) * 100.0
                        break  # use first valid entry

            records.append(self._make_record(
                country_id=iso3,
                signal_key="hdx_hapi_funding_coverage",
                value=coverage,
                period=now_str,
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
            "quality_flag": "hdx_hapi_api",
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
