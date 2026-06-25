"""Tests for HDX HAPI adapter (SwR-083, AP-15.8).

TC-SwR-083-001: Verify HDXHAPIAdapter fetches conflict events, humanitarian needs,
and funding coverage from the HDX HAPI API, normalizes to NormalizedRecord dicts.
"""
from __future__ import annotations
from datetime import datetime, timezone
import pytest
from siasa.adapters.hdx_hapi import HDXHAPIAdapter
from siasa.adapters.base import FetchResult

SAMPLE_CONFLICT_RESPONSE = {
    "data": [
        {"event_type": "battles", "location_name": "Khartoum"},
        {"event_type": "violence", "location_name": "Darfur"},
        {"event_type": "protests", "location_name": "Port Sudan"},
    ]
}
SAMPLE_NEEDS_RESPONSE = {
    "data": [
        {"population_in_need": 5000000, "sector": "food"},
        {"population_in_need": 3000000, "sector": "health"},
    ]
}
SAMPLE_FUNDING_RESPONSE = {
    "data": [
        {"requirements_usd": 1000000000, "funding_usd": 400000000, "year": 2024},
    ]
}
EMPTY_RESPONSE = {"data": []}
FIXED_NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)

def _route_fetch(url):
    if "conflict-event" in url:
        return SAMPLE_CONFLICT_RESPONSE
    elif "humanitarian-needs" in url:
        return SAMPLE_NEEDS_RESPONSE
    elif "funding" in url:
        return SAMPLE_FUNDING_RESPONSE
    return EMPTY_RESPONSE

def _make_adapter(fetch_fn=None, country_ids=None, now_fn=None, max_retries=3):
    if country_ids is None:
        country_ids = ("SDN", "UKR")
    if now_fn is None:
        now_fn = lambda: FIXED_NOW
    return HDXHAPIAdapter(
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

    def test_signal_keys_contain_hdx_prefix(self):
        for rec in _make_adapter().fetch().records:
            assert rec["signal_key"].startswith("hdx_hapi_")

    def test_values_are_numeric(self):
        for rec in _make_adapter().fetch().records:
            assert isinstance(rec["value"], (int, float))

class TestConflictEventParsing:
    def test_conflict_events_extracted(self):
        result = _make_adapter(country_ids=("SDN",)).fetch()
        events = [r for r in result.records if r["signal_key"] == "hdx_hapi_conflict_events"]
        assert len(events) == 1
        assert events[0]["value"] == 3.0  # 3 entries

class TestHumanitarianNeedsParsing:
    def test_needs_extracted(self):
        result = _make_adapter(country_ids=("SDN",)).fetch()
        needs = [r for r in result.records if r["signal_key"] == "hdx_hapi_humanitarian_needs"]
        assert len(needs) == 1
        assert needs[0]["value"] == 8000000.0  # 5M + 3M

class TestFundingCoverageParsing:
    def test_funding_coverage_extracted(self):
        result = _make_adapter(country_ids=("SDN",)).fetch()
        funding = [r for r in result.records if r["signal_key"] == "hdx_hapi_funding_coverage"]
        assert len(funding) == 1
        assert abs(funding[0]["value"] - 40.0) < 0.1  # 400M/1000M * 100

    def test_funding_zero_requirements(self):
        def zero_funding(url):
            if "funding" in url:
                return {"data": [{"requirements_usd": 0, "funding_usd": 0}]}
            return _route_fetch(url)
        result = _make_adapter(fetch_fn=zero_funding, country_ids=("SDN",)).fetch()
        funding = [r for r in result.records if r["signal_key"] == "hdx_hapi_funding_coverage"]
        assert funding[0]["value"] == 0.0

class TestMultipleIndicators:
    def test_three_signals_per_country(self):
        result = _make_adapter(country_ids=("SDN",)).fetch()
        signals = {r["signal_key"] for r in result.records}
        assert "hdx_hapi_conflict_events" in signals
        assert "hdx_hapi_humanitarian_needs" in signals
        assert "hdx_hapi_funding_coverage" in signals

    def test_record_count_two_countries(self):
        result = _make_adapter(country_ids=("SDN", "UKR")).fetch()
        assert len(result.records) == 6  # 3 signals x 2 countries

class TestCountryMapping:
    def test_only_configured_countries_returned(self):
        result = _make_adapter(country_ids=("SDN",)).fetch()
        assert all(r["country_id"] == "SDN" for r in result.records)

    def test_empty_country_ids_returns_empty(self):
        result = _make_adapter(country_ids=()).fetch()
        assert result.is_success is True
        assert result.records == []

class TestPeriodHandling:
    def test_period_is_iso_date(self):
        for rec in _make_adapter().fetch().records:
            datetime.strptime(rec["period"], "%Y-%m-%d")

class TestErrorHandling:
    def test_api_error_returns_unsuccessful(self):
        def fail(url): raise ConnectionError("timeout")
        result = _make_adapter(fetch_fn=fail, max_retries=0).fetch()
        assert result.is_success is False

    def test_partial_failure_returns_partial_records(self):
        def partial(url):
            if "conflict-event" in url: raise ConnectionError("down")
            return _route_fetch(url)
        result = _make_adapter(fetch_fn=partial, max_retries=0).fetch()
        assert result.is_success is True
        signals = {r["signal_key"] for r in result.records}
        assert "hdx_hapi_humanitarian_needs" in signals
        assert "hdx_hapi_conflict_events" not in signals

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
        assert _make_adapter().source_id == "SRC-HDX-HAPI"
    def test_domain_is_B(self):
        assert _make_adapter().domain == "B"
    def test_quality_flag(self):
        for rec in _make_adapter().fetch().records:
            assert rec["quality_flag"] == "hdx_hapi_api"

class TestDiagnostics:
    def test_success_diagnostics(self):
        assert "hdx" in _make_adapter().fetch().diagnostics.lower()
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
        assert len(calls) >= 3  # 3 endpoints x countries

    def test_url_contains_app_identifier(self):
        calls = []
        def track(url): calls.append(url); return _route_fetch(url)
        _make_adapter(fetch_fn=track, country_ids=("SDN",)).fetch()
        assert any("app_identifier" in url for url in calls)
