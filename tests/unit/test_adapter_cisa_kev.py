"""Tests for the CISA KEV (Known Exploited Vulnerabilities) adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from siasa.adapters.cisa_kev import CISAKEVAdapter


def _make_vuln(
    date_added: str = "2025-06-01",
    due_date: str = "2025-07-01",
    ransomware: str = "Unknown",
    cve_id: str = "CVE-2025-0001",
) -> dict[str, Any]:
    return {
        "cveID": cve_id,
        "vendorProject": "TestVendor",
        "product": "TestProduct",
        "vulnerabilityName": "Test Vulnerability",
        "dateAdded": date_added,
        "shortDescription": "A test vulnerability.",
        "requiredAction": "Apply updates.",
        "dueDate": due_date,
        "knownRansomwareCampaignUse": ransomware,
        "notes": "",
        "cwes": ["CWE-79"],
    }


def _make_catalog(vulns: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "title": "CISA Catalog of Known Exploited Vulnerabilities",
        "catalogVersion": "2025.06.15",
        "dateReleased": "2025-06-15T00:00:00Z",
        "count": len(vulns),
        "vulnerabilities": vulns,
    }


def _fixed_now() -> datetime:
    return datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)


def _no_sleep(_: float) -> None:
    pass


class TestCISAKEVAdapterFetch:
    """Tests for successful data fetching and signal computation."""

    def test_basic_fetch_produces_records(self):
        vulns = [
            _make_vuln(date_added="2025-06-01", due_date="2025-07-01"),
            _make_vuln(date_added="2025-06-10", due_date="2025-07-10", cve_id="CVE-2025-0002"),
        ]

        def mock_fetch(url: str) -> Any:
            return _make_catalog(vulns)

        adapter = CISAKEVAdapter(
            country_ids={"UKR", "POL"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert "cisa_kev_fetch_ok" in result.diagnostics
        assert len(result.records) > 0
        assert all(r["quality_flag"] == "cisa_kev_global" for r in result.records)

    def test_recent_count_within_window(self):
        vulns = [
            _make_vuln(date_added="2025-06-01"),  # 14 days ago -> within 30-day window
            _make_vuln(date_added="2025-05-01", cve_id="CVE-2025-0002"),  # 45 days ago -> outside
            _make_vuln(date_added="2025-06-14", cve_id="CVE-2025-0003"),  # 1 day ago -> within
        ]

        def mock_fetch(url: str) -> Any:
            return _make_catalog(vulns)

        adapter = CISAKEVAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            recent_days=30,
        )
        result = adapter.fetch()

        signals = {r["signal_key"]: r["value"] for r in result.records if r["country_id"] == "UKR"}
        assert signals["cyber_kev_recent_count"] == 2.0
        assert signals["cyber_kev_total"] == 3.0

    def test_ransomware_recent_counted(self):
        vulns = [
            _make_vuln(date_added="2025-06-10", ransomware="Known"),
            _make_vuln(date_added="2025-06-12", ransomware="Unknown", cve_id="CVE-2025-0002"),
            _make_vuln(date_added="2025-06-14", ransomware="Known", cve_id="CVE-2025-0003"),
        ]

        def mock_fetch(url: str) -> Any:
            return _make_catalog(vulns)

        adapter = CISAKEVAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        signals = {r["signal_key"]: r["value"] for r in result.records if r["country_id"] == "UKR"}
        assert signals["cyber_kev_ransomware_recent"] == 2.0

    def test_overdue_count(self):
        vulns = [
            _make_vuln(due_date="2025-06-01"),  # overdue (before Jun 15)
            _make_vuln(due_date="2025-06-20", cve_id="CVE-2025-0002"),  # not overdue
            _make_vuln(due_date="2025-01-01", cve_id="CVE-2025-0003"),  # overdue
        ]

        def mock_fetch(url: str) -> Any:
            return _make_catalog(vulns)

        adapter = CISAKEVAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        signals = {r["signal_key"]: r["value"] for r in result.records if r["country_id"] == "UKR"}
        assert signals["cyber_kev_overdue_count"] == 2.0

    def test_broadcast_to_all_target_countries(self):
        vulns = [_make_vuln(date_added="2025-06-10")]

        def mock_fetch(url: str) -> Any:
            return _make_catalog(vulns)

        adapter = CISAKEVAdapter(
            country_ids={"UKR", "POL", "DEU"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        countries = {r["country_id"] for r in result.records}
        assert countries == {"UKR", "POL", "DEU"}

        # Each country should get the same signals
        ukr_signals = {r["signal_key"]: r["value"] for r in result.records if r["country_id"] == "UKR"}
        pol_signals = {r["signal_key"]: r["value"] for r in result.records if r["country_id"] == "POL"}
        assert ukr_signals == pol_signals

    def test_default_pilot_set_when_no_country_filter(self):
        vulns = [_make_vuln()]

        def mock_fetch(url: str) -> Any:
            return _make_catalog(vulns)

        adapter = CISAKEVAdapter(
            country_ids=None,
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        countries = {r["country_id"] for r in result.records}
        assert "UKR" in countries
        assert "USA" in countries
        assert len(countries) >= 10

    def test_empty_catalog_produces_no_signal_records(self):
        """Total=0 means no records at all (all signals are 0)."""
        def mock_fetch(url: str) -> Any:
            return _make_catalog([])

        adapter = CISAKEVAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert result.records == []

    def test_freshness_hours_is_zero(self):
        """Global catalog fetched now => freshness = 0."""
        vulns = [_make_vuln()]

        def mock_fetch(url: str) -> Any:
            return _make_catalog(vulns)

        adapter = CISAKEVAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        for record in result.records:
            assert record["freshness_hours"] == 0


class TestCISAKEVAdapterRetry:
    """Tests for retry and error handling."""

    def test_retry_on_failure(self):
        call_count = 0

        def mock_fetch(url: str) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("network error")
            return _make_catalog([_make_vuln()])

        adapter = CISAKEVAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            max_retries=3,
        )
        result = adapter.fetch()

        assert result.is_success
        assert call_count == 3

    def test_all_retries_exhausted(self):
        def mock_fetch(url: str) -> Any:
            raise ConnectionError("persistent failure")

        adapter = CISAKEVAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            max_retries=2,
        )
        result = adapter.fetch()

        assert not result.is_success
        assert "cisa_kev_fetch_failed" in result.diagnostics

    def test_source_id_and_domain(self):
        adapter = CISAKEVAdapter()
        assert adapter.source_id == "SRC-CISA-KEV"
        assert adapter.domain == "E"
