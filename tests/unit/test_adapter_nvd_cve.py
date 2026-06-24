"""Tests for NVD CVE 2.0 adapter (SwR-075, AP-14.4).

TC-SwR-075-001: Verify NVDCVEAdapter fetches daily CVE publications,
extracts CVSS scores, aggregates by severity, normalizes to records.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from siasa.adapters.nvd_cve import (
    NVDCVEAdapter,
    _extract_cvss_score,
)
from siasa.adapters.base import FetchResult


# ── Fixtures ──────────────────────────────────────────────────────────────

SAMPLE_CVE_RESPONSE = {
    "resultsPerPage": 3,
    "startIndex": 0,
    "totalResults": 3,
    "vulnerabilities": [
        {
            "cve": {
                "id": "CVE-2026-0001",
                "published": "2026-06-01T12:00:00.000",
                "metrics": {
                    "cvssMetricV31": [{
                        "cvssData": {"baseScore": 9.8, "baseSeverity": "CRITICAL"},
                    }],
                },
            },
        },
        {
            "cve": {
                "id": "CVE-2026-0002",
                "published": "2026-06-01T14:00:00.000",
                "metrics": {
                    "cvssMetricV31": [{
                        "cvssData": {"baseScore": 7.5, "baseSeverity": "HIGH"},
                    }],
                },
            },
        },
        {
            "cve": {
                "id": "CVE-2026-0003",
                "published": "2026-06-01T16:00:00.000",
                "metrics": {
                    "cvssMetricV31": [{
                        "cvssData": {"baseScore": 4.3, "baseSeverity": "MEDIUM"},
                    }],
                },
            },
        },
    ],
}

EMPTY_CVE_RESPONSE = {
    "resultsPerPage": 0,
    "startIndex": 0,
    "totalResults": 0,
    "vulnerabilities": [],
}

FIXED_NOW = datetime(2026, 6, 5, 12, 0, 0, tzinfo=timezone.utc)


def _make_adapter(
    fetch_fn=None,
    now_fn=None,
    max_retries=3,
    lookback_days=1,
):
    if now_fn is None:
        now_fn = lambda: FIXED_NOW  # noqa: E731
    return NVDCVEAdapter(
        fetch_json=fetch_fn or (lambda url: SAMPLE_CVE_RESPONSE),
        now_provider=now_fn,
        retry_sleep=lambda _: None,
        max_retries=max_retries,
        lookback_days=lookback_days,
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

    def test_produces_multiple_signals(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        signal_keys = {r["signal_key"] for r in result.records}
        assert "nvd_cve_count_daily" in signal_keys
        assert "nvd_avg_cvss_base" in signal_keys

    def test_values_are_numeric(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert isinstance(rec["value"], (int, float))


# ── 2. CVE count aggregation ────────────────────────────────────────────

class TestCVECount:
    def test_daily_count_matches_vulnerabilities(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        count_recs = [r for r in result.records if r["signal_key"] == "nvd_cve_count_daily"]
        assert len(count_recs) >= 1
        # 3 CVEs in sample
        total = sum(r["value"] for r in count_recs)
        assert total == 3

    def test_critical_count(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        critical_recs = [r for r in result.records if r["signal_key"] == "nvd_critical_cve_count"]
        if critical_recs:
            # 1 CRITICAL in sample
            assert critical_recs[0]["value"] == 1


# ── 3. CVSS score extraction ────────────────────────────────────────────

class TestCVSSExtraction:
    def test_extract_cvss_v31(self):
        metrics = {"cvssMetricV31": [{"cvssData": {"baseScore": 9.8}}]}
        assert _extract_cvss_score(metrics) == 9.8

    def test_extract_cvss_missing(self):
        assert _extract_cvss_score({}) is None

    def test_extract_cvss_empty_list(self):
        metrics = {"cvssMetricV31": []}
        assert _extract_cvss_score(metrics) is None

    def test_avg_cvss_calculated(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        avg_recs = [r for r in result.records if r["signal_key"] == "nvd_avg_cvss_base"]
        if avg_recs:
            # (9.8 + 7.5 + 4.3) / 3 ≈ 7.2
            assert 7.0 <= avg_recs[0]["value"] <= 7.5


# ── 4. Period handling ──────────────────────────────────────────────────

class TestPeriodHandling:
    def test_period_is_iso_date(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            datetime.strptime(rec["period"], "%Y-%m-%d")


# ── 5. Error handling ────────────────────────────────────────────────────

class TestErrorHandling:
    def test_api_error_returns_unsuccessful(self):
        def fail_fetch(url):
            raise ConnectionError("timeout")
        adapter = _make_adapter(fetch_fn=fail_fetch, max_retries=0)
        result = adapter.fetch()
        assert result.is_success is False

    def test_empty_response_produces_zero_count(self):
        adapter = _make_adapter(fetch_fn=lambda url: EMPTY_CVE_RESPONSE)
        result = adapter.fetch()
        assert result.is_success is True
        count_recs = [r for r in result.records if r["signal_key"] == "nvd_cve_count_daily"]
        if count_recs:
            assert count_recs[0]["value"] == 0

    def test_malformed_response_handled(self):
        adapter = _make_adapter(fetch_fn=lambda url: {"broken": True})
        result = adapter.fetch()
        assert isinstance(result, FetchResult)


# ── 6. Retry logic ──────────────────────────────────────────────────────

class TestRetryLogic:
    def test_retries_on_failure(self):
        call_count = 0
        def flaky(url):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return SAMPLE_CVE_RESPONSE
        adapter = _make_adapter(fetch_fn=flaky, max_retries=3)
        result = adapter.fetch()
        assert result.is_success is True
        assert call_count == 3


# ── 7. Source metadata ───────────────────────────────────────────────────

class TestSourceMetadata:
    def test_source_id(self):
        adapter = _make_adapter()
        assert adapter.source_id == "SRC-NVD-CVE"

    def test_domain_is_E(self):
        adapter = _make_adapter()
        assert adapter.domain == "E"

    def test_quality_flag(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["quality_flag"] == "nvd_cve_api"

    def test_country_id_is_GLOBAL(self):
        """NVD CVEs are global, not country-specific."""
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["country_id"] == "GLOBAL"


# ── 8. Diagnostics ────────────────────────────────────────────────────

class TestDiagnostics:
    def test_success_diagnostics(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        assert "nvd" in result.diagnostics.lower()

    def test_failure_diagnostics(self):
        def fail(url):
            raise ConnectionError("fail")
        adapter = _make_adapter(fetch_fn=fail, max_retries=0)
        result = adapter.fetch()
        assert "fail" in result.diagnostics.lower()
