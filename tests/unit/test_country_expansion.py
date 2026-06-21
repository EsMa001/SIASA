"""Tests for expanded country support in live runtime.

Validates that all countries in _SUPPORTED_LIVE_PILOT_COUNTRIES have valid
GDELT configuration, that pilot sets resolve correctly, and that the
country expansion meets minimum coverage targets.
"""

from __future__ import annotations

import pytest

from siasa.runs.live_runtime import (
    _SUPPORTED_LIVE_PILOT_COUNTRIES,
    _NAMED_LIVE_PILOT_SETS,
    _GOVERNED_LIVE_DOMAINS_BY_COUNTRY,
)


class TestCountryEntryValidity:
    """Every country entry must have valid gdelt_query and gdelt_code."""

    def test_all_countries_have_gdelt_query(self) -> None:
        for iso3, info in _SUPPORTED_LIVE_PILOT_COUNTRIES.items():
            assert "gdelt_query" in info, f"{iso3} missing gdelt_query"
            assert isinstance(info["gdelt_query"], str), f"{iso3} gdelt_query not str"
            assert len(info["gdelt_query"]) > 0, f"{iso3} gdelt_query is empty"

    def test_all_countries_have_gdelt_code(self) -> None:
        for iso3, info in _SUPPORTED_LIVE_PILOT_COUNTRIES.items():
            assert "gdelt_code" in info, f"{iso3} missing gdelt_code"
            assert isinstance(info["gdelt_code"], str), f"{iso3} gdelt_code not str"
            assert len(info["gdelt_code"]) == 2, (
                f"{iso3} gdelt_code '{info['gdelt_code']}' is not 2 characters"
            )

    def test_iso3_codes_are_3_chars_uppercase(self) -> None:
        for iso3 in _SUPPORTED_LIVE_PILOT_COUNTRIES:
            assert len(iso3) == 3, f"ISO3 code '{iso3}' is not 3 characters"
            assert iso3 == iso3.upper(), f"ISO3 code '{iso3}' is not uppercase"


class TestNoDuplicateGdeltCodes:
    """No two different ISO-3 countries should map to the same FIPS code."""

    def test_no_duplicate_gdelt_codes(self) -> None:
        code_to_iso: dict[str, str] = {}
        for iso3, info in _SUPPORTED_LIVE_PILOT_COUNTRIES.items():
            code = info["gdelt_code"]
            assert code not in code_to_iso, (
                f"Duplicate gdelt_code '{code}' used by both "
                f"{code_to_iso[code]} and {iso3}"
            )
            code_to_iso[code] = iso3


class TestPilotSetsResolveToValidCountries:
    """Every pilot set must only contain countries present in the supported dict."""

    def test_all_pilot_sets_resolve_to_supported_countries(self) -> None:
        for set_name, country_tuple in _NAMED_LIVE_PILOT_SETS.items():
            for iso3 in country_tuple:
                assert iso3 in _SUPPORTED_LIVE_PILOT_COUNTRIES, (
                    f"Pilot set '{set_name}' contains unsupported country '{iso3}'"
                )

    def test_all_pilot_sets_are_non_empty(self) -> None:
        for set_name, country_tuple in _NAMED_LIVE_PILOT_SETS.items():
            assert len(country_tuple) > 0, f"Pilot set '{set_name}' is empty"

    def test_no_duplicates_within_pilot_sets(self) -> None:
        for set_name, country_tuple in _NAMED_LIVE_PILOT_SETS.items():
            assert len(country_tuple) == len(set(country_tuple)), (
                f"Pilot set '{set_name}' has duplicate entries"
            )


class TestNewPilotSetsExistAndContainExpectedCountries:
    """Validate the newly-added regional pilot sets."""

    def test_latam_focus_exists(self) -> None:
        assert "latam-focus" in _NAMED_LIVE_PILOT_SETS

    def test_latam_focus_countries(self) -> None:
        expected = {"BRA", "MEX", "COL", "ARG", "VEN", "CHL", "PER", "ECU", "BOL", "CUB"}
        actual = set(_NAMED_LIVE_PILOT_SETS["latam-focus"])
        assert expected == actual, f"latam-focus mismatch: missing={expected - actual}, extra={actual - expected}"

    def test_africa_extended_exists(self) -> None:
        assert "africa-extended" in _NAMED_LIVE_PILOT_SETS

    def test_africa_extended_contains_existing_african_countries(self) -> None:
        existing_africa = {"EGY", "NGA", "SDN"}
        actual = set(_NAMED_LIVE_PILOT_SETS["africa-extended"])
        assert existing_africa.issubset(actual), (
            f"africa-extended missing existing countries: {existing_africa - actual}"
        )

    def test_africa_extended_contains_new_african_countries(self) -> None:
        new_africa = {"ZAF", "KEN", "ETH", "TZA", "COD", "MOZ", "SOM", "LBY", "MAR", "DZA", "TUN", "GHA", "CMR", "AGO", "ZWE"}
        actual = set(_NAMED_LIVE_PILOT_SETS["africa-extended"])
        assert new_africa.issubset(actual), (
            f"africa-extended missing new countries: {new_africa - actual}"
        )

    def test_europe_extended_exists(self) -> None:
        assert "europe-extended" in _NAMED_LIVE_PILOT_SETS

    def test_europe_extended_contains_existing_european_countries(self) -> None:
        existing_europe = {"UKR", "POL", "DEU", "EST", "FIN", "CHE", "NLD", "SWE", "NOR", "PRT", "IRL"}
        actual = set(_NAMED_LIVE_PILOT_SETS["europe-extended"])
        assert existing_europe.issubset(actual), (
            f"europe-extended missing existing countries: {existing_europe - actual}"
        )

    def test_europe_extended_contains_new_european_countries(self) -> None:
        new_europe = {"FRA", "GBR", "ITA", "ESP", "GRC", "ROU", "BGR", "SRB", "HUN", "CZE", "AUT", "BEL", "DNK"}
        actual = set(_NAMED_LIVE_PILOT_SETS["europe-extended"])
        assert new_europe.issubset(actual), (
            f"europe-extended missing new countries: {new_europe - actual}"
        )

    def test_asia_extended_exists(self) -> None:
        assert "asia-extended" in _NAMED_LIVE_PILOT_SETS

    def test_asia_extended_contains_key_asian_countries(self) -> None:
        key_asia = {"CHN", "IND", "JPN", "KOR", "THA", "VNM", "PHL", "IDN", "KAZ"}
        actual = set(_NAMED_LIVE_PILOT_SETS["asia-extended"])
        assert key_asia.issubset(actual), (
            f"asia-extended missing key countries: {key_asia - actual}"
        )

    def test_global_broad_exists(self) -> None:
        assert "global-broad" in _NAMED_LIVE_PILOT_SETS

    def test_global_broad_contains_all_supported_countries(self) -> None:
        all_supported = set(_SUPPORTED_LIVE_PILOT_COUNTRIES.keys())
        actual = set(_NAMED_LIVE_PILOT_SETS["global-broad"])
        assert all_supported == actual, (
            f"global-broad mismatch: missing={all_supported - actual}, extra={actual - all_supported}"
        )


class TestExistingPilotSetsUnchanged:
    """Original pilot sets must not be modified."""

    def test_representative_unchanged(self) -> None:
        assert set(_NAMED_LIVE_PILOT_SETS["representative"]) == {"UKR", "POL", "ISR", "TWN"}

    def test_core_focus_initial_unchanged(self) -> None:
        assert set(_NAMED_LIVE_PILOT_SETS["core-focus-initial"]) == {
            "UKR", "RUS", "CHN", "TWN", "ISR", "POL"
        }

    def test_mvp_complete_unchanged(self) -> None:
        expected = {
            "UKR", "RUS", "CHN", "TWN", "IRN", "ISR", "TUR", "IND", "PAK", "GEO",
            "POL", "USA", "DEU", "EST", "FIN", "SAU", "QAT", "EGY", "NGA", "SDN",
            "MMR", "NOR", "CHE", "SWE", "NLD", "IRL", "PRT", "NZL", "CAN", "AUS",
        }
        assert set(_NAMED_LIVE_PILOT_SETS["mvp-complete"]) == expected


class TestTotalCountryCoverage:
    """Total supported countries must meet minimum expansion target."""

    def test_total_country_count_at_least_70(self) -> None:
        count = len(_SUPPORTED_LIVE_PILOT_COUNTRIES)
        assert count >= 70, f"Only {count} countries supported, need >= 70"

    def test_total_country_count_realistic_upper_bound(self) -> None:
        count = len(_SUPPORTED_LIVE_PILOT_COUNTRIES)
        assert count <= 200, f"Suspiciously high count: {count}"


class TestDomainMappingConsistency:
    """Every supported country should have a domain mapping."""

    def test_all_supported_countries_have_domain_mapping(self) -> None:
        for iso3 in _SUPPORTED_LIVE_PILOT_COUNTRIES:
            assert iso3 in _GOVERNED_LIVE_DOMAINS_BY_COUNTRY, (
                f"Country {iso3} has no entry in _GOVERNED_LIVE_DOMAINS_BY_COUNTRY"
            )

    def test_domain_mapping_values_are_valid(self) -> None:
        valid_domains = {"A", "B", "C", "D", "E"}
        for iso3, domains in _GOVERNED_LIVE_DOMAINS_BY_COUNTRY.items():
            assert isinstance(domains, list), f"{iso3} domains not a list"
            assert len(domains) > 0, f"{iso3} has empty domain list"
            for d in domains:
                assert d in valid_domains, f"{iso3} has invalid domain '{d}'"
