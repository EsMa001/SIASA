"""Tests for WHO GHO adapter (SwR-077, AP-15.2).

TC-SwR-077-001: Verify WHOGHOAdapter fetches life expectancy, under-5 mortality,
and maternal mortality from the WHO GHO Azure CDN API, normalizes to
NormalizedRecord-compatible dicts, handles OData JSON parsing, errors, and retries.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from siasa.adapters.who_gho import (
    WHOGHOAdapter,
    _parse_gho_response,
    _ISO3_TO_ISO2,
)
from siasa.adapters.base import FetchResult


# ── Fixtures ──────────────────────────────────────────────────────────────

# Minimal GHO OData response for life expectancy (WHOSIS_000001)
SAMPLE_LIFE_EXP_RESPONSE = {
    "@odata.context": "https://ghoapi.azureedge.net/api/$metadata#WHOSIS_000001",
    "value": [
        {
            "IndicatorCode": "WHOSIS_000001",
            "SpatialDim": "DEU",
            "Dim1": "SEX_BTSX",
            "TimeDim": 2021,
            "NumericValue": 80.6,
            "TimeDimensionValue": "2021",
        },
        {
            "IndicatorCode": "WHOSIS_000001",
            "SpatialDim": "DEU",
            "Dim1": "SEX_BTSX",
            "TimeDim": 2019,
            "NumericValue": 81.3,
            "TimeDimensionValue": "2019",
        },
        {
            "IndicatorCode": "WHOSIS_000001",
            "SpatialDim": "DEU",
            "Dim1": "SEX_MLE",
            "TimeDim": 2021,
            "NumericValue": 78.1,
            "TimeDimensionValue": "2021",
        },
        {
            "IndicatorCode": "WHOSIS_000001",
            "SpatialDim": "NGA",
            "Dim1": "SEX_BTSX",
            "TimeDim": 2021,
            "NumericValue": 52.7,
            "TimeDimensionValue": "2021",
        },
    ],
}

# Under-5 mortality (MDG_0000000007)
SAMPLE_U5MR_RESPONSE = {
    "@odata.context": "https://ghoapi.azureedge.net/api/$metadata#MDG_0000000007",
    "value": [
        {
            "IndicatorCode": "MDG_0000000007",
            "SpatialDim": "DEU",
            "Dim1": "SEX_BTSX",
            "TimeDim": 2022,
            "NumericValue": 3.5,
            "TimeDimensionValue": "2022",
        },
        {
            "IndicatorCode": "MDG_0000000007",
            "SpatialDim": "NGA",
            "Dim1": "SEX_BTSX",
            "TimeDim": 2022,
            "NumericValue": 107.4,
            "TimeDimensionValue": "2022",
        },
    ],
}

# Maternal mortality (MDG_0000000026)
SAMPLE_MMR_RESPONSE = {
    "@odata.context": "https://ghoapi.azureedge.net/api/$metadata#MDG_0000000026",
    "value": [
        {
            "IndicatorCode": "MDG_0000000026",
            "SpatialDim": "DEU",
            "Dim1": None,
            "TimeDim": 2020,
            "NumericValue": 4.0,
            "TimeDimensionValue": "2020",
        },
        {
            "IndicatorCode": "MDG_0000000026",
            "SpatialDim": "NGA",
            "Dim1": None,
            "TimeDim": 2020,
            "NumericValue": 1047.0,
            "TimeDimensionValue": "2020",
        },
    ],
}

EMPTY_RESPONSE = {
    "@odata.context": "https://ghoapi.azureedge.net/api/$metadata#Empty",
    "value": [],
}

MALFORMED_RESPONSE = {"unexpected": "data"}

FIXED_NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)

# Map indicator → mock response
INDICATOR_RESPONSES = {
    "WHOSIS_000001": SAMPLE_LIFE_EXP_RESPONSE,
    "MDG_0000000007": SAMPLE_U5MR_RESPONSE,
    "MDG_0000000026": SAMPLE_MMR_RESPONSE,
}


def _route_fetch(url: str) -> object:
    """Route mock fetch to correct response based on indicator in URL."""
    for indicator, response in INDICATOR_RESPONSES.items():
        if indicator in url:
            return response
    return EMPTY_RESPONSE


def _make_adapter(
    fetch_fn=None,
    country_ids=None,
    now_fn=None,
    max_retries=3,
):
    if country_ids is None:
        country_ids = ("DEU", "NGA")
    if now_fn is None:
        now_fn = lambda: FIXED_NOW  # noqa: E731
    return WHOGHOAdapter(
        country_ids=country_ids,
        fetch_json=fetch_fn or _route_fetch,
        now_provider=now_fn,
        retry_sleep=lambda _: None,
        max_retries=max_retries,
    )


# ── 1. Basic fetch + record structure ────────────────────────────────────

class TestBasicFetch:
    def test_returns_fetch_result(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        assert isinstance(result, FetchResult)
        assert result.is_success is True

    def test_records_have_required_fields(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        assert len(result.records) > 0
        rec = result.records[0]
        required = {"country_id", "period", "signal_key", "value", "quality_flag"}
        assert required.issubset(set(rec.keys()))

    def test_signal_keys_contain_who_prefix(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["signal_key"].startswith("who_")

    def test_values_are_numeric(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert isinstance(rec["value"], (int, float))


# ── 2. Life expectancy parsing ───────────────────────────────────────────

class TestLifeExpectancyParsing:
    def test_life_exp_records_extracted(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        le_records = [r for r in result.records if r["signal_key"] == "who_life_expectancy_years"]
        assert len(le_records) > 0

    def test_life_exp_filters_both_sexes_only(self):
        """Should only extract SEX_BTSX records, not SEX_MLE/FMLE."""
        adapter = _make_adapter(country_ids=("DEU",))
        result = adapter.fetch()
        le_records = [r for r in result.records if r["signal_key"] == "who_life_expectancy_years"]
        assert len(le_records) == 1  # Only BTSX, not MLE

    def test_life_exp_uses_latest_year(self):
        adapter = _make_adapter(country_ids=("DEU",))
        result = adapter.fetch()
        le_records = [r for r in result.records if r["signal_key"] == "who_life_expectancy_years"]
        assert le_records[0]["period"] == "2021"
        assert le_records[0]["value"] == 80.6

    def test_life_exp_multiple_countries(self):
        adapter = _make_adapter(country_ids=("DEU", "NGA"))
        result = adapter.fetch()
        le_records = [r for r in result.records if r["signal_key"] == "who_life_expectancy_years"]
        countries = {r["country_id"] for r in le_records}
        assert "DEU" in countries
        assert "NGA" in countries


# ── 3. Under-5 mortality parsing ─────────────────────────────────────────

class TestUnder5MortalityParsing:
    def test_u5mr_records_extracted(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        u5_records = [r for r in result.records if r["signal_key"] == "who_under5_mortality_per1000"]
        assert len(u5_records) > 0

    def test_u5mr_value(self):
        adapter = _make_adapter(country_ids=("NGA",))
        result = adapter.fetch()
        u5_records = [r for r in result.records if r["signal_key"] == "who_under5_mortality_per1000"]
        assert u5_records[0]["value"] == 107.4


# ── 4. Maternal mortality parsing ────────────────────────────────────────

class TestMaternalMortalityParsing:
    def test_mmr_records_extracted(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        mmr_records = [r for r in result.records if r["signal_key"] == "who_maternal_mortality_per100k"]
        assert len(mmr_records) > 0

    def test_mmr_value(self):
        adapter = _make_adapter(country_ids=("NGA",))
        result = adapter.fetch()
        mmr_records = [r for r in result.records if r["signal_key"] == "who_maternal_mortality_per100k"]
        assert mmr_records[0]["value"] == 1047.0

    def test_mmr_handles_null_dim1(self):
        """Maternal mortality has Dim1=None — should still be parsed."""
        adapter = _make_adapter(country_ids=("DEU",))
        result = adapter.fetch()
        mmr_records = [r for r in result.records if r["signal_key"] == "who_maternal_mortality_per100k"]
        assert len(mmr_records) == 1


# ── 5. OData response parsing ───────────────────────────────────────────

class TestODataParsing:
    def test_parse_gho_response_extracts_values(self):
        records = _parse_gho_response(SAMPLE_LIFE_EXP_RESPONSE, sex_filter="SEX_BTSX")
        assert len(records) > 0

    def test_parse_gho_empty_response(self):
        records = _parse_gho_response(EMPTY_RESPONSE)
        assert records == []

    def test_parse_gho_malformed_response(self):
        records = _parse_gho_response(MALFORMED_RESPONSE)
        assert records == []

    def test_parse_gho_extracts_latest_per_country(self):
        records = _parse_gho_response(SAMPLE_LIFE_EXP_RESPONSE, sex_filter="SEX_BTSX")
        deu_records = [r for r in records if r["country_code"] == "DEU"]
        assert len(deu_records) == 1
        assert deu_records[0]["year"] == 2021

    def test_parse_gho_filters_by_sex(self):
        all_records = _parse_gho_response(SAMPLE_LIFE_EXP_RESPONSE, sex_filter="SEX_BTSX")
        deu_count = sum(1 for r in all_records if r["country_code"] == "DEU")
        assert deu_count == 1  # Only BTSX, not MLE


# ── 6. Country code mapping (ISO3 → WHO/ISO2) ───────────────────────────

class TestCountryCodeMapping:
    def test_iso3_mapping_exists_for_common_countries(self):
        assert "DEU" in _ISO3_TO_ISO2
        assert "USA" in _ISO3_TO_ISO2
        assert "NGA" in _ISO3_TO_ISO2

    def test_mapping_returns_correct_iso2(self):
        assert _ISO3_TO_ISO2["DEU"] == "DEU"  # WHO uses ISO-3 alpha directly
        # WHO API actually uses ISO-3 alpha codes for SpatialDim

    def test_only_configured_countries_returned(self):
        adapter = _make_adapter(country_ids=("DEU",))
        result = adapter.fetch()
        country_ids = {r["country_id"] for r in result.records}
        assert country_ids == {"DEU"}

    def test_empty_country_ids_returns_empty(self):
        adapter = _make_adapter(country_ids=())
        result = adapter.fetch()
        assert result.is_success is True
        assert result.records == []

    def test_unknown_country_skipped_gracefully(self):
        adapter = _make_adapter(country_ids=("XYZ",))
        result = adapter.fetch()
        assert result.is_success is True
        assert result.records == []


# ── 7. Period handling ──────────────────────────────────────────────────

class TestPeriodHandling:
    def test_period_is_year_string(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert isinstance(rec["period"], str)
            assert len(rec["period"]) == 4  # "2021" format
            int(rec["period"])  # Should parse as integer


# ── 8. Error handling ────────────────────────────────────────────────────

class TestErrorHandling:
    def test_api_error_returns_unsuccessful(self):
        def fail_fetch(url):
            raise ConnectionError("timeout")
        adapter = _make_adapter(fetch_fn=fail_fetch, max_retries=0)
        result = adapter.fetch()
        assert result.is_success is False
        assert result.records == []

    def test_malformed_json_handled_gracefully(self):
        adapter = _make_adapter(
            fetch_fn=lambda url: {"broken": True},
        )
        result = adapter.fetch()
        assert isinstance(result, FetchResult)
        assert result.is_success is True

    def test_partial_failure_returns_partial_records(self):
        """If one indicator fails, others should still work."""
        def partial_fail_fetch(url):
            if "MDG_0000000007" in url:
                raise ConnectionError("U5MR API down")
            return _route_fetch(url)
        adapter = _make_adapter(fetch_fn=partial_fail_fetch, max_retries=0)
        result = adapter.fetch()
        assert result.is_success is True
        assert len(result.records) > 0
        signal_keys = {r["signal_key"] for r in result.records}
        assert "who_life_expectancy_years" in signal_keys
        assert "who_under5_mortality_per1000" not in signal_keys


# ── 9. Retry logic ──────────────────────────────────────────────────────

class TestRetryLogic:
    def test_retries_on_transient_failure(self):
        call_count = 0
        def flaky_fetch(url):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return _route_fetch(url)
        adapter = _make_adapter(fetch_fn=flaky_fetch, max_retries=3)
        result = adapter.fetch()
        assert result.is_success is True
        assert call_count >= 3

    def test_retry_sleep_called(self):
        sleep_calls = []
        def fail_fetch(url):
            raise ConnectionError("fail")
        adapter = _make_adapter(fetch_fn=fail_fetch, max_retries=1)
        adapter.retry_sleep = lambda d: sleep_calls.append(d)
        adapter.fetch()
        assert len(sleep_calls) >= 1

    def test_exponential_backoff(self):
        sleep_calls = []
        def fail_fetch(url):
            raise ConnectionError("fail")
        adapter = _make_adapter(fetch_fn=fail_fetch, max_retries=3)
        adapter.retry_sleep = lambda d: sleep_calls.append(d)
        adapter.fetch()
        if len(sleep_calls) >= 2:
            assert sleep_calls[1] >= sleep_calls[0]


# ── 10. Source metadata ─────────────────────────────────────────────────

class TestSourceMetadata:
    def test_source_id(self):
        adapter = _make_adapter()
        assert adapter.source_id == "SRC-WHO-GHO"

    def test_domain_is_C(self):
        """Health indicators belong to Domain C (Human Development)."""
        adapter = _make_adapter()
        assert adapter.domain == "C"

    def test_quality_flag(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["quality_flag"] == "who_gho_api"


# ── 11. Diagnostics ────────────────────────────────────────────────────

class TestDiagnostics:
    def test_success_diagnostics(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        assert "who" in result.diagnostics.lower()

    def test_empty_diagnostics(self):
        adapter = _make_adapter(country_ids=())
        result = adapter.fetch()
        assert "no" in result.diagnostics.lower() or "0" in result.diagnostics

    def test_partial_error_diagnostics(self):
        def partial_fail(url):
            if "MDG_0000000007" in url:
                raise ConnectionError("U5MR down")
            return _route_fetch(url)
        adapter = _make_adapter(fetch_fn=partial_fail, max_retries=0)
        result = adapter.fetch()
        assert "partial" in result.diagnostics.lower() or "error" in result.diagnostics.lower()


# ── 12. Freshness metadata ────────────────────────────────────────────

class TestFreshnessMetadata:
    def test_freshness_hours_in_records(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert "freshness_hours" in rec
            assert isinstance(rec["freshness_hours"], (int, float))

    def test_expected_source_count(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec.get("expected_source_count") == 1


# ── 13. Multiple indicators aggregation ─────────────────────────────────

class TestMultipleIndicators:
    def test_all_three_indicators_returned_for_country(self):
        """DEU should have all 3 indicators: LE, U5MR, MMR."""
        adapter = _make_adapter(country_ids=("DEU",))
        result = adapter.fetch()
        signals = {r["signal_key"] for r in result.records}
        assert "who_life_expectancy_years" in signals
        assert "who_under5_mortality_per1000" in signals
        assert "who_maternal_mortality_per100k" in signals

    def test_record_count_for_two_countries(self):
        """DEU + NGA: 3 indicators each = 6 records."""
        adapter = _make_adapter(country_ids=("DEU", "NGA"))
        result = adapter.fetch()
        assert len(result.records) == 6


# ── 14. Injectable fetch function ───────────────────────────────────────

class TestInjectableFetch:
    def test_custom_fetch_function_used(self):
        calls = []
        def tracking_fetch(url):
            calls.append(url)
            return _route_fetch(url)
        adapter = _make_adapter(fetch_fn=tracking_fetch)
        adapter.fetch()
        assert len(calls) >= 3  # At least 3 indicator calls

    def test_url_contains_indicator_code(self):
        calls = []
        def tracking_fetch(url):
            calls.append(url)
            return _route_fetch(url)
        adapter = _make_adapter(fetch_fn=tracking_fetch)
        adapter.fetch()
        url_text = " ".join(calls)
        assert "WHOSIS_000001" in url_text
        assert "MDG_0000000007" in url_text
        assert "MDG_0000000026" in url_text

    def test_url_contains_country_filter(self):
        """URL should filter by country ISO code."""
        calls = []
        def tracking_fetch(url):
            calls.append(url)
            return _route_fetch(url)
        adapter = _make_adapter(fetch_fn=tracking_fetch, country_ids=("DEU",))
        adapter.fetch()
        # Should have DEU in the filter query
        assert any("DEU" in url for url in calls)
