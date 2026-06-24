"""Tests for ECB Data adapter (SwR-073, AP-14.2).

TC-SwR-073-001: Verify ECBDataAdapter fetches exchange rates and key interest
rates from ECB SDMX-JSON API, normalizes to NormalizedRecord-compatible dicts,
handles SDMX parsing, errors, and retries.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from siasa.adapters.ecb_data import (
    ECBDataAdapter,
    _parse_sdmx_observations,
)
from siasa.adapters.base import FetchResult


# ── Fixtures ──────────────────────────────────────────────────────────────

# Minimal SDMX-JSON response for EXR (exchange rates)
SAMPLE_FX_RESPONSE = {
    "header": {"id": "test", "prepared": "2026-06-05T12:00:00"},
    "dataSets": [{
        "series": {
            "0:0:0:0:0": {
                "observations": {"0": [1.0845]}
            },
            "0:1:0:0:0": {
                "observations": {"0": [157.32]}
            },
        }
    }],
    "structure": {
        "dimensions": {
            "series": [
                {"id": "FREQ", "values": [{"id": "D"}]},
                {"id": "CURRENCY", "values": [{"id": "USD"}, {"id": "JPY"}]},
                {"id": "CURRENCY_DENOM", "values": [{"id": "EUR"}]},
                {"id": "EXR_TYPE", "values": [{"id": "SP00"}]},
                {"id": "EXR_SUFFIX", "values": [{"id": "A"}]},
            ],
            "observation": [
                {"id": "TIME_PERIOD", "values": [{"id": "2026-06-05"}]},
            ],
        }
    },
}

# Minimal SDMX-JSON response for key interest rate
SAMPLE_RATE_RESPONSE = {
    "header": {"id": "test", "prepared": "2026-06-05T12:00:00"},
    "dataSets": [{
        "series": {
            "0:0:0:0": {
                "observations": {"0": [4.25]}
            },
        }
    }],
    "structure": {
        "dimensions": {
            "series": [
                {"id": "FREQ", "values": [{"id": "D"}]},
                {"id": "FM_TYPE", "values": [{"id": "MRR"}]},
                {"id": "PROVIDER_FM_ID", "values": [{"id": "4F"}]},
                {"id": "DATA_TYPE_FM", "values": [{"id": "LEV"}]},
            ],
            "observation": [
                {"id": "TIME_PERIOD", "values": [{"id": "2026-06-05"}]},
            ],
        }
    },
}

EMPTY_RESPONSE = {
    "header": {"id": "test"},
    "dataSets": [{"series": {}}],
    "structure": {"dimensions": {"series": [], "observation": []}},
}

FIXED_NOW = datetime(2026, 6, 5, 12, 0, 0, tzinfo=timezone.utc)


def _make_adapter(
    fetch_fn=None,
    country_ids=None,
    now_fn=None,
    max_retries=3,
):
    if country_ids is None:
        country_ids = ("DEU", "USA", "JPN")
    if now_fn is None:
        now_fn = lambda: FIXED_NOW  # noqa: E731
    return ECBDataAdapter(
        country_ids=country_ids,
        fetch_json=fetch_fn or (lambda url: SAMPLE_FX_RESPONSE),
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

    def test_signal_keys_contain_ecb_prefix(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["signal_key"].startswith("ecb_")

    def test_values_are_numeric(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert isinstance(rec["value"], (int, float))


# ── 2. FX rate parsing ───────────────────────────────────────────────────

class TestFXParsing:
    def test_fx_records_extracted_from_sdmx(self):
        """SDMX FX response should produce records for mapped currencies."""
        def route_fetch(url):
            if "EXR" in url:
                return SAMPLE_FX_RESPONSE
            return SAMPLE_RATE_RESPONSE
        adapter = _make_adapter(fetch_fn=route_fetch)
        result = adapter.fetch()
        fx_records = [r for r in result.records if "fx_" in r["signal_key"]]
        assert len(fx_records) > 0

    def test_fx_signal_key_contains_currency(self):
        def route_fetch(url):
            if "EXR" in url:
                return SAMPLE_FX_RESPONSE
            return SAMPLE_RATE_RESPONSE
        adapter = _make_adapter(fetch_fn=route_fetch)
        result = adapter.fetch()
        fx_records = [r for r in result.records if "fx_" in r["signal_key"]]
        signal_keys = {r["signal_key"] for r in fx_records}
        # Should have USD and/or JPY
        assert any("usd" in k or "jpy" in k for k in signal_keys)


# ── 3. Key rate parsing ──────────────────────────────────────────────────

class TestKeyRateParsing:
    def test_key_rate_records_extracted(self):
        def route_fetch(url):
            if "EXR" in url:
                return SAMPLE_FX_RESPONSE
            return SAMPLE_RATE_RESPONSE
        adapter = _make_adapter(fetch_fn=route_fetch)
        result = adapter.fetch()
        rate_records = [r for r in result.records if "key_rate" in r["signal_key"]]
        assert len(rate_records) > 0

    def test_key_rate_value(self):
        def route_fetch(url):
            if "EXR" in url:
                return SAMPLE_FX_RESPONSE
            return SAMPLE_RATE_RESPONSE
        adapter = _make_adapter(fetch_fn=route_fetch)
        result = adapter.fetch()
        rate_records = [r for r in result.records if "key_rate" in r["signal_key"]]
        if rate_records:
            assert rate_records[0]["value"] == 4.25


# ── 4. SDMX observation parsing ─────────────────────────────────────────

class TestSDMXParsing:
    def test_parse_sdmx_observations_extracts_values(self):
        obs = _parse_sdmx_observations(SAMPLE_FX_RESPONSE)
        assert len(obs) > 0

    def test_parse_sdmx_empty_response(self):
        obs = _parse_sdmx_observations(EMPTY_RESPONSE)
        assert obs == []

    def test_parse_sdmx_malformed_response(self):
        obs = _parse_sdmx_observations({"unexpected": "data"})
        assert obs == []


# ── 5. Country mapping ──────────────────────────────────────────────────

class TestCountryMapping:
    def test_eurozone_countries_get_eur_rate(self):
        def route_fetch(url):
            if "EXR" in url:
                return SAMPLE_FX_RESPONSE
            return SAMPLE_RATE_RESPONSE
        adapter = _make_adapter(
            fetch_fn=route_fetch,
            country_ids=("DEU", "FRA"),
        )
        result = adapter.fetch()
        country_ids = {r["country_id"] for r in result.records}
        # Eurozone countries should get key_rate records
        assert "DEU" in country_ids or "FRA" in country_ids

    def test_empty_country_ids_returns_empty(self):
        adapter = _make_adapter(country_ids=())
        result = adapter.fetch()
        assert result.is_success is True
        assert result.records == []


# ── 6. Period handling ───────────────────────────────────────────────────

class TestPeriodHandling:
    def test_period_is_iso_date(self):
        def route_fetch(url):
            if "EXR" in url:
                return SAMPLE_FX_RESPONSE
            return SAMPLE_RATE_RESPONSE
        adapter = _make_adapter(fetch_fn=route_fetch)
        result = adapter.fetch()
        for rec in result.records:
            datetime.strptime(rec["period"], "%Y-%m-%d")


# ── 7. Error handling ────────────────────────────────────────────────────

class TestErrorHandling:
    def test_api_error_returns_unsuccessful(self):
        def fail_fetch(url):
            raise ConnectionError("timeout")
        adapter = _make_adapter(fetch_fn=fail_fetch, max_retries=0)
        result = adapter.fetch()
        assert result.is_success is False
        assert result.records == []

    def test_malformed_sdmx_handled_gracefully(self):
        adapter = _make_adapter(
            fetch_fn=lambda url: {"broken": True},
        )
        result = adapter.fetch()
        assert isinstance(result, FetchResult)


# ── 8. Retry logic ──────────────────────────────────────────────────────

class TestRetryLogic:
    def test_retries_on_transient_failure(self):
        call_count = 0
        def flaky_fetch(url):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return SAMPLE_FX_RESPONSE
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


# ── 9. Source metadata ───────────────────────────────────────────────────

class TestSourceMetadata:
    def test_source_id(self):
        adapter = _make_adapter()
        assert adapter.source_id == "SRC-ECB-DATA"

    def test_domain_is_D(self):
        adapter = _make_adapter()
        assert adapter.domain == "D"

    def test_quality_flag(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["quality_flag"] == "ecb_sdw_api"


# ── 10. Diagnostics ────────────────────────────────────────────────────

class TestDiagnostics:
    def test_success_diagnostics(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        assert "ecb" in result.diagnostics.lower() or "ok" in result.diagnostics.lower()

    def test_empty_diagnostics(self):
        adapter = _make_adapter(country_ids=())
        result = adapter.fetch()
        assert "no" in result.diagnostics.lower() or "empty" in result.diagnostics.lower()
