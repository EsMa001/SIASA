"""Tests for the ReliefWeb Reports adapter."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import pytest

from siasa.adapters.reliefweb import ReliefWebAdapter, _RELIEFWEB_COUNTRY_NAMES


def _make_report(
    source_name: str = "OCHA",
    date_created: str = "2025-06-10T12:00:00+00:00",
) -> dict[str, Any]:
    return {
        "id": "12345",
        "fields": {
            "source": [{"name": source_name}],
            "date": {"created": date_created},
        },
    }


def _make_response(reports: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(reports),
        "data": reports,
    }


def _fixed_now() -> datetime:
    return datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)


def _no_sleep(_: float) -> None:
    pass


class TestReliefWebAdapterNoAppname:
    """Tests for graceful degradation when no appname is configured."""

    def test_no_appname_returns_failed_result(self):
        adapter = ReliefWebAdapter(
            appname="",
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        env_backup = os.environ.pop("RELIEFWEB_APPNAME", None)
        try:
            result = adapter.fetch()
        finally:
            if env_backup is not None:
                os.environ["RELIEFWEB_APPNAME"] = env_backup

        assert not result.is_success
        assert "reliefweb_no_appname" in result.diagnostics
        assert "RELIEFWEB_APPNAME" in result.diagnostics
        assert result.records == []

    def test_appname_from_env_var(self):
        calls: list[str] = []

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            calls.append(url)
            assert "siasa-approved" in url
            return _make_response([])

        adapter = ReliefWebAdapter(
            appname="",
            appname_env_var="RELIEFWEB_APPNAME",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        env_backup = os.environ.get("RELIEFWEB_APPNAME")
        os.environ["RELIEFWEB_APPNAME"] = "siasa-approved"
        try:
            result = adapter.fetch()
        finally:
            if env_backup is not None:
                os.environ["RELIEFWEB_APPNAME"] = env_backup
            else:
                os.environ.pop("RELIEFWEB_APPNAME", None)

        assert result.is_success
        assert len(calls) == 1


class TestReliefWebAdapterFetch:
    """Tests for successful data fetching and aggregation."""

    def test_single_country_reports(self):
        reports = [
            _make_report(source_name="OCHA", date_created="2025-06-10T12:00:00+00:00"),
            _make_report(source_name="UNHCR", date_created="2025-06-12T08:00:00+00:00"),
            _make_report(source_name="OCHA", date_created="2025-06-14T15:00:00+00:00"),
        ]

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            return _make_response(reports)

        adapter = ReliefWebAdapter(
            appname="test-app",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert "reliefweb_fetch_ok" in result.diagnostics

        signals = {r["signal_key"]: r["value"] for r in result.records}
        assert signals["humanitarian_report_count"] == 3.0
        assert signals["humanitarian_report_sources"] == 2.0  # OCHA + UNHCR

        assert all(r["country_id"] == "UKR" for r in result.records)
        assert all(r["quality_flag"] == "reliefweb_reports" for r in result.records)

    def test_multiple_countries(self):
        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            if "Ukraine" in url:
                return _make_response([_make_report()])
            elif "Pakistan" in url:
                return _make_response([_make_report(), _make_report(source_name="WHO")])
            return _make_response([])

        adapter = ReliefWebAdapter(
            appname="test-app",
            country_ids={"UKR", "PAK"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        countries = {r["country_id"] for r in result.records}
        assert "UKR" in countries
        assert "PAK" in countries

    def test_country_with_no_reports_excluded(self):
        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            return _make_response([])

        adapter = ReliefWebAdapter(
            appname="test-app",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert result.records == []

    def test_freshness_hours_computed(self):
        reports = [
            _make_report(date_created="2025-06-14T12:00:00+00:00"),
        ]

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            return _make_response(reports)

        adapter = ReliefWebAdapter(
            appname="test-app",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,  # 2025-06-15 12:00
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        # 2025-06-14 12:00 to 2025-06-15 12:00 = 24 hours
        for record in result.records:
            assert record["freshness_hours"] == 24

    def test_unmapped_country_skipped(self):
        """Countries without name mapping should be silently skipped."""
        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            return _make_response([_make_report()])

        adapter = ReliefWebAdapter(
            appname="test-app",
            country_ids={"XYZ"},  # Not in mapping
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert result.records == []

    def test_per_country_failure_does_not_abort(self):
        """One country's API failure should not prevent other countries."""
        call_count = 0

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            nonlocal call_count
            call_count += 1
            if "Pakistan" in url:
                raise ConnectionError("network error for PAK")
            return _make_response([_make_report()])

        adapter = ReliefWebAdapter(
            appname="test-app",
            country_ids={"UKR", "PAK"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            max_retries=0,  # No retry to speed up test
        )
        result = adapter.fetch()

        assert result.is_success
        countries = {r["country_id"] for r in result.records}
        assert "UKR" in countries
        assert "PAK" not in countries


class TestReliefWebAdapterRetry:
    """Tests for retry and error handling."""

    def test_retry_on_failure(self):
        call_count = 0

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("network error")
            return _make_response([_make_report()])

        adapter = ReliefWebAdapter(
            appname="test-app",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            max_retries=3,
        )
        result = adapter.fetch()

        assert result.is_success
        assert call_count == 3

    def test_source_id_and_domain(self):
        adapter = ReliefWebAdapter()
        assert adapter.source_id == "SRC-RELIEFWEB"
        assert adapter.domain == "C"


class TestCountryNameMapping:
    """Tests for pilot country name mapping completeness."""

    def test_core_pilot_countries_mapped(self):
        core = {"UKR", "RUS", "CHN", "ISR", "IND", "IRN", "TUR", "PAK", "GEO", "POL"}
        for iso3 in core:
            assert iso3 in _RELIEFWEB_COUNTRY_NAMES, f"Missing ReliefWeb name for {iso3}"

    def test_mapping_values_are_strings(self):
        for iso3, name in _RELIEFWEB_COUNTRY_NAMES.items():
            assert isinstance(name, str) and len(name) > 0, f"Invalid name for {iso3}"
