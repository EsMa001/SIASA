"""IODA Internet Outages adapter — outage signals for Domain E.

Source: https://api.ioda.inetintel.cc.gatech.edu/v2/alerts
Free, no auth. JSON format.
Fetches internet outage alerts by country.

Traceability: SwR-079
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

_BASE_URL = "https://api.ioda.inetintel.cc.gatech.edu/v2/alerts"

# Map IODA level strings to numeric severity
_LEVEL_SCORES: dict[str, float] = {
    "critical": 3.0,
    "warning": 2.0,
    "normal": 1.0,
}


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
class IODAOutageAdapter(SourceAdapter):
    """Fetch internet outage alerts from IODA API.

    Produces two signal types:
    - ioda_outage_alert_count: Number of outage alerts for a country
    - ioda_bgp_visibility_drop: BGP visibility drop severity score
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-IODA"
    domain: str = "E"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    freshness_hours: int = 24

    def fetch(self) -> FetchResult:
        """Fetch outage alerts for configured countries."""
        if not self.country_ids:
            return FetchResult(
                records=[],
                diagnostics="ioda_no_countries_configured",
                is_success=True,
            )

        all_records: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            url = _BASE_URL
            payload = self._fetch_with_retry(url)
            records = self._parse_alerts(payload)
            all_records.extend(records)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"alerts:{exc}")

        if errors and not all_records:
            return FetchResult(
                records=[],
                diagnostics=f"ioda_fetch_failed: {'; '.join(errors)}",
                is_success=False,
            )

        diagnostics = (
            f"ioda_fetch_ok countries={len(self.country_ids)} "
            f"records={len(all_records)}"
        )
        if errors:
            diagnostics += f" partial_errors={len(errors)}"

        return FetchResult(
            records=all_records,
            diagnostics=diagnostics,
            is_success=True,
        )

    def _parse_alerts(self, payload: object) -> list[dict[str, Any]]:
        """Parse IODA alerts JSON response."""
        if not isinstance(payload, dict):
            return []

        data = payload.get("data")
        if not isinstance(data, list):
            return []

        country_set = set(self.country_ids)
        # Aggregate alerts per country
        country_alerts: dict[str, list[dict[str, Any]]] = {}

        for entry in data:
            if not isinstance(entry, dict):
                continue

            entity_type = entry.get("entityType", "")
            if entity_type != "country":
                continue

            entity_code = entry.get("entityCode", "")
            if entity_code not in country_set:
                continue

            country_alerts.setdefault(entity_code, []).append(entry)

        now_str = self.now_provider().strftime("%Y-%m-%d")
        records: list[dict[str, Any]] = []

        for iso3 in sorted(country_set):
            alerts = country_alerts.get(iso3, [])
            alert_count = len(alerts)

            records.append(self._make_record(
                country_id=iso3,
                signal_key="ioda_outage_alert_count",
                value=float(alert_count),
                period=now_str,
            ))

            # BGP visibility drop: max severity level among alerts
            max_severity = 0.0
            for alert in alerts:
                level = alert.get("level", "normal")
                severity = _LEVEL_SCORES.get(str(level).lower(), 0.0)
                max_severity = max(max_severity, severity)

            records.append(self._make_record(
                country_id=iso3,
                signal_key="ioda_bgp_visibility_drop",
                value=max_severity,
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
            "quality_flag": "ioda_api",
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
