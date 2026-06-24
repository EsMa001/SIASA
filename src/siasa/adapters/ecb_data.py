"""ECB Statistical Data Warehouse adapter — economic signals for Domain D.

Source: https://data-api.ecb.europa.eu/service/data/
Free, no auth. SDMX-JSON format.
Fetches daily exchange rates and key interest rates.

Traceability: SwR-073, AP-14.2
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

_BASE_URL = "https://data-api.ecb.europa.eu/service/data"

# ISO-3 → ECB currency code (currencies in ECB reference set)
_ISO3_TO_CURRENCY: dict[str, str] = {
    "USA": "USD", "JPN": "JPY", "GBR": "GBP", "CHE": "CHF",
    "AUS": "AUD", "CAN": "CAD", "CHN": "CNY", "BRA": "BRL",
    "KOR": "KRW", "MEX": "MXN", "IND": "INR", "TUR": "TRY",
    "ZAF": "ZAR", "NOR": "NOK", "SWE": "SEK", "DNK": "DKK",
    "POL": "PLN", "CZE": "CZK", "HUN": "HUF", "ROU": "RON",
    "SGP": "SGD", "HKG": "HKD", "NZL": "NZD", "ISR": "ILS",
    "THA": "THB", "MYS": "MYR", "PHL": "PHP", "IDN": "IDR",
    "ISL": "ISK",
    # Eurozone countries → EUR (base currency, rate = 1.0)
    "DEU": "EUR", "FRA": "EUR", "ITA": "EUR", "ESP": "EUR",
    "NLD": "EUR", "BEL": "EUR", "AUT": "EUR", "FIN": "EUR",
    "PRT": "EUR", "IRL": "EUR", "GRC": "EUR", "SVK": "EUR",
    "SVN": "EUR", "EST": "EUR", "LVA": "EUR", "LTU": "EUR",
    "CYP": "EUR", "MLT": "EUR", "LUX": "EUR", "HRV": "EUR",
}

# Eurozone country set
_EUROZONE_COUNTRIES = {
    iso3 for iso3, cur in _ISO3_TO_CURRENCY.items() if cur == "EUR"
}


def _parse_sdmx_observations(payload: object) -> list[dict[str, Any]]:
    """Extract observation values from SDMX-JSON response.

    Returns list of dicts with keys: series_key, dimension_values, time_period, value.
    """
    if not isinstance(payload, dict):
        return []

    data_sets = payload.get("dataSets")
    if not isinstance(data_sets, list) or not data_sets:
        return []

    structure = payload.get("structure", {})
    if not isinstance(structure, dict):
        return []

    dims = structure.get("dimensions", {})
    series_dims = dims.get("series", [])
    obs_dims = dims.get("observation", [])

    series_data = data_sets[0].get("series", {})
    if not isinstance(series_data, dict):
        return []

    results: list[dict[str, Any]] = []

    for series_key, series_obj in series_data.items():
        if not isinstance(series_obj, dict):
            continue

        # Decode series dimension values
        key_parts = series_key.split(":")
        dim_values: dict[str, str] = {}
        for i, part in enumerate(key_parts):
            if i < len(series_dims):
                dim_def = series_dims[i]
                dim_id = dim_def.get("id", f"dim_{i}")
                idx = int(part)
                vals = dim_def.get("values", [])
                if idx < len(vals):
                    dim_values[dim_id] = vals[idx].get("id", "")

        observations = series_obj.get("observations", {})
        if not isinstance(observations, dict):
            continue

        for obs_key, obs_val in observations.items():
            time_period = ""
            if obs_dims:
                obs_idx = int(obs_key)
                time_vals = obs_dims[0].get("values", [])
                if obs_idx < len(time_vals):
                    time_period = time_vals[obs_idx].get("id", "")

            value = obs_val[0] if isinstance(obs_val, list) and obs_val else None
            if value is not None:
                results.append({
                    "series_key": series_key,
                    "dimension_values": dim_values,
                    "time_period": time_period,
                    "value": float(value),
                })

    return results


def _default_fetch_json(url: str) -> object:
    req = Request(url, headers={
        "User-Agent": "SIASA/1.0",
        "Accept": "application/vnd.sdmx.data+json;version=1.0.0-wd",
    })
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class ECBDataAdapter(SourceAdapter):
    """Fetch exchange rates and key interest rates from ECB Data API.

    Produces two signal types:
    - ecb_fx_{currency}_per_eur: Exchange rates vs EUR
    - ecb_key_rate: ECB main refinancing operations rate
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-ECB-DATA"
    domain: str = "D"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    freshness_hours: int = 72

    def fetch(self) -> FetchResult:
        """Fetch FX rates and key rate for configured countries."""
        if not self.country_ids:
            return FetchResult(
                records=[],
                diagnostics="ecb_no_countries_configured",
                is_success=True,
            )

        all_records: list[dict[str, Any]] = []
        errors: list[str] = []

        # 1. Fetch exchange rates
        try:
            fx_records = self._fetch_exchange_rates()
            all_records.extend(fx_records)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"fx:{exc}")

        # 2. Fetch key interest rate (for Eurozone countries)
        eurozone_countries = [c for c in self.country_ids if c in _EUROZONE_COUNTRIES]
        if eurozone_countries:
            try:
                rate_records = self._fetch_key_rate(eurozone_countries)
                all_records.extend(rate_records)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"rate:{exc}")

        if errors and not all_records:
            return FetchResult(
                records=[],
                diagnostics=f"ecb_fetch_failed: {'; '.join(errors)}",
                is_success=False,
            )

        diagnostics = (
            f"ecb_fetch_ok countries={len(self.country_ids)} "
            f"records={len(all_records)}"
        )
        if errors:
            diagnostics += f" partial_errors={len(errors)}"

        return FetchResult(
            records=all_records,
            diagnostics=diagnostics,
            is_success=True,
        )

    def _fetch_exchange_rates(self) -> list[dict[str, Any]]:
        """Fetch latest ECB FX rates."""
        # Determine unique currencies needed
        currency_map: dict[str, str] = {}
        for iso3 in self.country_ids:
            cur = _ISO3_TO_CURRENCY.get(iso3)
            if cur and cur != "EUR":
                currency_map[iso3] = cur

        if not currency_map:
            return []

        unique_currencies = sorted(set(currency_map.values()))
        symbols = "+".join(unique_currencies)

        url = f"{_BASE_URL}/EXR/D.{symbols}.EUR.SP00.A?lastNObservations=1&format=jsondata"
        payload = self._fetch_with_retry(url)
        observations = _parse_sdmx_observations(payload)

        now = self.now_provider()
        records: list[dict[str, Any]] = []

        # Build currency → observation value mapping
        currency_values: dict[str, tuple[float, str]] = {}
        for obs in observations:
            currency = obs["dimension_values"].get("CURRENCY", "")
            if currency:
                currency_values[currency] = (obs["value"], obs.get("time_period", ""))

        # Map countries to their FX records
        for iso3 in sorted(currency_map):
            currency = currency_map[iso3]
            if currency in currency_values:
                value, period = currency_values[currency]
                records.append(self._make_record(
                    country_id=iso3,
                    signal_key=f"ecb_fx_{currency.lower()}_per_eur",
                    value=value,
                    period=period or now.strftime("%Y-%m-%d"),
                ))

        return records

    def _fetch_key_rate(self, eurozone_countries: list[str]) -> list[dict[str, Any]]:
        """Fetch ECB main refinancing operations rate."""
        url = f"{_BASE_URL}/FM/D.U2.EUR.4F.MM.MRR.LEV?lastNObservations=1&format=jsondata"
        payload = self._fetch_with_retry(url)
        observations = _parse_sdmx_observations(payload)

        if not observations:
            return []

        # Use the first (latest) observation
        obs = observations[0]
        period = obs.get("time_period", self.now_provider().strftime("%Y-%m-%d"))

        records: list[dict[str, Any]] = []
        for iso3 in sorted(eurozone_countries):
            records.append(self._make_record(
                country_id=iso3,
                signal_key="ecb_key_rate",
                value=obs["value"],
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
            "quality_flag": "ecb_sdw_api",
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
