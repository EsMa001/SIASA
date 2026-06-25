"""Tests for IODA Outages adapter (SwR-079).

TC-SwR-079-001: Verify IODAOutageAdapter fetches internet outage alerts
from IODA API, normalizes to NormalizedRecord-compatible dicts,
handles parsing, errors, and retries.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from siasa.adapters.ioda_outages import IODAOutageAdapter
from siasa.adapters.base import FetchResult


# ── Fixtures ──────────────────────────────────────────────────────────────

SAMPLE_RESPONSE = {
    "data": [
        {
            "entityType": "country",
            "entityCode": "IR",
            "level": "critical",
            "datasource": "bgp",
            "condition": "drop",
        },
        {
            "entityType": "country",
            "entityCode": "IR",
            "level": "warning",
            "datasource": "active-probing",
            "condition": "drop",
        },
        {
            "entityType": "country",
            "entityCode": "RU",
            "level": "warning",
            "datasource": "bgp",
            "condition": "drop",
        },
        {
            "entityType": "region",
            "entityCode": "US-CA",
            "level": "normal",
            "datasource": "bgp",
        },
    ],
}

EMPTY_RESPONSE = {"data": []}

FIXED_NOW = datetime(2026, 6, 5, 12, 0, 0, tzinfo=timezone.utc)


def _make_adapter(
    fetch_fn=None,
    country_ids=None,
    now_fn=None,
    max_retries=3,
):
    if country_ids is None:
        country_ids = ("IR", "RU")
    if now_fn is None:
        now_fn = lambda: FIXED_NOW  # noqa: E731
    return IODAOutageAdapter(
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

    def test_signal_keys_contain_ioda_prefix(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["signal_key"].startswith("ioda_")

    def test_values_are_numeric(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert isinstance(rec["value"], (int, float))


# ── 2. Alert parsing ────────────────────────────────────────────────────

class TestAlertParsing:
    def test_alert_count_extracted(self):
        adapter = _make_adapter(country_ids=("IR",))
        result = adapter.fetch()
        alert_records = [
            r for r in result.records
            if r["signal_key"] == "ioda_outage_alert_count"
        ]
        assert len(alert_records) == 1
        assert alert_records[0]["value"] == 2.0  # Two IR alerts

    def test_bgp_visibility_drop_extracted(self):
        adapter = _make_adapter(country_ids=("IR",))
        result = adapter.fetch()
        bgp_records = [
            r for r in result.records
            if r["signal_key"] == "ioda_bgp_visibility_drop"
        ]
        assert len(bgp_records) == 1
        assert bgp_records[0]["value"] == 3.0  # critical = 3.0

    def test_only_country_entities_used(self):
        """Region entities should be filtered out."""
        adapter = _make_adapter(country_ids=("US-CA",))
        result = adapter.fetch()
        alert_records = [
            r for r in result.records
            if r["signal_key"] == "ioda_outage_alert_count"
        ]
        # US-CA is a region, not a country entity type
        assert len(alert_records) == 1
        assert alert_records[0]["value"] == 0.0


# ── 3. Country mapping ──────────────────────────────────────────────────

class TestCountryMapping:
    def test_only_configured_countries_returned(self):
        adapter = _make_adapter(country_ids=("IR",))
        result = adapter.fetch()
        country_ids = {r["country_id"] for r in result.records}
        assert country_ids == {"IR"}

    def test_empty_country_ids_returns_empty(self):
        adapter = _make_adapter(country_ids=())
        result = adapter.fetch()
        assert result.is_success is True
        assert result.records == []

    def test_multiple_countries(self):
        adapter = _make_adapter(country_ids=("IR", "RU"))
        result = adapter.fetch()
        country_ids = {r["country_id"] for r in result.records}
        assert "IR" in country_ids
        assert "RU" in country_ids


# ── 4. Period handling ───────────────────────────────────────────────────

class TestPeriodHandling:
    def test_period_is_iso_date(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            datetime.strptime(rec["period"], "%Y-%m-%d")

    def test_period_uses_now_provider(self):
        custom_now = datetime(2025, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
        adapter = _make_adapter(now_fn=lambda: custom_now)
        result = adapter.fetch()
        for rec in result.records:
            assert rec["period"] == "2025-03-15"


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
        # No data entries → records for each country with 0 values
        assert result.is_success is True


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
        assert adapter.source_id == "SRC-IODA"

    def test_domain_is_E(self):
        adapter = _make_adapter()
        assert adapter.domain == "E"

    def test_quality_flag(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["quality_flag"] == "ioda_api"


# ── 8. Diagnostics ────────────────────────────────────────────────────

class TestDiagnostics:
    def test_success_diagnostics(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        assert "ioda" in result.diagnostics.lower() or "ok" in result.diagnostics.lower()

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
            assert rec["freshness_hours"] == 24

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
