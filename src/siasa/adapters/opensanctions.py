"""OpenSanctions adapter — sanctions signals for Domain B.

Source: https://api.opensanctions.org/search/sanctions
Free (rate-limited). JSON format.
Fetches sanctions entity counts and new listings by country.

Traceability: SwR-082
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

_BASE_URL = "https://api.opensanctions.org/search/sanctions"


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
class OpenSanctionsAdapter(SourceAdapter):
    """Fetch sanctions data from OpenSanctions API.

    Produces two signal types:
    - opensanctions_entity_count: Total sanctioned entities for a country
    - opensanctions_new_listings: Number of recently added sanctions
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-OPENSANCTIONS"
    domain: str = "B"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    freshness_hours: int = 168  # weekly data

    def fetch(self) -> FetchResult:
        """Fetch sanctions data for configured countries."""
        if not self.country_ids:
            return FetchResult(
                records=[],
                diagnostics="opensanctions_no_countries_configured",
                is_success=True,
            )

        all_records: list[dict[str, Any]] = []
        errors: list[str] = []

        for iso3 in self.country_ids:
            try:
                url = f"{_BASE_URL}?countries={iso3.lower()}"
                payload = self._fetch_with_retry(url)
                records = self._parse_sanctions(payload, iso3)
                all_records.extend(records)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{iso3}:{exc}")

        if errors and not all_records:
            return FetchResult(
                records=[],
                diagnostics=f"opensanctions_fetch_failed: {'; '.join(errors)}",
                is_success=False,
            )

        diagnostics = (
            f"opensanctions_fetch_ok countries={len(self.country_ids)} "
            f"records={len(all_records)}"
        )
        if errors:
            diagnostics += f" partial_errors={len(errors)}"

        return FetchResult(
            records=all_records,
            diagnostics=diagnostics,
            is_success=True,
        )

    def _parse_sanctions(self, payload: object, country_id: str) -> list[dict[str, Any]]:
        """Parse OpenSanctions search response."""
        if not isinstance(payload, dict):
            return []

        now_str = self.now_provider().strftime("%Y-%m-%d")
        records: list[dict[str, Any]] = []

        # Total entity count
        total = payload.get("total")
        if isinstance(total, dict):
            entity_count = total.get("value", 0)
        elif isinstance(total, (int, float)):
            entity_count = total
        else:
            entity_count = 0

        records.append(self._make_record(
            country_id=country_id,
            signal_key="opensanctions_entity_count",
            value=float(entity_count),
            period=now_str,
        ))

        # Count new listings from results
        results = payload.get("results")
        new_count = 0
        if isinstance(results, list):
            new_count = len(results)

        records.append(self._make_record(
            country_id=country_id,
            signal_key="opensanctions_new_listings",
            value=float(new_count),
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
            "quality_flag": "opensanctions_api",
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
