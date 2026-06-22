"""Frankfurter API adapter — ECB exchange rates for Domain D.

Source: https://api.frankfurter.dev (ECB reference rates via Frankfurter).
Free, no auth, no rate limit. 30+ currencies.
Provides latest + historical exchange rates.

Traceability: SwR-ADAPTER-FRANKFURTER, AP-11.2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from time import sleep
from typing import Any, Callable
import json
from urllib.request import Request, urlopen

from .base import FetchResult, SourceAdapter


FetchJson = Callable[[str], object]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]


def _default_fetch_json(url: str) -> object:
    req = Request(url, headers={"User-Agent": "SIASA/1.0"})
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def _utc_now() -> datetime:
    return datetime.now(UTC)


# ISO-3 → Frankfurter currency code mapping.
# Only countries whose national currency is in the ECB reference set.
_ISO3_TO_CURRENCY: dict[str, str] = {
    "AUS": "AUD", "BRA": "BRL", "CAN": "CAD", "CHE": "CHF",
    "CHN": "CNY", "CZE": "CZK", "DNK": "DKK", "GBR": "GBP",
    "HKG": "HKD", "HUN": "HUF", "IDN": "IDR", "ISR": "ILS",
    "IND": "INR", "ISL": "ISK", "JPN": "JPY", "KOR": "KRW",
    "MEX": "MXN", "MYS": "MYR", "NOR": "NOK", "NZL": "NZD",
    "PHL": "PHP", "POL": "PLN", "ROU": "RON", "SWE": "SEK",
    "SGP": "SGD", "THA": "THB", "TUR": "TRY", "ZAF": "ZAR",
    # Eurozone countries → EUR
    "DEU": "EUR", "FRA": "EUR", "ITA": "EUR", "ESP": "EUR",
    "NLD": "EUR", "BEL": "EUR", "AUT": "EUR", "FIN": "EUR",
    "PRT": "EUR", "IRL": "EUR", "GRC": "EUR", "SVK": "EUR",
    "SVN": "EUR",    "EST": "EUR",  # Estonia joined Eurozone 2011
    "LVA": "EUR", "LTU": "EUR", "CYP": "EUR", "MLT": "EUR",
    "LUX": "EUR", "HRV": "EUR",
    # USA is the base currency → special handling
    "USA": "USD",
}

# Supported Frankfurter currencies (ECB reference set)
_SUPPORTED_CURRENCIES = {
    "AUD", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR",
    "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "ISK", "JPY",
    "KOR",  # Note: Frankfurter uses KRW
    "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN", "RON",
    "SEK", "SGD", "THB", "TRY", "USD", "ZAR",
}


@dataclass
class FrankfurterAdapter(SourceAdapter):
    """Fetch ECB exchange rates from Frankfurter API.

    For each requested country, maps ISO-3 to a currency and fetches the
    latest USD-based exchange rate. Countries without a mapped or supported
    currency are skipped with diagnostics.
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-FRANKFURTER"
    domain: str = "D"
    base_url: str = "https://api.frankfurter.dev/v1"
    base_currency: str = "USD"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    # Freshness: ECB publishes daily on business days; ~48h max staleness
    daily_freshness_hours: int = 72

    def fetch(self) -> FetchResult:
        """Fetch latest exchange rates for all mapped countries."""
        try:
            # Determine unique currencies needed
            currency_map = self._build_currency_map()
            if not currency_map:
                return FetchResult(
                    records=[],
                    diagnostics="frankfurter_no_mapped_currencies",
                    is_success=True,
                )

            unique_currencies = sorted(set(currency_map.values()) - {self.base_currency})
            if not unique_currencies:
                # All countries use base currency (e.g., all USA)
                return FetchResult(
                    records=self._build_base_currency_records(currency_map),
                    diagnostics=f"frankfurter_base_only countries={len(currency_map)}",
                    is_success=True,
                )

            # Single API call for all currencies at once
            symbols = ",".join(unique_currencies)
            url = f"{self.base_url}/latest?base={self.base_currency}&symbols={symbols}"
            payload = self._fetch_with_retry(url)
            records = self._parse_payload(payload, currency_map)

            diagnostics = (
                f"frankfurter_fetch_ok countries={len(currency_map)} "
                f"currencies={len(unique_currencies)} records={len(records)}"
            )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except Exception as exc:  # noqa: BLE001
            return FetchResult(
                records=[],
                diagnostics=f"frankfurter_fetch_failed: {exc}",
                is_success=False,
            )

    def _build_currency_map(self) -> dict[str, str]:
        """Map country ISO-3 codes to Frankfurter-supported currencies."""
        result: dict[str, str] = {}
        for iso3 in self.country_ids:
            currency = _ISO3_TO_CURRENCY.get(iso3)
            if currency and (currency in _SUPPORTED_CURRENCIES or currency == self.base_currency):
                result[iso3] = currency
        return result

    def _build_base_currency_records(self, currency_map: dict[str, str]) -> list[dict[str, Any]]:
        """Build records for countries using the base currency (rate = 1.0)."""
        now = self.now_provider()
        records: list[dict[str, Any]] = []
        for iso3 in sorted(currency_map):
            records.append(self._make_record(iso3, currency_map[iso3], 1.0, now))
        return records

    def _parse_payload(
        self, payload: object, currency_map: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Parse Frankfurter latest response into SIASA records."""
        if not isinstance(payload, dict):
            raise ValueError("Frankfurter payload must be a JSON object")

        rates = payload.get("rates")
        if not isinstance(rates, dict):
            raise ValueError("Frankfurter payload must contain 'rates' object")

        date_str = payload.get("date", "")
        now = self.now_provider()

        records: list[dict[str, Any]] = []
        for iso3 in sorted(currency_map):
            currency = currency_map[iso3]
            if currency == self.base_currency:
                rate = 1.0
            else:
                rate = rates.get(currency)
                if rate is None:
                    continue
            records.append(self._make_record(iso3, currency, float(rate), now, date_str))
        return records

    def _make_record(
        self,
        country_id: str,
        currency: str,
        rate: float,
        now: datetime,
        date_str: str = "",
    ) -> dict[str, Any]:
        return {
            "country_id": country_id,
            "period": date_str or now.strftime("%Y-%m-%d"),
            "signal_key": f"ecb_fx_{currency.lower()}_per_usd",
            "value": rate,
            "currency": currency,
            "expected_source_count": 1,
            "freshness_hours": self.daily_freshness_hours,
            "freshness_horizon_hours": self.daily_freshness_hours,
            "quality_flag": "ecb_frankfurter_api",
        }

    def _fetch_with_retry(self, url: str) -> object:
        if self.max_retries < 0:
            raise ValueError("Frankfurter adapter max_retries must be >= 0")

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
