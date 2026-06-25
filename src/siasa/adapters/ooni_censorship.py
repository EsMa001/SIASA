"""OONI Censorship adapter — censorship signals for Domain E.

Source: https://api.ooni.io/api/v1/aggregation
Free, no auth. JSON format.
Fetches web censorship measurement aggregations by country.

Traceability: SwR-080
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

_BASE_URL = "https://api.ooni.io/api/v1/aggregation"


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
class OONICensorshipAdapter(SourceAdapter):
    """Fetch censorship measurement aggregations from OONI API.

    Produces two signal types:
    - ooni_blocked_site_count: Number of confirmed blocked sites
    - ooni_censorship_incident_count: Number of anomalous measurements
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-OONI"
    domain: str = "E"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    freshness_hours: int = 48

    def fetch(self) -> FetchResult:
        """Fetch censorship data for configured countries."""
        if not self.country_ids:
            return FetchResult(
                records=[],
                diagnostics="ooni_no_countries_configured",
                is_success=True,
            )

        all_records: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            url = _BASE_URL
            payload = self._fetch_with_retry(url)
            records = self._parse_aggregation(payload)
            all_records.extend(records)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"aggregation:{exc}")

        if errors and not all_records:
            return FetchResult(
                records=[],
                diagnostics=f"ooni_fetch_failed: {'; '.join(errors)}",
                is_success=False,
            )

        diagnostics = (
            f"ooni_fetch_ok countries={len(self.country_ids)} "
            f"records={len(all_records)}"
        )
        if errors:
            diagnostics += f" partial_errors={len(errors)}"

        return FetchResult(
            records=all_records,
            diagnostics=diagnostics,
            is_success=True,
        )

    def _parse_aggregation(self, payload: object) -> list[dict[str, Any]]:
        """Parse OONI aggregation JSON response."""
        if not isinstance(payload, dict):
            return []

        result = payload.get("result")
        if not isinstance(result, list):
            return []

        country_set = set(self.country_ids)
        # Aggregate per country: map iso2 probe_cc to records
        country_data: dict[str, dict[str, float]] = {}

        for entry in result:
            if not isinstance(entry, dict):
                continue

            probe_cc = entry.get("probe_cc", "")
            if probe_cc not in country_set:
                continue

            data = country_data.setdefault(probe_cc, {
                "anomaly_count": 0.0,
                "confirmed_count": 0.0,
            })
            anomaly = entry.get("anomaly_count")
            if anomaly is not None:
                data["anomaly_count"] += float(anomaly)
            confirmed = entry.get("confirmed_count")
            if confirmed is not None:
                data["confirmed_count"] += float(confirmed)

        now_str = self.now_provider().strftime("%Y-%m-%d")
        records: list[dict[str, Any]] = []

        for iso_code in sorted(country_set):
            data = country_data.get(iso_code)
            if data is None:
                continue

            records.append(self._make_record(
                country_id=iso_code,
                signal_key="ooni_blocked_site_count",
                value=data["confirmed_count"],
                period=now_str,
            ))
            records.append(self._make_record(
                country_id=iso_code,
                signal_key="ooni_censorship_incident_count",
                value=data["anomaly_count"],
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
            "quality_flag": "ooni_api",
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
