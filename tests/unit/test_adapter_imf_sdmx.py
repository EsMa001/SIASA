"""Tests for IMF DataMapper adapter (SwR-076, AP-15.1).

TC-SwR-076-001: Verify IMFDataMapperAdapter fetches CPI inflation, GDP growth,
and current account balance from the IMF DataMapper API, normalizes to
NormalizedRecord-compatible dicts, handles JSON parsing, errors, and retries.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from siasa.adapters.imf_sdmx import (
    IMFDataMapperAdapter,
    _parse_datamapper_response,
)
from siasa.adapters.base import FetchResult


# ── Fixtures ──────────────────────────────────────────────────────────────

# Minimal IMF DataMapper API response for CPI inflation (PCPIPCH)
SAMPLE_CPI_RESPONSE = {
    "values": {
        "PCPIPCH": {
            "DEU": {"2023": 5.9, "2024": 2.9},
            "USA": {"2023": 4.1, "2024": 3.0},
            "NGA": {"2023": 24.7, "2024": 28.3},
        }
    },
    "api": {"version": "1", "output-method": "json"},
}

# GDP growth response (NGDP_RPCH)
SAMPLE_GDP_RESPONSE = {
    "values": {
        "NGDP_RPCH": {
            "DEU": {"2023": -0.3, "2024": 0.2},
            "USA": {"2023": 2.5, "2024": 2.8},
            "NGA": {"2023": 2.9, "2024": 3.3},
        }
    },
    "api": {"version": "1", "output-method": "json"},
}

# Current account balance (BCA_NGDPD)
SAMPLE_CA_RESPONSE = {
    "values": {
        "BCA_NGDPD": {
            "DEU": {"2023": 6.7, "2024": 6.3},
            "USA": {"2023": -3.3, "2024": -3.1},
        }
    },
    "api": {"version": "1", "output-method": "json"},
}

EMPTY_RESPONSE = {
    "values": {"PCPIPCH": {}},
    "api": {"version": "1", "output-method": "json"},
}

MALFORMED_RESPONSE = {"unexpected": "data"}

FIXED_NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)

# Map indicator → mock response
INDICATOR_RESPONSES = {
    "PCPIPCH": SAMPLE_CPI_RESPONSE,
    "NGDP_RPCH": SAMPLE_GDP_RESPONSE,
    "BCA_NGDPD": SAMPLE_CA_RESPONSE,
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
        country_ids = ("DEU", "USA", "NGA")
    if now_fn is None:
        now_fn = lambda: FIXED_NOW  # noqa: E731
    return IMFDataMapperAdapter(
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

    def test_signal_keys_contain_imf_prefix(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["signal_key"].startswith("imf_")

    def test_values_are_numeric(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert isinstance(rec["value"], (int, float))


# ── 2. CPI inflation parsing ────────────────────────────────────────────

class TestCPIParsing:
    def test_cpi_records_extracted(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        cpi_records = [r for r in result.records if "cpi" in r["signal_key"]]
        assert len(cpi_records) > 0

    def test_cpi_signal_key_format(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        cpi_records = [r for r in result.records if "cpi" in r["signal_key"]]
        for rec in cpi_records:
            assert rec["signal_key"] == "imf_cpi_inflation_pct"

    def test_cpi_value_matches_response(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        deu_cpi = [r for r in result.records
                   if r["signal_key"] == "imf_cpi_inflation_pct"
                   and r["country_id"] == "DEU"]
        assert len(deu_cpi) == 1
        # Should be the latest year value
        assert deu_cpi[0]["value"] == 2.9

    def test_cpi_period_is_latest_year(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        deu_cpi = [r for r in result.records
                   if r["signal_key"] == "imf_cpi_inflation_pct"
                   and r["country_id"] == "DEU"]
        assert deu_cpi[0]["period"] == "2024"


# ── 3. GDP growth parsing ────────────────────────────────────────────────

class TestGDPParsing:
    def test_gdp_records_extracted(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        gdp_records = [r for r in result.records if r["signal_key"] == "imf_gdp_growth_pct"]
        assert len(gdp_records) > 0

    def test_gdp_signal_key_format(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        gdp_records = [r for r in result.records if r["signal_key"] == "imf_gdp_growth_pct"]
        assert len(gdp_records) > 0
        for rec in gdp_records:
            assert rec["signal_key"] == "imf_gdp_growth_pct"

    def test_gdp_negative_value(self):
        """DEU GDP 2024 is 0.2, 2023 is -0.3 — latest should be 0.2."""
        adapter = _make_adapter()
        result = adapter.fetch()
        deu_gdp = [r for r in result.records
                   if r["signal_key"] == "imf_gdp_growth_pct"
                   and r["country_id"] == "DEU"]
        assert len(deu_gdp) == 1
        assert deu_gdp[0]["value"] == 0.2


# ── 4. Current account balance parsing ───────────────────────────────────

class TestCurrentAccountParsing:
    def test_ca_records_extracted(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        ca_records = [r for r in result.records if "current_account" in r["signal_key"]]
        assert len(ca_records) > 0

    def test_ca_signal_key_format(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        ca_records = [r for r in result.records if "current_account" in r["signal_key"]]
        for rec in ca_records:
            assert rec["signal_key"] == "imf_current_account_pct_gdp"

    def test_ca_country_without_data_skipped(self):
        """NGA has no current account data in sample — should be skipped."""
        adapter = _make_adapter()
        result = adapter.fetch()
        nga_ca = [r for r in result.records
                  if r["signal_key"] == "imf_current_account_pct_gdp"
                  and r["country_id"] == "NGA"]
        assert len(nga_ca) == 0


# ── 5. DataMapper response parsing ──────────────────────────────────────

class TestDataMapperParsing:
    def test_parse_datamapper_response_extracts_values(self):
        records = _parse_datamapper_response(SAMPLE_CPI_RESPONSE, "PCPIPCH")
        assert len(records) > 0

    def test_parse_datamapper_empty_response(self):
        records = _parse_datamapper_response(EMPTY_RESPONSE, "PCPIPCH")
        assert records == []

    def test_parse_datamapper_malformed_response(self):
        records = _parse_datamapper_response(MALFORMED_RESPONSE, "PCPIPCH")
        assert records == []

    def test_parse_datamapper_extracts_latest_year(self):
        records = _parse_datamapper_response(SAMPLE_CPI_RESPONSE, "PCPIPCH")
        deu_records = [r for r in records if r["country_id"] == "DEU"]
        assert len(deu_records) == 1
        assert deu_records[0]["year"] == "2024"
        assert deu_records[0]["value"] == 2.9

    def test_parse_datamapper_skips_null_values(self):
        """Response where values field maps to null."""
        response = {
            "values": {"PCPIPCH": {"DEU": {"2024": None}}},
        }
        records = _parse_datamapper_response(response, "PCPIPCH")
        assert records == []


# ── 6. Country mapping (ISO3) ────────────────────────────────────────────

class TestCountryMapping:
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
        # XYZ is not in the mock data, so no records
        assert result.records == []


# ── 7. Period handling ──────────────────────────────────────────────────

class TestPeriodHandling:
    def test_period_is_year_string(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert isinstance(rec["period"], str)
            assert len(rec["period"]) == 4  # "2024" format
            int(rec["period"])  # Should parse as integer

    def test_period_defaults_to_empty_when_no_data(self):
        """When no years available, period should default to empty string."""
        def empty_fetch(url):
            return EMPTY_RESPONSE
        adapter = _make_adapter(fetch_fn=empty_fetch, country_ids=("DEU",))
        result = adapter.fetch()
        assert result.records == []


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
        # Should succeed but with no/few records
        assert result.is_success is True

    def test_partial_failure_returns_partial_records(self):
        """If one indicator fails, others should still work."""
        call_count = 0
        def partial_fail_fetch(url):
            nonlocal call_count
            call_count += 1
            if "NGDP_RPCH" in url:
                raise ConnectionError("GDP API down")
            return _route_fetch(url)
        adapter = _make_adapter(fetch_fn=partial_fail_fetch, max_retries=0)
        result = adapter.fetch()
        assert result.is_success is True
        assert len(result.records) > 0
        # Should have CPI and CA but no GDP
        signal_keys = {r["signal_key"] for r in result.records}
        assert "imf_cpi_inflation_pct" in signal_keys
        assert "imf_gdp_growth_pct" not in signal_keys


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
        # Check backoff increases
        if len(sleep_calls) >= 2:
            assert sleep_calls[1] >= sleep_calls[0]


# ── 10. Source metadata ─────────────────────────────────────────────────

class TestSourceMetadata:
    def test_source_id(self):
        adapter = _make_adapter()
        assert adapter.source_id == "SRC-IMF-DATAMAPPER"

    def test_domain_is_D(self):
        adapter = _make_adapter()
        assert adapter.domain == "D"

    def test_quality_flag(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["quality_flag"] == "imf_datamapper_api"


# ── 11. Diagnostics ────────────────────────────────────────────────────

class TestDiagnostics:
    def test_success_diagnostics(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        assert "imf" in result.diagnostics.lower()

    def test_empty_diagnostics(self):
        adapter = _make_adapter(country_ids=())
        result = adapter.fetch()
        assert "no" in result.diagnostics.lower() or "empty" in result.diagnostics.lower() or "0" in result.diagnostics

    def test_partial_error_diagnostics(self):
        def partial_fail(url):
            if "NGDP_RPCH" in url:
                raise ConnectionError("GDP down")
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
        """DEU and USA should have all 3 indicators: CPI, GDP, CA."""
        adapter = _make_adapter(country_ids=("DEU", "USA"))
        result = adapter.fetch()
        deu_signals = {r["signal_key"] for r in result.records
                       if r["country_id"] == "DEU"}
        assert "imf_cpi_inflation_pct" in deu_signals
        assert "imf_gdp_growth_pct" in deu_signals
        assert "imf_current_account_pct_gdp" in deu_signals

    def test_record_count_matches_countries_x_indicators(self):
        """DEU+USA: 3 indicators each = 6 records.
        NGA: 2 indicators (no CA data) = 2 records.
        Total: 8."""
        adapter = _make_adapter(country_ids=("DEU", "USA", "NGA"))
        result = adapter.fetch()
        assert len(result.records) == 8


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
        assert "PCPIPCH" in url_text
        assert "NGDP_RPCH" in url_text
        assert "BCA_NGDPD" in url_text
