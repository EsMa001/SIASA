"""WHO Global Health Observatory adapter — health signals for Domain C.

Source: https://ghoapi.azureedge.net/api/
Free, no auth. OData JSON format via Azure CDN.
Fetches life expectancy (WHOSIS_000001), under-5 mortality (MDG_0000000007),
and maternal mortality ratio (MDG_0000000026).

Traceability: SwR-077, AP-15.2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import sleep
from typing import Any, Callable
import json
from urllib.request import Request, urlopen
from urllib.parse import quote

from .base import FetchResult, SourceAdapter


FetchJson = Callable[[str], object]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]

_BASE_URL = "https://ghoapi.azureedge.net/api"

# WHO GHO indicators → (signal_key, sex_filter)
# sex_filter: "SEX_BTSX" for both-sex aggregates, None for indicators without sex dim
_INDICATORS: dict[str, tuple[str, str | None]] = {
    "WHOSIS_000001": ("who_life_expectancy_years", "SEX_BTSX"),
    "MDG_0000000007": ("who_under5_mortality_per1000", "SEX_BTSX"),
    "MDG_0000000026": ("who_maternal_mortality_per100k", None),
}

# ISO-3 alpha → WHO SpatialDim code (WHO uses ISO-3 alpha codes directly)
# This mapping exists so we can extend it for edge cases where WHO diverges
_ISO3_TO_ISO2: dict[str, str] = {
    "AFG": "AFG", "ALB": "ALB", "DZA": "DZA", "AGO": "AGO", "ARG": "ARG",
    "ARM": "ARM", "AUS": "AUS", "AUT": "AUT", "AZE": "AZE", "BGD": "BGD",
    "BLR": "BLR", "BEL": "BEL", "BEN": "BEN", "BOL": "BOL", "BIH": "BIH",
    "BWA": "BWA", "BRA": "BRA", "BGR": "BGR", "BFA": "BFA", "BDI": "BDI",
    "KHM": "KHM", "CMR": "CMR", "CAN": "CAN", "CAF": "CAF", "TCD": "TCD",
    "CHL": "CHL", "CHN": "CHN", "COL": "COL", "COD": "COD", "COG": "COG",
    "CRI": "CRI", "CIV": "CIV", "HRV": "HRV", "CUB": "CUB", "CYP": "CYP",
    "CZE": "CZE", "DNK": "DNK", "DJI": "DJI", "DOM": "DOM", "ECU": "ECU",
    "EGY": "EGY", "SLV": "SLV", "GNQ": "GNQ", "ERI": "ERI", "EST": "EST",
    "ETH": "ETH", "FIN": "FIN", "FRA": "FRA", "GAB": "GAB", "GMB": "GMB",
    "GEO": "GEO", "DEU": "DEU", "GHA": "GHA", "GRC": "GRC", "GTM": "GTM",
    "GIN": "GIN", "GNB": "GNB", "HTI": "HTI", "HND": "HND", "HUN": "HUN",
    "ISL": "ISL", "IND": "IND", "IDN": "IDN", "IRN": "IRN", "IRQ": "IRQ",
    "IRL": "IRL", "ISR": "ISR", "ITA": "ITA", "JAM": "JAM", "JPN": "JPN",
    "JOR": "JOR", "KAZ": "KAZ", "KEN": "KEN", "KWT": "KWT", "KGZ": "KGZ",
    "LAO": "LAO", "LVA": "LVA", "LBN": "LBN", "LSO": "LSO", "LBR": "LBR",
    "LBY": "LBY", "LTU": "LTU", "LUX": "LUX", "MDG": "MDG", "MWI": "MWI",
    "MYS": "MYS", "MLI": "MLI", "MLT": "MLT", "MRT": "MRT", "MUS": "MUS",
    "MEX": "MEX", "MDA": "MDA", "MNG": "MNG", "MNE": "MNE", "MAR": "MAR",
    "MOZ": "MOZ", "MMR": "MMR", "NAM": "NAM", "NPL": "NPL", "NLD": "NLD",
    "NZL": "NZL", "NIC": "NIC", "NER": "NER", "NGA": "NGA", "MKD": "MKD",
    "NOR": "NOR", "OMN": "OMN", "PAK": "PAK", "PAN": "PAN", "PNG": "PNG",
    "PRY": "PRY", "PER": "PER", "PHL": "PHL", "POL": "POL", "PRT": "PRT",
    "QAT": "QAT", "ROU": "ROU", "RUS": "RUS", "RWA": "RWA", "SAU": "SAU",
    "SEN": "SEN", "SRB": "SRB", "SLE": "SLE", "SGP": "SGP", "SVK": "SVK",
    "SVN": "SVN", "SOM": "SOM", "ZAF": "ZAF", "KOR": "KOR", "SSD": "SSD",
    "ESP": "ESP", "LKA": "LKA", "SDN": "SDN", "SWZ": "SWZ", "SWE": "SWE",
    "CHE": "CHE", "SYR": "SYR", "TWN": "TWN", "TJK": "TJK", "TZA": "TZA",
    "THA": "THA", "TLS": "TLS", "TGO": "TGO", "TTO": "TTO", "TUN": "TUN",
    "TUR": "TUR", "TKM": "TKM", "UGA": "UGA", "UKR": "UKR", "ARE": "ARE",
    "GBR": "GBR", "USA": "USA", "URY": "URY", "UZB": "UZB", "VEN": "VEN",
    "VNM": "VNM", "YEM": "YEM", "ZMB": "ZMB", "ZWE": "ZWE",
}


def _parse_gho_response(
    payload: object,
    sex_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Extract latest values from WHO GHO OData JSON response.

    GHO format:
      {"value": [{"SpatialDim": "DEU", "TimeDim": 2021, "NumericValue": 80.6, ...}]}

    Returns list of dicts with keys: country_code, year, value.
    Only the latest year per country is returned.
    """
    if not isinstance(payload, dict):
        return []

    values = payload.get("value")
    if not isinstance(values, list) or not values:
        return []

    # Group by country, keeping latest year
    country_latest: dict[str, tuple[int, float]] = {}

    for entry in values:
        if not isinstance(entry, dict):
            continue

        country_code = entry.get("SpatialDim")
        time_dim = entry.get("TimeDim")
        numeric_value = entry.get("NumericValue")

        if not country_code or time_dim is None or numeric_value is None:
            continue

        if not isinstance(numeric_value, (int, float)):
            continue

        # Apply sex filter if specified
        if sex_filter is not None:
            dim1 = entry.get("Dim1")
            if dim1 != sex_filter:
                continue

        year = int(time_dim)
        if country_code not in country_latest or year > country_latest[country_code][0]:
            country_latest[country_code] = (year, float(numeric_value))

    return [
        {"country_code": cc, "year": year, "value": value}
        for cc, (year, value) in country_latest.items()
    ]


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
class WHOGHOAdapter(SourceAdapter):
    """Fetch health indicators from WHO Global Health Observatory.

    Produces three signal types per country:
    - who_life_expectancy_years: Life expectancy at birth (both sexes)
    - who_under5_mortality_per1000: Under-5 mortality rate per 1000 live births
    - who_maternal_mortality_per100k: Maternal mortality ratio per 100,000 live births
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-WHO-GHO"
    domain: str = "C"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    freshness_hours: int = 2160  # WHO updates ~quarterly, 90 days

    def fetch(self) -> FetchResult:
        """Fetch health indicators for configured countries."""
        if not self.country_ids:
            return FetchResult(
                records=[],
                diagnostics="who_no_countries_configured",
                is_success=True,
            )

        all_records: list[dict[str, Any]] = []
        errors: list[str] = []

        for indicator, (signal_key, sex_filter) in _INDICATORS.items():
            try:
                records = self._fetch_indicator(indicator, signal_key, sex_filter)
                all_records.extend(records)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{indicator}:{exc}")

        if errors and not all_records:
            return FetchResult(
                records=[],
                diagnostics=f"who_fetch_failed: {'; '.join(errors)}",
                is_success=False,
            )

        diagnostics = (
            f"who_fetch_ok countries={len(self.country_ids)} "
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
        sex_filter: str | None,
    ) -> list[dict[str, Any]]:
        """Fetch a single WHO indicator for configured countries."""
        # Build OData filter for countries
        who_codes = []
        iso3_to_who: dict[str, str] = {}
        for iso3 in self.country_ids:
            who_code = _ISO3_TO_ISO2.get(iso3, iso3)
            who_codes.append(who_code)
            iso3_to_who[iso3] = who_code

        # OData filter: SpatialDim in list
        filter_parts = [f"SpatialDim eq '{code}'" for code in sorted(set(who_codes))]
        odata_filter = " or ".join(filter_parts)
        encoded_filter = quote(odata_filter)

        url = f"{_BASE_URL}/{indicator}?$filter={encoded_filter}"

        payload = self._fetch_with_retry(url)
        parsed = _parse_gho_response(payload, sex_filter=sex_filter)

        # Map back WHO codes to ISO3 and filter to configured countries
        who_to_iso3: dict[str, str] = {v: k for k, v in iso3_to_who.items()}
        configured_set = set(self.country_ids)
        records: list[dict[str, Any]] = []

        for item in parsed:
            who_code = item["country_code"]
            # Map back to ISO3 if needed
            iso3 = who_to_iso3.get(who_code, who_code)
            if iso3 not in configured_set:
                continue
            records.append(self._make_record(
                country_id=iso3,
                signal_key=signal_key,
                value=item["value"],
                period=str(item["year"]),
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
            "quality_flag": "who_gho_api",
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
