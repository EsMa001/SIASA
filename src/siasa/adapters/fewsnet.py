"""FEWS NET adapter — food security signals for Domain C.

Source: https://fdw.fews.net/api/marketpricefacts/
Free, no auth. JSON format.
Fetches market price data and IPC phase classifications.

Traceability: SwR-081
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

_MARKET_PRICE_URL = "https://fdw.fews.net/api/marketpricefacts/"
_IPC_URL = "https://fdw.fews.net/api/ipcphase/"


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
class FEWSNETAdapter(SourceAdapter):
    """Fetch food security data from FEWS NET Data Warehouse.

    Produces two signal types:
    - fewsnet_food_price_index: Commodity price value
    - fewsnet_ipc_phase: IPC food security phase classification
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-FEWSNET"
    domain: str = "C"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    freshness_hours: int = 720  # monthly data

    def fetch(self) -> FetchResult:
        """Fetch food security data for configured countries."""
        if not self.country_ids:
            return FetchResult(
                records=[],
                diagnostics="fewsnet_no_countries_configured",
                is_success=True,
            )

        all_records: list[dict[str, Any]] = []
        errors: list[str] = []

        # 1. Fetch market prices
        try:
            payload = self._fetch_with_retry(_MARKET_PRICE_URL)
            records = self._parse_market_prices(payload)
            all_records.extend(records)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"market_prices:{exc}")

        # 2. Fetch IPC phases
        try:
            payload = self._fetch_with_retry(_IPC_URL)
            records = self._parse_ipc_phases(payload)
            all_records.extend(records)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ipc_phases:{exc}")

        if errors and not all_records:
            return FetchResult(
                records=[],
                diagnostics=f"fewsnet_fetch_failed: {'; '.join(errors)}",
                is_success=False,
            )

        diagnostics = (
            f"fewsnet_fetch_ok countries={len(self.country_ids)} "
            f"records={len(all_records)}"
        )
        if errors:
            diagnostics += f" partial_errors={len(errors)}"

        return FetchResult(
            records=all_records,
            diagnostics=diagnostics,
            is_success=True,
        )

    def _parse_market_prices(self, payload: object) -> list[dict[str, Any]]:
        """Parse FEWS NET market price JSON response."""
        if not isinstance(payload, list):
            return []

        country_set = set(self.country_ids)
        records: list[dict[str, Any]] = []

        for entry in payload:
            if not isinstance(entry, dict):
                continue

            country_code = entry.get("country", "")
            if country_code not in country_set:
                continue

            price = entry.get("price")
            if price is None:
                continue

            period = entry.get("date", "")

            records.append(self._make_record(
                country_id=country_code,
                signal_key="fewsnet_food_price_index",
                value=float(price),
                period=str(period),
            ))

        return records

    def _parse_ipc_phases(self, payload: object) -> list[dict[str, Any]]:
        """Parse FEWS NET IPC phase JSON response."""
        if not isinstance(payload, list):
            return []

        country_set = set(self.country_ids)
        records: list[dict[str, Any]] = []

        for entry in payload:
            if not isinstance(entry, dict):
                continue

            country_code = entry.get("country", "")
            if country_code not in country_set:
                continue

            phase = entry.get("phase")
            if phase is None:
                continue

            period = entry.get("date", "")

            records.append(self._make_record(
                country_id=country_code,
                signal_key="fewsnet_ipc_phase",
                value=float(phase),
                period=str(period),
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
            "quality_flag": "fewsnet_api",
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
