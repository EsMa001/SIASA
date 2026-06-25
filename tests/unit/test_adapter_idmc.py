"""Tests for IDMC Displacement adapter (SwR-078).

TC-SwR-078-001: Verify IDMCDisplacementAdapter fetches displacement data
from IDMC API, normalizes to NormalizedRecord-compatible dicts,
handles parsing, errors, and retries.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from siasa.adapters.idmc_displacement import IDMCDisplacementAdapter
from siasa.adapters.base import FetchResult


# ── Fixtures ──────────────────────────────────────────────────────────────

SAMPLE_RESPONSE = [
    {
        "iso3": "UKR",
        "year": 2023,
        "conflict_new_displacements": 123456,
        "disaster_new_displacements": 78900,
    },
    {
        "iso3": "SYR",
        "year": 2023,
        "conflict_new_displacements": 200000,
        "disaster_new_displacements": 15000,
    },
    {
        "iso3": "ETH",
        "year": 2023,
        "conflict_new_displacements": 350000,
        "disaster_new_displacements": 120000,
    },
    {
        "iso3": "UKR",
        "year": 2022,
        "conflict_new_displacements": 500000,
        "disaster_new_displacements": 45000,
    },
]

EMPTY_RESPONSE: list = []

FIXED_NOW = datetime(2026, 6, 5, 12, 0, 0, tzinfo=timezone.utc)


def _make_adapter(
    fetch_fn=None,
    country_ids=None,
    now_fn=None,
    max_retries=3,
):
    if country_ids is None:
        country_ids = ("UKR", "SYR")
    if now_fn is None:
        now_fn = lambda: FIXED_NOW  # noqa: E731
    return IDMCDisplacementAdapter(
        country_ids=country_ids,
        fetch_json=fetch_fn or (lambda url: SAMPLE_RESPONSE),
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

    def test_signal_keys_contain_idmc_prefix(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["signal_key"].startswith("idmc_")

    def test_values_are_numeric(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert isinstance(rec["value"], (int, float))


# ── 2. Displacement data parsing ─────────────────────────────────────────

class TestDisplacementParsing:
    def test_conflict_displacements_extracted(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        conflict_records = [
            r for r in result.records
            if r["signal_key"] == "idmc_new_displacements_conflict"
        ]
        assert len(conflict_records) > 0

    def test_disaster_displacements_extracted(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        disaster_records = [
            r for r in result.records
            if r["signal_key"] == "idmc_new_displacements_disaster"
        ]
        assert len(disaster_records) > 0

    def test_conflict_value_matches(self):
        adapter = _make_adapter(country_ids=("UKR",))
        result = adapter.fetch()
        conflict_records = [
            r for r in result.records
            if r["signal_key"] == "idmc_new_displacements_conflict"
            and r["country_id"] == "UKR"
        ]
        assert len(conflict_records) > 0
        values = {r["value"] for r in conflict_records}
        assert 123456.0 in values

    def test_disaster_value_matches(self):
        adapter = _make_adapter(country_ids=("UKR",))
        result = adapter.fetch()
        disaster_records = [
            r for r in result.records
            if r["signal_key"] == "idmc_new_displacements_disaster"
            and r["country_id"] == "UKR"
        ]
        assert len(disaster_records) > 0
        values = {r["value"] for r in disaster_records}
        assert 78900.0 in values


# ── 3. Country mapping ──────────────────────────────────────────────────

class TestCountryMapping:
    def test_only_configured_countries_returned(self):
        adapter = _make_adapter(country_ids=("UKR",))
        result = adapter.fetch()
        country_ids = {r["country_id"] for r in result.records}
        assert country_ids == {"UKR"}

    def test_empty_country_ids_returns_empty(self):
        adapter = _make_adapter(country_ids=())
        result = adapter.fetch()
        assert result.is_success is True
        assert result.records == []

    def test_unmatched_country_returns_no_records(self):
        adapter = _make_adapter(country_ids=("ZZZ",))
        result = adapter.fetch()
        assert result.is_success is True
        assert result.records == []


# ── 4. Period handling ───────────────────────────────────────────────────

class TestPeriodHandling:
    def test_period_is_year_string(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["period"] in ("2023", "2022")

    def test_period_defaults_to_empty_string_when_no_year(self):
        response = [{"iso3": "UKR", "conflict_new_displacements": 100}]
        adapter = _make_adapter(fetch_fn=lambda url: response, country_ids=("UKR",))
        result = adapter.fetch()
        assert len(result.records) > 0
        assert result.records[0]["period"] == ""


# ── 5. Error handling ────────────────────────────────────────────────────

class TestErrorHandling:
    def test_api_error_returns_unsuccessful(self):
        def fail_fetch(url):
            raise ConnectionError("timeout")
        adapter = _make_adapter(fetch_fn=fail_fetch, max_retries=0)
        result = adapter.fetch()
        assert result.is_success is False
        assert result.records == []

    def test_malformed_response_handled_gracefully(self):
        adapter = _make_adapter(fetch_fn=lambda url: {"broken": True})
        result = adapter.fetch()
        assert isinstance(result, FetchResult)
        assert result.is_success is True
        assert result.records == []


# ── 6. Retry logic ──────────────────────────────────────────────────────

class TestRetryLogic:
    def test_retries_on_transient_failure(self):
        call_count = 0
        def flaky_fetch(url):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return SAMPLE_RESPONSE
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


# ── 7. Source metadata ───────────────────────────────────────────────────

class TestSourceMetadata:
    def test_source_id(self):
        adapter = _make_adapter()
        assert adapter.source_id == "SRC-IDMC"

    def test_domain_is_C(self):
        adapter = _make_adapter()
        assert adapter.domain == "C"

    def test_quality_flag(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["quality_flag"] == "idmc_api"


# ── 8. Diagnostics ────────────────────────────────────────────────────

class TestDiagnostics:
    def test_success_diagnostics(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        assert "idmc" in result.diagnostics.lower() or "ok" in result.diagnostics.lower()

    def test_empty_diagnostics(self):
        adapter = _make_adapter(country_ids=())
        result = adapter.fetch()
        assert "no" in result.diagnostics.lower() or "empty" in result.diagnostics.lower()


# ── 9. Freshness metadata ───────────────────────────────────────────────

class TestFreshnessMetadata:
    def test_freshness_hours_in_records(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert "freshness_hours" in rec
            assert rec["freshness_hours"] == 720

    def test_freshness_horizon_hours_in_records(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert "freshness_horizon_hours" in rec

    def test_expected_source_count(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["expected_source_count"] == 1


# ── 10. Injectable fetch ─────────────────────────────────────────────────

class TestInjectableFetch:
    def test_custom_fetch_function_used(self):
        urls_called = []
        def tracking_fetch(url):
            urls_called.append(url)
            return SAMPLE_RESPONSE
        adapter = _make_adapter(fetch_fn=tracking_fetch)
        adapter.fetch()
        assert len(urls_called) > 0

    def test_custom_now_provider_used(self):
        custom_now = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        adapter = _make_adapter(now_fn=lambda: custom_now)
        result = adapter.fetch()
        assert result.is_success is True
