"""Tests for Eurostat adapter (SwR-074, AP-14.3).

TC-SwR-074-001: Verify EurostatAdapter fetches monthly HICP inflation and
unemployment rates per EU country, normalizes to NormalizedRecord-compatible dicts.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from siasa.adapters.eurostat import (
    EurostatAdapter,
    _parse_eurostat_json,
)
from siasa.adapters.base import FetchResult


# ── Fixtures ──────────────────────────────────────────────────────────────

# Eurostat JSON-stat style response for HICP inflation (prc_hicp_manr)
SAMPLE_HICP_RESPONSE = {
    "version": "2.0",
    "label": "HICP - annual rate of change",
    "id": ["freq", "unit", "coicop", "geo", "time"],
    "size": [1, 1, 1, 2, 2],
    "dimension": {
        "geo": {
            "label": "geo",
            "category": {
                "index": {"DE": 0, "FR": 1},
                "label": {"DE": "Germany", "FR": "France"},
            },
        },
        "time": {
            "label": "time",
            "category": {
                "index": {"2026M04": 0, "2026M05": 1},
                "label": {"2026M04": "2026M04", "2026M05": "2026M05"},
            },
        },
    },
    "value": {
        "0": 2.1,   # DE, 2026M04
        "1": 2.3,   # DE, 2026M05
        "2": 1.8,   # FR, 2026M04
        "3": 1.9,   # FR, 2026M05
    },
}

# Eurostat JSON-stat response for unemployment (une_rt_m)
SAMPLE_UNEMP_RESPONSE = {
    "version": "2.0",
    "label": "Unemployment rate",
    "id": ["freq", "s_adj", "age", "unit", "sex", "geo", "time"],
    "size": [1, 1, 1, 1, 1, 2, 1],
    "dimension": {
        "geo": {
            "label": "geo",
            "category": {
                "index": {"DE": 0, "FR": 1},
                "label": {"DE": "Germany", "FR": "France"},
            },
        },
        "time": {
            "label": "time",
            "category": {
                "index": {"2026M04": 0},
                "label": {"2026M04": "2026M04"},
            },
        },
    },
    "value": {
        "0": 3.2,   # DE
        "1": 7.1,   # FR
    },
}

EMPTY_RESPONSE: dict = {
    "version": "2.0",
    "id": ["geo", "time"],
    "size": [0, 0],
    "dimension": {
        "geo": {"category": {"index": {}, "label": {}}},
        "time": {"category": {"index": {}, "label": {}}},
    },
    "value": {},
}

FIXED_NOW = datetime(2026, 6, 5, 12, 0, 0, tzinfo=timezone.utc)


def _make_adapter(
    fetch_fn=None,
    country_ids=None,
    now_fn=None,
    max_retries=3,
):
    if country_ids is None:
        country_ids = ("DEU", "FRA")
    if now_fn is None:
        now_fn = lambda: FIXED_NOW  # noqa: E731
    return EurostatAdapter(
        country_ids=country_ids,
        fetch_json=fetch_fn or (lambda url: SAMPLE_HICP_RESPONSE),
        now_provider=now_fn,
        retry_sleep=lambda _: None,
        max_retries=max_retries,
    )


# ── 1. Basic fetch ──────────────────────────────────────────────────────

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

    def test_signal_keys_contain_eurostat_prefix(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["signal_key"].startswith("eurostat_")

    def test_values_are_numeric(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert isinstance(rec["value"], (int, float))


# ── 2. HICP inflation parsing ───────────────────────────────────────────

class TestHICPParsing:
    def test_hicp_records_extracted(self):
        def route_fetch(url):
            if "prc_hicp" in url:
                return SAMPLE_HICP_RESPONSE
            return SAMPLE_UNEMP_RESPONSE
        adapter = _make_adapter(fetch_fn=route_fetch)
        result = adapter.fetch()
        hicp = [r for r in result.records if "hicp" in r["signal_key"]]
        assert len(hicp) > 0

    def test_hicp_values_match(self):
        def route_fetch(url):
            if "prc_hicp" in url:
                return SAMPLE_HICP_RESPONSE
            return SAMPLE_UNEMP_RESPONSE
        adapter = _make_adapter(fetch_fn=route_fetch)
        result = adapter.fetch()
        hicp = [r for r in result.records if "hicp" in r["signal_key"]]
        values = {r["value"] for r in hicp}
        # Should contain values from fixture
        assert values & {2.1, 2.3, 1.8, 1.9}


# ── 3. Unemployment parsing ─────────────────────────────────────────────

class TestUnemploymentParsing:
    def test_unemployment_records_extracted(self):
        def route_fetch(url):
            if "prc_hicp" in url:
                return SAMPLE_HICP_RESPONSE
            return SAMPLE_UNEMP_RESPONSE
        adapter = _make_adapter(fetch_fn=route_fetch)
        result = adapter.fetch()
        unemp = [r for r in result.records if "unemployment" in r["signal_key"]]
        assert len(unemp) > 0


# ── 4. JSON-stat parsing ────────────────────────────────────────────────

class TestJSONStatParsing:
    def test_parse_eurostat_json_extracts_values(self):
        records = _parse_eurostat_json(SAMPLE_HICP_RESPONSE, "eurostat_hicp_inflation")
        assert len(records) > 0

    def test_parse_eurostat_json_empty(self):
        records = _parse_eurostat_json(EMPTY_RESPONSE, "test_signal")
        assert records == []

    def test_parse_eurostat_json_malformed(self):
        records = _parse_eurostat_json({"broken": True}, "test_signal")
        assert records == []


# ── 5. Country mapping ──────────────────────────────────────────────────

class TestCountryMapping:
    def test_iso2_to_iso3_mapping(self):
        def route_fetch(url):
            if "prc_hicp" in url:
                return SAMPLE_HICP_RESPONSE
            return SAMPLE_UNEMP_RESPONSE
        adapter = _make_adapter(fetch_fn=route_fetch, country_ids=("DEU",))
        result = adapter.fetch()
        for rec in result.records:
            assert rec["country_id"] == "DEU"

    def test_empty_country_ids(self):
        adapter = _make_adapter(country_ids=())
        result = adapter.fetch()
        assert result.is_success is True
        assert result.records == []


# ── 6. Period handling ───────────────────────────────────────────────────

class TestPeriodHandling:
    def test_period_from_eurostat_monthly(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            # Should be YYYY-MM or YYYY-MM-DD
            assert len(rec["period"]) >= 7


# ── 7. Error handling ────────────────────────────────────────────────────

class TestErrorHandling:
    def test_api_error_returns_unsuccessful(self):
        def fail_fetch(url):
            raise ConnectionError("timeout")
        adapter = _make_adapter(fetch_fn=fail_fetch, max_retries=0)
        result = adapter.fetch()
        assert result.is_success is False

    def test_malformed_response_handled(self):
        adapter = _make_adapter(fetch_fn=lambda url: {"broken": True})
        result = adapter.fetch()
        assert isinstance(result, FetchResult)


# ── 8. Retry logic ──────────────────────────────────────────────────────

class TestRetryLogic:
    def test_retries_on_failure(self):
        call_count = 0
        def flaky(url):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return SAMPLE_HICP_RESPONSE
        adapter = _make_adapter(fetch_fn=flaky, max_retries=3)
        result = adapter.fetch()
        assert result.is_success is True
        assert call_count >= 3


# ── 9. Source metadata ───────────────────────────────────────────────────

class TestSourceMetadata:
    def test_source_id(self):
        adapter = _make_adapter()
        assert adapter.source_id == "SRC-EUROSTAT"

    def test_domain_is_D(self):
        adapter = _make_adapter()
        assert adapter.domain == "D"

    def test_quality_flag(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["quality_flag"] == "eurostat_api"


# ── 10. Diagnostics ────────────────────────────────────────────────────

class TestDiagnostics:
    def test_success_diagnostics(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        assert "eurostat" in result.diagnostics.lower()

    def test_empty_diagnostics(self):
        adapter = _make_adapter(country_ids=())
        result = adapter.fetch()
        assert "no" in result.diagnostics.lower() or "empty" in result.diagnostics.lower()
