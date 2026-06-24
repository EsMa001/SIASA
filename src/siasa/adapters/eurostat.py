"""Eurostat adapter — economic signals for Domain D.

Source: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/
Free, no auth. JSON-stat format.
Fetches monthly HICP inflation and unemployment rates per EU country.

Traceability: SwR-074, AP-14.3
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import sleep
from typing import Any, Callable
import json
from urllib.request import Request, urlopen

from .base import FetchResult, SourceAdapter


FetchJson = Callable[[str], object]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]

_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

# ISO-3 → ISO-2 mapping for EU countries available in Eurostat
_ISO3_TO_ISO2: dict[str, str] = {
    "DEU": "DE", "FRA": "FR", "ITA": "IT", "ESP": "ES",
    "NLD": "NL", "BEL": "BE", "AUT": "AT", "FIN": "FI",
    "PRT": "PT", "IRL": "IE", "GRC": "EL", "SVK": "SK",
    "SVN": "SI", "EST": "EE", "LVA": "LV", "LTU": "LT",
    "CYP": "CY", "MLT": "MT", "LUX": "LU", "HRV": "HR",
    "POL": "PL", "CZE": "CZ", "HUN": "HU", "ROU": "RO",
    "BGR": "BG", "SWE": "SE", "DNK": "DK",
}

# Reverse: ISO-2 → ISO-3
_ISO2_TO_ISO3: dict[str, str] = {v: k for k, v in _ISO3_TO_ISO2.items()}


def _parse_eurostat_json(
    payload: object, signal_key: str
) -> list[dict[str, Any]]:
    """Parse Eurostat JSON-stat response into flat records.

    Returns list of dicts with: geo (ISO-2), time_period, value, signal_key.
    """
    if not isinstance(payload, dict):
        return []

    dimensions = payload.get("dimension", {})
    if not isinstance(dimensions, dict):
        return []

    geo_dim = dimensions.get("geo", {})
    time_dim = dimensions.get("time", {})
    values = payload.get("value", {})

    if not geo_dim or not time_dim or not values:
        return []

    geo_index = geo_dim.get("category", {}).get("index", {})
    time_index = time_dim.get("category", {}).get("index", {})

    if not geo_index or not time_index:
        return []

    # Build reverse index: position → geo/time code
    geo_codes = sorted(geo_index.keys(), key=lambda k: geo_index[k])
    time_codes = sorted(time_index.keys(), key=lambda k: time_index[k])

    n_times = len(time_codes)
    records: list[dict[str, Any]] = []

    for geo_code in geo_codes:
        geo_pos = geo_index[geo_code]
        for time_code in time_codes:
            time_pos = time_index[time_code]
            # Flat index = geo_pos * n_times + time_pos
            flat_idx = str(geo_pos * n_times + time_pos)
            val = values.get(flat_idx)
            if val is not None:
                # Convert monthly period: 2026M05 → 2026-05
                period = time_code.replace("M", "-") if "M" in time_code else time_code
                records.append({
                    "geo": geo_code,
                    "time_period": period,
                    "value": float(val),
                    "signal_key": signal_key,
                })

    return records


def _default_fetch_json(url: str) -> object:
    req = Request(url, headers={"User-Agent": "SIASA/1.0"})
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class EurostatAdapter(SourceAdapter):
    """Fetch HICP inflation and unemployment rates from Eurostat.

    Produces two signal types:
    - eurostat_hicp_inflation: Monthly HICP annual rate of change
    - eurostat_unemployment_rate: Monthly unemployment rate
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-EUROSTAT"
    domain: str = "D"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    freshness_hours: int = 720  # Monthly data — ~30 days

    def fetch(self) -> FetchResult:
        """Fetch inflation + unemployment for configured countries."""
        if not self.country_ids:
            return FetchResult(
                records=[],
                diagnostics="eurostat_no_countries_configured",
                is_success=True,
            )

        # Map ISO-3 → ISO-2, filter to supported countries
        country_map = {
            iso3: _ISO3_TO_ISO2[iso3]
            for iso3 in self.country_ids
            if iso3 in _ISO3_TO_ISO2
        }

        if not country_map:
            return FetchResult(
                records=[],
                diagnostics="eurostat_no_eu_countries_in_set",
                is_success=True,
            )

        geo_filter = "+".join(sorted(set(country_map.values())))
        all_records: list[dict[str, Any]] = []
        errors: list[str] = []

        # 1. HICP inflation
        try:
            hicp_records = self._fetch_hicp(geo_filter, country_map)
            all_records.extend(hicp_records)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"hicp:{exc}")

        # 2. Unemployment rate
        try:
            unemp_records = self._fetch_unemployment(geo_filter, country_map)
            all_records.extend(unemp_records)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"unemp:{exc}")

        if errors and not all_records:
            return FetchResult(
                records=[],
                diagnostics=f"eurostat_fetch_failed: {'; '.join(errors)}",
                is_success=False,
            )

        diagnostics = (
            f"eurostat_fetch_ok countries={len(country_map)} "
            f"records={len(all_records)}"
        )
        if errors:
            diagnostics += f" partial_errors={len(errors)}"

        return FetchResult(
            records=all_records,
            diagnostics=diagnostics,
            is_success=True,
        )

    def _fetch_hicp(
        self, geo_filter: str, country_map: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Fetch HICP annual rate of change."""
        url = (
            f"{_BASE_URL}/prc_hicp_manr?"
            f"geo={geo_filter}&coicop=CP00&unit=RCH_A&sinceTimePeriod=2026M01"
            f"&format=JSON&lang=EN"
        )
        payload = self._fetch_with_retry(url)
        parsed = _parse_eurostat_json(payload, "eurostat_hicp_inflation")
        return self._map_records(parsed, country_map)

    def _fetch_unemployment(
        self, geo_filter: str, country_map: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Fetch monthly unemployment rate."""
        url = (
            f"{_BASE_URL}/une_rt_m?"
            f"geo={geo_filter}&age=TOTAL&sex=T&s_adj=SA&unit=PC_ACT"
            f"&sinceTimePeriod=2026M01&format=JSON&lang=EN"
        )
        payload = self._fetch_with_retry(url)
        parsed = _parse_eurostat_json(payload, "eurostat_unemployment_rate")
        return self._map_records(parsed, country_map)

    def _map_records(
        self, parsed: list[dict[str, Any]], country_map: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Map parsed Eurostat records to SIASA NormalizedRecord format."""
        # Build reverse ISO-2 → ISO-3 for this adapter's country set
        iso2_to_iso3 = {v: k for k, v in country_map.items()}

        records: list[dict[str, Any]] = []
        for item in parsed:
            geo = item["geo"]
            iso3 = iso2_to_iso3.get(geo)
            if not iso3:
                continue

            records.append({
                "country_id": iso3,
                "period": item["time_period"],
                "signal_key": item["signal_key"],
                "value": item["value"],
                "quality_flag": "eurostat_api",
                "freshness_hours": self.freshness_hours,
                "freshness_horizon_hours": self.freshness_hours,
                "expected_source_count": 1,
            })

        return records

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
