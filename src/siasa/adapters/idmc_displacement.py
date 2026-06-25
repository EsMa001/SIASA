"""IDMC Internal Displacement adapter — displacement signals for Domain C.

Source: https://api.idmcdb.org/api/displacement_data
Free, no auth. JSON list format.
Fetches new displacements by conflict and disaster.

Traceability: SwR-078
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

_BASE_URL = "https://api.idmcdb.org/api/displacement_data"


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
class IDMCDisplacementAdapter(SourceAdapter):
    """Fetch internal displacement data from IDMC API.

    Produces two signal types:
    - idmc_new_displacements_conflict: New displacements due to conflict
    - idmc_new_displacements_disaster: New displacements due to disaster
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-IDMC"
    domain: str = "C"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    freshness_hours: int = 720  # monthly data

    def fetch(self) -> FetchResult:
        """Fetch displacement data for configured countries."""
        if not self.country_ids:
            return FetchResult(
                records=[],
                diagnostics="idmc_no_countries_configured",
                is_success=True,
            )

        all_records: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            url = _BASE_URL
            payload = self._fetch_with_retry(url)
            records = self._parse_displacement_data(payload)
            all_records.extend(records)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"displacement:{exc}")

        if errors and not all_records:
            return FetchResult(
                records=[],
                diagnostics=f"idmc_fetch_failed: {'; '.join(errors)}",
                is_success=False,
            )

        diagnostics = (
            f"idmc_fetch_ok countries={len(self.country_ids)} "
            f"records={len(all_records)}"
        )
        if errors:
            diagnostics += f" partial_errors={len(errors)}"

        return FetchResult(
            records=all_records,
            diagnostics=diagnostics,
            is_success=True,
        )

    def _parse_displacement_data(self, payload: object) -> list[dict[str, Any]]:
        """Parse IDMC displacement JSON response."""
        if not isinstance(payload, list):
            return []

        country_set = set(self.country_ids)
        records: list[dict[str, Any]] = []

        for entry in payload:
            if not isinstance(entry, dict):
                continue

            iso3 = entry.get("iso3", "")
            if iso3 not in country_set:
                continue

            year = entry.get("year")
            period = str(year) if year is not None else ""

            conflict_val = entry.get("conflict_new_displacements")
            if conflict_val is not None:
                records.append(self._make_record(
                    country_id=iso3,
                    signal_key="idmc_new_displacements_conflict",
                    value=float(conflict_val),
                    period=period,
                ))

            disaster_val = entry.get("disaster_new_displacements")
            if disaster_val is not None:
                records.append(self._make_record(
                    country_id=iso3,
                    signal_key="idmc_new_displacements_disaster",
                    value=float(disaster_val),
                    period=period,
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
            "quality_flag": "idmc_api",
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
