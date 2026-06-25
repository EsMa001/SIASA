"""SIASA Data Registry — Country and Signal registries (AP-13.2).

Implements:
- SwR-057: Country registry with canonical entity resolution
- SwR-058: Signal registry with aggregation metadata
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Country Registry (SwR-057)
# ---------------------------------------------------------------------------

@dataclass
class CountryRegistryEntry:
    """Canonical country record for entity resolution across sources."""
    canonical_id: str        # ISO-3 (primary key)
    iso2: str = ""           # ISO-2
    name_en: str = ""        # English name
    region: str = ""         # UN region
    subregion: str = ""      # UN subregion
    active_in_siasa: bool = True


# Embedded registry — 88 governed pilot countries + key extras
# Source: _SUPPORTED_LIVE_PILOT_COUNTRIES in live_runtime.py
_COUNTRY_REGISTRY: list[dict] = [
    {"canonical_id": "AFG", "iso2": "AF", "name_en": "Afghanistan", "region": "Asia", "subregion": "Southern Asia"},
    {"canonical_id": "AGO", "iso2": "AO", "name_en": "Angola", "region": "Africa", "subregion": "Middle Africa"},
    {"canonical_id": "ARG", "iso2": "AR", "name_en": "Argentina", "region": "Americas", "subregion": "South America"},
    {"canonical_id": "AUS", "iso2": "AU", "name_en": "Australia", "region": "Oceania", "subregion": "Australia and New Zealand"},
    {"canonical_id": "AUT", "iso2": "AT", "name_en": "Austria", "region": "Europe", "subregion": "Western Europe"},
    {"canonical_id": "BEL", "iso2": "BE", "name_en": "Belgium", "region": "Europe", "subregion": "Western Europe"},
    {"canonical_id": "BGR", "iso2": "BG", "name_en": "Bulgaria", "region": "Europe", "subregion": "Eastern Europe"},
    {"canonical_id": "BOL", "iso2": "BO", "name_en": "Bolivia", "region": "Americas", "subregion": "South America"},
    {"canonical_id": "BRA", "iso2": "BR", "name_en": "Brazil", "region": "Americas", "subregion": "South America"},
    {"canonical_id": "CAN", "iso2": "CA", "name_en": "Canada", "region": "Americas", "subregion": "Northern America"},
    {"canonical_id": "CHE", "iso2": "CH", "name_en": "Switzerland", "region": "Europe", "subregion": "Western Europe"},
    {"canonical_id": "CHL", "iso2": "CL", "name_en": "Chile", "region": "Americas", "subregion": "South America"},
    {"canonical_id": "CHN", "iso2": "CN", "name_en": "China", "region": "Asia", "subregion": "Eastern Asia"},
    {"canonical_id": "CMR", "iso2": "CM", "name_en": "Cameroon", "region": "Africa", "subregion": "Middle Africa"},
    {"canonical_id": "COD", "iso2": "CD", "name_en": "Congo (DRC)", "region": "Africa", "subregion": "Middle Africa"},
    {"canonical_id": "COL", "iso2": "CO", "name_en": "Colombia", "region": "Americas", "subregion": "South America"},
    {"canonical_id": "CUB", "iso2": "CU", "name_en": "Cuba", "region": "Americas", "subregion": "Caribbean"},
    {"canonical_id": "CZE", "iso2": "CZ", "name_en": "Czechia", "region": "Europe", "subregion": "Eastern Europe"},
    {"canonical_id": "DEU", "iso2": "DE", "name_en": "Germany", "region": "Europe", "subregion": "Western Europe"},
    {"canonical_id": "DNK", "iso2": "DK", "name_en": "Denmark", "region": "Europe", "subregion": "Northern Europe"},
    {"canonical_id": "DZA", "iso2": "DZ", "name_en": "Algeria", "region": "Africa", "subregion": "Northern Africa"},
    {"canonical_id": "ECU", "iso2": "EC", "name_en": "Ecuador", "region": "Americas", "subregion": "South America"},
    {"canonical_id": "EGY", "iso2": "EG", "name_en": "Egypt", "region": "Africa", "subregion": "Northern Africa"},
    {"canonical_id": "ESP", "iso2": "ES", "name_en": "Spain", "region": "Europe", "subregion": "Southern Europe"},
    {"canonical_id": "EST", "iso2": "EE", "name_en": "Estonia", "region": "Europe", "subregion": "Northern Europe"},
    {"canonical_id": "ETH", "iso2": "ET", "name_en": "Ethiopia", "region": "Africa", "subregion": "Eastern Africa"},
    {"canonical_id": "FIN", "iso2": "FI", "name_en": "Finland", "region": "Europe", "subregion": "Northern Europe"},
    {"canonical_id": "FRA", "iso2": "FR", "name_en": "France", "region": "Europe", "subregion": "Western Europe"},
    {"canonical_id": "GBR", "iso2": "GB", "name_en": "United Kingdom", "region": "Europe", "subregion": "Northern Europe"},
    {"canonical_id": "GEO", "iso2": "GE", "name_en": "Georgia", "region": "Asia", "subregion": "Western Asia"},
    {"canonical_id": "GHA", "iso2": "GH", "name_en": "Ghana", "region": "Africa", "subregion": "Western Africa"},
    {"canonical_id": "GRC", "iso2": "GR", "name_en": "Greece", "region": "Europe", "subregion": "Southern Europe"},
    {"canonical_id": "HUN", "iso2": "HU", "name_en": "Hungary", "region": "Europe", "subregion": "Eastern Europe"},
    {"canonical_id": "IDN", "iso2": "ID", "name_en": "Indonesia", "region": "Asia", "subregion": "South-eastern Asia"},
    {"canonical_id": "IND", "iso2": "IN", "name_en": "India", "region": "Asia", "subregion": "Southern Asia"},
    {"canonical_id": "IRL", "iso2": "IE", "name_en": "Ireland", "region": "Europe", "subregion": "Northern Europe"},
    {"canonical_id": "IRN", "iso2": "IR", "name_en": "Iran", "region": "Asia", "subregion": "Southern Asia"},
    {"canonical_id": "IRQ", "iso2": "IQ", "name_en": "Iraq", "region": "Asia", "subregion": "Western Asia"},
    {"canonical_id": "ISR", "iso2": "IL", "name_en": "Israel", "region": "Asia", "subregion": "Western Asia"},
    {"canonical_id": "ITA", "iso2": "IT", "name_en": "Italy", "region": "Europe", "subregion": "Southern Europe"},
    {"canonical_id": "JOR", "iso2": "JO", "name_en": "Jordan", "region": "Asia", "subregion": "Western Asia"},
    {"canonical_id": "JPN", "iso2": "JP", "name_en": "Japan", "region": "Asia", "subregion": "Eastern Asia"},
    {"canonical_id": "KAZ", "iso2": "KZ", "name_en": "Kazakhstan", "region": "Asia", "subregion": "Central Asia"},
    {"canonical_id": "KEN", "iso2": "KE", "name_en": "Kenya", "region": "Africa", "subregion": "Eastern Africa"},
    {"canonical_id": "KHM", "iso2": "KH", "name_en": "Cambodia", "region": "Asia", "subregion": "South-eastern Asia"},
    {"canonical_id": "KOR", "iso2": "KR", "name_en": "South Korea", "region": "Asia", "subregion": "Eastern Asia"},
    {"canonical_id": "LAO", "iso2": "LA", "name_en": "Laos", "region": "Asia", "subregion": "South-eastern Asia"},
    {"canonical_id": "LBN", "iso2": "LB", "name_en": "Lebanon", "region": "Asia", "subregion": "Western Asia"},
    {"canonical_id": "LBY", "iso2": "LY", "name_en": "Libya", "region": "Africa", "subregion": "Northern Africa"},
    {"canonical_id": "MAR", "iso2": "MA", "name_en": "Morocco", "region": "Africa", "subregion": "Northern Africa"},
    {"canonical_id": "MEX", "iso2": "MX", "name_en": "Mexico", "region": "Americas", "subregion": "Central America"},
    {"canonical_id": "MMR", "iso2": "MM", "name_en": "Myanmar", "region": "Asia", "subregion": "South-eastern Asia"},
    {"canonical_id": "MNG", "iso2": "MN", "name_en": "Mongolia", "region": "Asia", "subregion": "Eastern Asia"},
    {"canonical_id": "MOZ", "iso2": "MZ", "name_en": "Mozambique", "region": "Africa", "subregion": "Eastern Africa"},
    {"canonical_id": "MYS", "iso2": "MY", "name_en": "Malaysia", "region": "Asia", "subregion": "South-eastern Asia"},
    {"canonical_id": "NGA", "iso2": "NG", "name_en": "Nigeria", "region": "Africa", "subregion": "Western Africa"},
    {"canonical_id": "NLD", "iso2": "NL", "name_en": "Netherlands", "region": "Europe", "subregion": "Western Europe"},
    {"canonical_id": "NOR", "iso2": "NO", "name_en": "Norway", "region": "Europe", "subregion": "Northern Europe"},
    {"canonical_id": "NZL", "iso2": "NZ", "name_en": "New Zealand", "region": "Oceania", "subregion": "Australia and New Zealand"},
    {"canonical_id": "PAK", "iso2": "PK", "name_en": "Pakistan", "region": "Asia", "subregion": "Southern Asia"},
    {"canonical_id": "PER", "iso2": "PE", "name_en": "Peru", "region": "Americas", "subregion": "South America"},
    {"canonical_id": "PHL", "iso2": "PH", "name_en": "Philippines", "region": "Asia", "subregion": "South-eastern Asia"},
    {"canonical_id": "POL", "iso2": "PL", "name_en": "Poland", "region": "Europe", "subregion": "Eastern Europe"},
    {"canonical_id": "PRK", "iso2": "KP", "name_en": "North Korea", "region": "Asia", "subregion": "Eastern Asia"},
    {"canonical_id": "PRT", "iso2": "PT", "name_en": "Portugal", "region": "Europe", "subregion": "Southern Europe"},
    {"canonical_id": "QAT", "iso2": "QA", "name_en": "Qatar", "region": "Asia", "subregion": "Western Asia"},
    {"canonical_id": "ROU", "iso2": "RO", "name_en": "Romania", "region": "Europe", "subregion": "Eastern Europe"},
    {"canonical_id": "RUS", "iso2": "RU", "name_en": "Russia", "region": "Europe", "subregion": "Eastern Europe"},
    {"canonical_id": "SAU", "iso2": "SA", "name_en": "Saudi Arabia", "region": "Asia", "subregion": "Western Asia"},
    {"canonical_id": "SDN", "iso2": "SD", "name_en": "Sudan", "region": "Africa", "subregion": "Northern Africa"},
    {"canonical_id": "SGP", "iso2": "SG", "name_en": "Singapore", "region": "Asia", "subregion": "South-eastern Asia"},
    {"canonical_id": "SOM", "iso2": "SO", "name_en": "Somalia", "region": "Africa", "subregion": "Eastern Africa"},
    {"canonical_id": "SRB", "iso2": "RS", "name_en": "Serbia", "region": "Europe", "subregion": "Southern Europe"},
    {"canonical_id": "SWE", "iso2": "SE", "name_en": "Sweden", "region": "Europe", "subregion": "Northern Europe"},
    {"canonical_id": "SYR", "iso2": "SY", "name_en": "Syria", "region": "Asia", "subregion": "Western Asia"},
    {"canonical_id": "THA", "iso2": "TH", "name_en": "Thailand", "region": "Asia", "subregion": "South-eastern Asia"},
    {"canonical_id": "TUN", "iso2": "TN", "name_en": "Tunisia", "region": "Africa", "subregion": "Northern Africa"},
    {"canonical_id": "TUR", "iso2": "TR", "name_en": "Turkey", "region": "Asia", "subregion": "Western Asia"},
    {"canonical_id": "TWN", "iso2": "TW", "name_en": "Taiwan", "region": "Asia", "subregion": "Eastern Asia"},
    {"canonical_id": "TZA", "iso2": "TZ", "name_en": "Tanzania", "region": "Africa", "subregion": "Eastern Africa"},
    {"canonical_id": "UKR", "iso2": "UA", "name_en": "Ukraine", "region": "Europe", "subregion": "Eastern Europe"},
    {"canonical_id": "USA", "iso2": "US", "name_en": "United States", "region": "Americas", "subregion": "Northern America"},
    {"canonical_id": "UZB", "iso2": "UZ", "name_en": "Uzbekistan", "region": "Asia", "subregion": "Central Asia"},
    {"canonical_id": "VEN", "iso2": "VE", "name_en": "Venezuela", "region": "Americas", "subregion": "South America"},
    {"canonical_id": "VNM", "iso2": "VN", "name_en": "Vietnam", "region": "Asia", "subregion": "South-eastern Asia"},
    {"canonical_id": "YEM", "iso2": "YE", "name_en": "Yemen", "region": "Asia", "subregion": "Western Asia"},
    {"canonical_id": "ZAF", "iso2": "ZA", "name_en": "South Africa", "region": "Africa", "subregion": "Southern Africa"},
    {"canonical_id": "ZWE", "iso2": "ZW", "name_en": "Zimbabwe", "region": "Africa", "subregion": "Eastern Africa"},
]


def load_country_registry() -> list[CountryRegistryEntry]:
    """Load the canonical country registry."""
    return [CountryRegistryEntry(**entry) for entry in _COUNTRY_REGISTRY]


def validate_country_registry(entries: list[CountryRegistryEntry]) -> list[str]:
    """Validate the country registry. Returns a list of issues (empty = OK)."""
    issues: list[str] = []
    seen_ids: set[str] = set()
    for entry in entries:
        if len(entry.canonical_id) != 3:
            issues.append(f"{entry.canonical_id}: canonical_id must be 3 chars (ISO-3)")
        if entry.canonical_id in seen_ids:
            issues.append(f"{entry.canonical_id}: duplicate canonical_id")
        seen_ids.add(entry.canonical_id)
        if not entry.name_en:
            issues.append(f"{entry.canonical_id}: missing name_en")
        if not entry.region:
            issues.append(f"{entry.canonical_id}: missing region")
    return issues


# ---------------------------------------------------------------------------
# Signal Registry (SwR-058)
# ---------------------------------------------------------------------------

@dataclass
class SignalRegistryEntry:
    """Metadata for a single signal key used across the SIASA pipeline."""
    signal_key: str
    domain: str                    # A/B/C/D/E
    source_id: str = ""            # Primary source
    description: str = ""
    unit: str = ""                 # count, ratio, score, USD, ...
    native_granularity: str = ""   # 15min, hourly, daily, yearly
    aggregation_method: str = "none"  # sum, mean, max, last, count, none


# All signal keys actively used by the 9 live adapters
KNOWN_ACTIVE_SIGNAL_KEYS: set[str] = {
    # Domain A (Information Space) — GDELT Doc
    "article_count",
    # Domain B (Security/Conflict) — GDELT Events
    "conflict_event_count", "protest_event_count", "violent_event_count",
    # Domain B — GDACS
    "disaster_alert_level",
    # Domain C (Physical/Social) — UNHCR
    "refugee_population", "asylum_seeker_population", "idp_population", "displacement_total",
    # Domain C — HDX-INFORM
    "inform_risk", "hazard_exposure", "vulnerability", "lack_coping_capacity",
    # Domain D (Economic) — World Bank
    "gdp_growth", "trade_volume_change",
    # Domain D — Frankfurter (dynamic fx keys not listed — pattern: ecb_fx_{currency}_per_usd)
    # Domain E (Cyber/InfoOps) — CISA-KEV
    "cyber_kev_recent_count", "cyber_kev_ransomware_recent", "cyber_kev_overdue_count", "cyber_kev_total",
    # Domain E — Voidly
    "censorship_score",
    # Domain A — Wikipedia Pageviews (AP-14.1)
    "wiki_pageview_count",
    # Domain D — ECB (AP-14.2)
    "ecb_key_rate", "ecb_fx_usd_per_eur", "ecb_fx_jpy_per_eur", "ecb_fx_gbp_per_eur",
    "ecb_fx_chf_per_eur", "ecb_fx_cny_per_eur", "ecb_fx_try_per_eur", "ecb_fx_zar_per_eur",
    # Domain D — Eurostat (AP-14.3)
    "eurostat_hicp_inflation", "eurostat_unemployment_rate",
    # Domain E — NVD CVE (AP-14.4)
    "nvd_cve_count_daily", "nvd_avg_cvss_base", "nvd_critical_cve_count",
}


_SIGNAL_REGISTRY: list[dict] = [
    # Domain A
    {"signal_key": "article_count", "domain": "A", "source_id": "SRC-GDELT-DOC", "description": "Article count from GDELT DOC API", "unit": "count", "native_granularity": "daily", "aggregation_method": "sum"},
    # Domain B — GDELT Events
    {"signal_key": "conflict_event_count", "domain": "B", "source_id": "SRC-GDELT-EVENTS", "description": "Conflict event count from GDELT Events", "unit": "count", "native_granularity": "15min", "aggregation_method": "sum"},
    {"signal_key": "protest_event_count", "domain": "B", "source_id": "SRC-GDELT-EVENTS", "description": "Protest event count from GDELT Events", "unit": "count", "native_granularity": "15min", "aggregation_method": "sum"},
    {"signal_key": "violent_event_count", "domain": "B", "source_id": "SRC-GDELT-EVENTS", "description": "Violent event count from GDELT Events", "unit": "count", "native_granularity": "15min", "aggregation_method": "sum"},
    # Domain B — GDACS
    {"signal_key": "disaster_alert_level", "domain": "B", "source_id": "SRC-GDACS", "description": "Disaster alert severity (1=green, 2=orange, 3=red)", "unit": "level", "native_granularity": "hourly", "aggregation_method": "max"},
    # Domain C — UNHCR
    {"signal_key": "refugee_population", "domain": "C", "source_id": "SRC-UNHCR-POP", "description": "Refugee population from UNHCR", "unit": "count", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "asylum_seeker_population", "domain": "C", "source_id": "SRC-UNHCR-POP", "description": "Asylum seeker population from UNHCR", "unit": "count", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "idp_population", "domain": "C", "source_id": "SRC-UNHCR-POP", "description": "Internally displaced persons from UNHCR", "unit": "count", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "displacement_total", "domain": "C", "source_id": "SRC-UNHCR-POP", "description": "Total displaced population from UNHCR", "unit": "count", "native_granularity": "yearly", "aggregation_method": "last"},
    # Domain C — HDX-INFORM
    {"signal_key": "inform_risk", "domain": "C", "source_id": "SRC-HDX-INFORM", "description": "INFORM composite risk index", "unit": "score", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "hazard_exposure", "domain": "C", "source_id": "SRC-HDX-INFORM", "description": "INFORM hazard & exposure dimension", "unit": "score", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "vulnerability", "domain": "C", "source_id": "SRC-HDX-INFORM", "description": "INFORM vulnerability dimension", "unit": "score", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "lack_coping_capacity", "domain": "C", "source_id": "SRC-HDX-INFORM", "description": "INFORM lack of coping capacity dimension", "unit": "score", "native_granularity": "yearly", "aggregation_method": "last"},
    # Domain D — World Bank
    {"signal_key": "gdp_growth", "domain": "D", "source_id": "WB-INDICATORS", "description": "GDP growth rate from World Bank", "unit": "percent", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "trade_volume_change", "domain": "D", "source_id": "WB-INDICATORS", "description": "Trade volume change from World Bank", "unit": "percent", "native_granularity": "yearly", "aggregation_method": "last"},
    # Domain E — CISA-KEV
    {"signal_key": "cyber_kev_recent_count", "domain": "E", "source_id": "SRC-CISA-KEV", "description": "Recent known exploited vulnerabilities count", "unit": "count", "native_granularity": "daily", "aggregation_method": "last"},
    {"signal_key": "cyber_kev_ransomware_recent", "domain": "E", "source_id": "SRC-CISA-KEV", "description": "Recent ransomware-known CVEs", "unit": "count", "native_granularity": "daily", "aggregation_method": "last"},
    {"signal_key": "cyber_kev_overdue_count", "domain": "E", "source_id": "SRC-CISA-KEV", "description": "Overdue remediation CVEs", "unit": "count", "native_granularity": "daily", "aggregation_method": "last"},
    {"signal_key": "cyber_kev_total", "domain": "E", "source_id": "SRC-CISA-KEV", "description": "Total known exploited vulnerabilities", "unit": "count", "native_granularity": "daily", "aggregation_method": "last"},
    # Domain E — Voidly
    {"signal_key": "censorship_score", "domain": "E", "source_id": "SRC-VOIDLY", "description": "Internet censorship score from Voidly", "unit": "score", "native_granularity": "daily", "aggregation_method": "last"},
    # Domain A — Wikipedia Pageviews (AP-14.1)
    {"signal_key": "wiki_pageview_count", "domain": "A", "source_id": "SRC-WIKIPEDIA-PAGEVIEWS", "description": "Daily pageview count for conflict-relevant Wikipedia articles", "unit": "count", "native_granularity": "daily", "aggregation_method": "sum"},
    # Domain D — ECB (AP-14.2)
    {"signal_key": "ecb_key_rate", "domain": "D", "source_id": "SRC-ECB-DATA", "description": "ECB main refinancing operations rate", "unit": "percent", "native_granularity": "daily", "aggregation_method": "last"},
    {"signal_key": "ecb_fx_usd_per_eur", "domain": "D", "source_id": "SRC-ECB-DATA", "description": "USD/EUR exchange rate from ECB", "unit": "ratio", "native_granularity": "daily", "aggregation_method": "last"},
    {"signal_key": "ecb_fx_jpy_per_eur", "domain": "D", "source_id": "SRC-ECB-DATA", "description": "JPY/EUR exchange rate from ECB", "unit": "ratio", "native_granularity": "daily", "aggregation_method": "last"},
    {"signal_key": "ecb_fx_gbp_per_eur", "domain": "D", "source_id": "SRC-ECB-DATA", "description": "GBP/EUR exchange rate from ECB", "unit": "ratio", "native_granularity": "daily", "aggregation_method": "last"},
    {"signal_key": "ecb_fx_chf_per_eur", "domain": "D", "source_id": "SRC-ECB-DATA", "description": "CHF/EUR exchange rate from ECB", "unit": "ratio", "native_granularity": "daily", "aggregation_method": "last"},
    {"signal_key": "ecb_fx_cny_per_eur", "domain": "D", "source_id": "SRC-ECB-DATA", "description": "CNY/EUR exchange rate from ECB", "unit": "ratio", "native_granularity": "daily", "aggregation_method": "last"},
    {"signal_key": "ecb_fx_try_per_eur", "domain": "D", "source_id": "SRC-ECB-DATA", "description": "TRY/EUR exchange rate from ECB", "unit": "ratio", "native_granularity": "daily", "aggregation_method": "last"},
    {"signal_key": "ecb_fx_zar_per_eur", "domain": "D", "source_id": "SRC-ECB-DATA", "description": "ZAR/EUR exchange rate from ECB", "unit": "ratio", "native_granularity": "daily", "aggregation_method": "last"},
    # Domain D — Eurostat (AP-14.3)
    {"signal_key": "eurostat_hicp_inflation", "domain": "D", "source_id": "SRC-EUROSTAT", "description": "Monthly HICP annual rate of change from Eurostat", "unit": "percent", "native_granularity": "monthly", "aggregation_method": "last"},
    {"signal_key": "eurostat_unemployment_rate", "domain": "D", "source_id": "SRC-EUROSTAT", "description": "Monthly unemployment rate from Eurostat", "unit": "percent", "native_granularity": "monthly", "aggregation_method": "last"},
    # Domain E — NVD CVE 2.0 (AP-14.4)
    {"signal_key": "nvd_cve_count_daily", "domain": "E", "source_id": "SRC-NVD-CVE", "description": "Daily CVE publication count from NVD", "unit": "count", "native_granularity": "daily", "aggregation_method": "sum"},
    {"signal_key": "nvd_avg_cvss_base", "domain": "E", "source_id": "SRC-NVD-CVE", "description": "Average CVSS base score of daily CVEs", "unit": "score", "native_granularity": "daily", "aggregation_method": "mean"},
    {"signal_key": "nvd_critical_cve_count", "domain": "E", "source_id": "SRC-NVD-CVE", "description": "Daily count of CRITICAL severity CVEs", "unit": "count", "native_granularity": "daily", "aggregation_method": "sum"},
    # Domain D — IMF DataMapper (AP-15.1)
    {"signal_key": "imf_cpi_inflation", "domain": "D", "source_id": "SRC-IMF-SDMX", "description": "CPI-based inflation rate from IMF DataMapper", "unit": "percent", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "imf_gdp_current_usd", "domain": "D", "source_id": "SRC-IMF-SDMX", "description": "GDP in current USD from IMF DataMapper", "unit": "usd", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "imf_current_account_pct_gdp", "domain": "D", "source_id": "SRC-IMF-SDMX", "description": "Current account balance as percent of GDP from IMF", "unit": "percent", "native_granularity": "yearly", "aggregation_method": "last"},
    # Domain C — WHO GHO (AP-15.2)
    {"signal_key": "who_life_expectancy", "domain": "C", "source_id": "SRC-WHO-GHO", "description": "Life expectancy at birth from WHO GHO", "unit": "years", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "who_under5_mortality", "domain": "C", "source_id": "SRC-WHO-GHO", "description": "Under-5 mortality rate from WHO GHO", "unit": "per_1000", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "who_maternal_mortality_ratio", "domain": "C", "source_id": "SRC-WHO-GHO", "description": "Maternal mortality ratio from WHO GHO", "unit": "per_100000", "native_granularity": "yearly", "aggregation_method": "last"},
    # Domain C — IDMC Displacement (AP-15.3)
    {"signal_key": "idmc_conflict_displacement", "domain": "C", "source_id": "SRC-IDMC", "description": "Internal displacement due to conflict from IDMC", "unit": "count", "native_granularity": "yearly", "aggregation_method": "sum"},
    {"signal_key": "idmc_disaster_displacement", "domain": "C", "source_id": "SRC-IDMC", "description": "Internal displacement due to disasters from IDMC", "unit": "count", "native_granularity": "yearly", "aggregation_method": "sum"},
    # Domain E — IODA Outages (AP-15.4)
    {"signal_key": "ioda_alert_count", "domain": "E", "source_id": "SRC-IODA", "description": "Internet outage alert count from IODA", "unit": "count", "native_granularity": "daily", "aggregation_method": "sum"},
    {"signal_key": "ioda_bgp_visibility_drop", "domain": "E", "source_id": "SRC-IODA", "description": "BGP visibility drop events from IODA", "unit": "count", "native_granularity": "daily", "aggregation_method": "sum"},
    # Domain E — OONI Censorship (AP-15.5)
    {"signal_key": "ooni_blocked_site_count", "domain": "E", "source_id": "SRC-OONI", "description": "Count of blocked sites detected by OONI", "unit": "count", "native_granularity": "daily", "aggregation_method": "sum"},
    {"signal_key": "ooni_censorship_incident_count", "domain": "E", "source_id": "SRC-OONI", "description": "Censorship incident count from OONI", "unit": "count", "native_granularity": "daily", "aggregation_method": "sum"},
    # Domain C — FEWS NET (AP-15.6)
    {"signal_key": "fewsnet_food_price_index", "domain": "C", "source_id": "SRC-FEWSNET", "description": "Food price index from FEWS NET", "unit": "index", "native_granularity": "monthly", "aggregation_method": "last"},
    {"signal_key": "fewsnet_ipc_phase", "domain": "C", "source_id": "SRC-FEWSNET", "description": "IPC food insecurity phase classification from FEWS NET", "unit": "score", "native_granularity": "monthly", "aggregation_method": "last"},
    # Domain B — OpenSanctions (AP-15.7)
    {"signal_key": "opensanctions_entity_count", "domain": "B", "source_id": "SRC-OPENSANCTIONS", "description": "Total sanctioned entity count from OpenSanctions", "unit": "count", "native_granularity": "daily", "aggregation_method": "last"},
    {"signal_key": "opensanctions_new_listings", "domain": "B", "source_id": "SRC-OPENSANCTIONS", "description": "Newly listed sanctioned entities from OpenSanctions", "unit": "count", "native_granularity": "daily", "aggregation_method": "sum"},
    # Domain B — HDX HAPI (AP-15.8)
    {"signal_key": "hdx_hapi_conflict_events", "domain": "B", "source_id": "SRC-HDX-HAPI", "description": "Conflict event count from HDX HAPI", "unit": "count", "native_granularity": "yearly", "aggregation_method": "sum"},
    {"signal_key": "hdx_hapi_humanitarian_needs", "domain": "B", "source_id": "SRC-HDX-HAPI", "description": "Humanitarian needs population count from HDX HAPI", "unit": "count", "native_granularity": "yearly", "aggregation_method": "last"},
    {"signal_key": "hdx_hapi_funding_coverage", "domain": "B", "source_id": "SRC-HDX-HAPI", "description": "Humanitarian funding coverage ratio from HDX HAPI", "unit": "ratio", "native_granularity": "yearly", "aggregation_method": "last"},
]


def load_signal_registry() -> list[SignalRegistryEntry]:
    """Load the canonical signal registry."""
    return [SignalRegistryEntry(**entry) for entry in _SIGNAL_REGISTRY]


def validate_signal_registry(entries: list[SignalRegistryEntry]) -> list[str]:
    """Validate the signal registry. Returns a list of issues (empty = OK)."""
    valid_domains = {"A", "B", "C", "D", "E"}
    valid_agg = {"sum", "mean", "max", "last", "count", "none"}
    issues: list[str] = []
    seen_keys: set[str] = set()
    for entry in entries:
        if not entry.signal_key:
            issues.append("Empty signal_key")
        if entry.signal_key in seen_keys:
            issues.append(f"{entry.signal_key}: duplicate signal_key")
        seen_keys.add(entry.signal_key)
        if entry.domain not in valid_domains:
            issues.append(f"{entry.signal_key}: invalid domain '{entry.domain}'")
        if entry.aggregation_method not in valid_agg:
            issues.append(f"{entry.signal_key}: invalid aggregation_method '{entry.aggregation_method}'")
    return issues
