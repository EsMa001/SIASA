"""Tests for FEWS NET adapter (SwR-081, AP-15.6).

TC-SwR-081-001: Verify FEWSNETAdapter fetches food prices and IPC phases
from the FEWS NET API, normalizes to NormalizedRecord-compatible dicts.
"""
from __future__ import annotations
from datetime import datetime, timezone
import pytest
from siasa.adapters.fewsnet import FEWSNETAdapter
from siasa.adapters.base import FetchResult

SAMPLE_MARKET_RESPONSE = [
    {"country": "ETH", "price": 45.5, "date": "2024-03", "commodity": "maize"},
    {"country": "ETH", "price": 52.3, "date": "2024-03", "commodity": "wheat"},
    {"country": "SDN", "price": 120.0, "date": "2024-03", "commodity": "sorghum"},
]
SAMPLE_IPC_RESPONSE = [
    {"country": "ETH", "phase": 3, "date": "2024-03"},
    {"country": "SDN", "phase": 4, "date": "2024-03"},
]
EMPTY_LIST = []
FIXED_NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)

def _route_fetch(url):
    if "ipcphase" in url:
        return SAMPLE_IPC_RESPONSE
    return SAMPLE_MARKET_RESPONSE

def _make_adapter(fetch_fn=None, country_ids=None, now_fn=None, max_retries=3):
    if country_ids is None:
        country_ids = ("ETH", "SDN")
    if now_fn is None:
        now_fn = lambda: FIXED_NOW
    return FEWSNETAdapter(
        country_ids=country_ids,
        fetch_json=fetch_fn or _route_fetch,
        now_provider=now_fn,
        retry_sleep=lambda _: None,
        max_retries=max_retries,
    )

class TestBasicFetch:
    def test_returns_fetch_result(self):
        result = _make_adapter().fetch()
        assert isinstance(result, FetchResult)
        assert result.is_success is True

    def test_records_have_required_fields(self):
        result = _make_adapter().fetch()
        assert len(result.records) > 0
        for rec in result.records:
            assert {"country_id", "period", "signal_key", "value", "quality_flag"}.issubset(rec.keys())

    def test_signal_keys_contain_fewsnet_prefix(self):
        for rec in _make_adapter().fetch().records:
            assert rec["signal_key"].startswith("fewsnet_")

    def test_values_are_numeric(self):
        for rec in _make_adapter().fetch().records:
            assert isinstance(rec["value"], (int, float))

class TestMarketPriceParsing:
    def test_price_records_extracted(self):
        result = _make_adapter().fetch()
        prices = [r for r in result.records if r["signal_key"] == "fewsnet_food_price_index"]
        assert len(prices) > 0

    def test_price_value(self):
        result = _make_adapter(country_ids=("SDN",)).fetch()
        prices = [r for r in result.records if r["signal_key"] == "fewsnet_food_price_index"]
        assert any(p["value"] == 120.0 for p in prices)

    def test_price_period(self):
        result = _make_adapter().fetch()
        prices = [r for r in result.records if r["signal_key"] == "fewsnet_food_price_index"]
        assert prices[0]["period"] == "2024-03"

class TestIPCParsing:
    def test_ipc_records_extracted(self):
        result = _make_adapter().fetch()
        ipc = [r for r in result.records if r["signal_key"] == "fewsnet_ipc_phase"]
        assert len(ipc) > 0

    def test_ipc_phase_value(self):
        result = _make_adapter(country_ids=("SDN",)).fetch()
        ipc = [r for r in result.records if r["signal_key"] == "fewsnet_ipc_phase"]
        assert ipc[0]["value"] == 4.0

    def test_partial_failure_still_returns_other(self):
        def partial_fail(url):
            if "ipcphase" in url: raise ConnectionError("IPC down")
            return SAMPLE_MARKET_RESPONSE
        result = _make_adapter(fetch_fn=partial_fail, max_retries=0).fetch()
        assert result.is_success is True
        signals = {r["signal_key"] for r in result.records}
        assert "fewsnet_food_price_index" in signals
        assert "fewsnet_ipc_phase" not in signals

class TestCountryMapping:
    def test_only_configured_countries_returned(self):
        result = _make_adapter(country_ids=("ETH",)).fetch()
        assert all(r["country_id"] == "ETH" for r in result.records)

    def test_empty_country_ids_returns_empty(self):
        result = _make_adapter(country_ids=()).fetch()
        assert result.is_success is True
        assert result.records == []

class TestErrorHandling:
    def test_api_error_returns_unsuccessful(self):
        def fail(url): raise ConnectionError("timeout")
        result = _make_adapter(fetch_fn=fail, max_retries=0).fetch()
        assert result.is_success is False

    def test_malformed_response_handled(self):
        result = _make_adapter(fetch_fn=lambda url: {"broken": True}).fetch()
        assert isinstance(result, FetchResult)
        assert result.is_success is True

class TestRetryLogic:
    def test_retries_on_failure(self):
        calls = [0]
        def flaky(url):
            calls[0] += 1
            if calls[0] < 3: raise ConnectionError("transient")
            return _route_fetch(url)
        result = _make_adapter(fetch_fn=flaky, max_retries=3).fetch()
        assert result.is_success is True

    def test_retry_sleep_called(self):
        sleeps = []
        def fail(url): raise ConnectionError("fail")
        a = _make_adapter(fetch_fn=fail, max_retries=1)
        a.retry_sleep = lambda d: sleeps.append(d)
        a.fetch()
        assert len(sleeps) >= 1

class TestSourceMetadata:
    def test_source_id(self):
        assert _make_adapter().source_id == "SRC-FEWSNET"
    def test_domain_is_C(self):
        assert _make_adapter().domain == "C"
    def test_quality_flag(self):
        for rec in _make_adapter().fetch().records:
            assert rec["quality_flag"] == "fewsnet_api"

class TestDiagnostics:
    def test_success_diagnostics(self):
        assert "fewsnet" in _make_adapter().fetch().diagnostics.lower()
    def test_empty_diagnostics(self):
        d = _make_adapter(country_ids=()).fetch().diagnostics
        assert "no" in d.lower() or "0" in d

class TestFreshnessMetadata:
    def test_freshness_hours(self):
        for rec in _make_adapter().fetch().records:
            assert isinstance(rec["freshness_hours"], (int, float))
    def test_expected_source_count(self):
        for rec in _make_adapter().fetch().records:
            assert rec["expected_source_count"] == 1

class TestInjectableFetch:
    def test_custom_fetch_used(self):
        calls = []
        def track(url): calls.append(url); return _route_fetch(url)
        _make_adapter(fetch_fn=track).fetch()
        assert len(calls) >= 2  # market + ipc
