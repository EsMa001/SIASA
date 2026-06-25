"""Tests for OONI Censorship adapter (SwR-080, AP-15.5).

TC-SwR-080-001: Verify OONICensorshipAdapter fetches blocked sites and censorship
incidents from the OONI API, normalizes to NormalizedRecord-compatible dicts.
"""
from __future__ import annotations
from datetime import datetime, timezone
import pytest
from siasa.adapters.ooni_censorship import OONICensorshipAdapter
from siasa.adapters.base import FetchResult

SAMPLE_RESPONSE = {
    "result": [
        {"probe_cc": "IR", "anomaly_count": 1234, "confirmed_count": 56},
        {"probe_cc": "IR", "anomaly_count": 100, "confirmed_count": 10},
        {"probe_cc": "CN", "anomaly_count": 5000, "confirmed_count": 200},
    ]
}
EMPTY_RESPONSE = {"result": []}
FIXED_NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)

def _make_adapter(fetch_fn=None, country_ids=None, now_fn=None, max_retries=3):
    if country_ids is None:
        country_ids = ("IR", "CN")
    if now_fn is None:
        now_fn = lambda: FIXED_NOW
    return OONICensorshipAdapter(
        country_ids=country_ids,
        fetch_json=fetch_fn or (lambda url: SAMPLE_RESPONSE),
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

    def test_signal_keys_contain_ooni_prefix(self):
        for rec in _make_adapter().fetch().records:
            assert rec["signal_key"].startswith("ooni_")

    def test_values_are_numeric(self):
        for rec in _make_adapter().fetch().records:
            assert isinstance(rec["value"], (int, float))

class TestCensorshipParsing:
    def test_blocked_site_count_extracted(self):
        result = _make_adapter(country_ids=("IR",)).fetch()
        blocked = [r for r in result.records if r["signal_key"] == "ooni_blocked_site_count"]
        assert len(blocked) == 1
        assert blocked[0]["value"] == 66.0  # 56 + 10

    def test_censorship_incident_count_extracted(self):
        result = _make_adapter(country_ids=("IR",)).fetch()
        incidents = [r for r in result.records if r["signal_key"] == "ooni_censorship_incident_count"]
        assert len(incidents) == 1
        assert incidents[0]["value"] == 1334.0  # 1234 + 100

    def test_aggregates_across_entries(self):
        result = _make_adapter(country_ids=("CN",)).fetch()
        blocked = [r for r in result.records if r["signal_key"] == "ooni_blocked_site_count"]
        assert blocked[0]["value"] == 200.0

class TestCountryMapping:
    def test_only_configured_countries_returned(self):
        result = _make_adapter(country_ids=("IR",)).fetch()
        assert all(r["country_id"] == "IR" for r in result.records)

    def test_empty_country_ids_returns_empty(self):
        result = _make_adapter(country_ids=()).fetch()
        assert result.is_success is True
        assert result.records == []

    def test_unknown_country_returns_empty_records(self):
        result = _make_adapter(country_ids=("XYZ",)).fetch()
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
            return SAMPLE_RESPONSE
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
        assert _make_adapter().source_id == "SRC-OONI"
    def test_domain_is_E(self):
        assert _make_adapter().domain == "E"
    def test_quality_flag(self):
        for rec in _make_adapter().fetch().records:
            assert rec["quality_flag"] == "ooni_api"

class TestDiagnostics:
    def test_success_diagnostics(self):
        assert "ooni" in _make_adapter().fetch().diagnostics.lower()
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
        def track(url): calls.append(url); return SAMPLE_RESPONSE
        _make_adapter(fetch_fn=track).fetch()
        assert len(calls) >= 1
