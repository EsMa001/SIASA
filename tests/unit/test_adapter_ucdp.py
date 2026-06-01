"""Tests for the UCDP GED adapter."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

import pytest

from siasa.adapters.ucdp import UCDPAdapter, _ISO3_TO_UCDP_COUNTRY_ID


def _make_event(
    country_id: int = 369,
    best: int = 5,
    type_of_violence: int = 1,
    date_start: str = "2024-06-15",
) -> dict[str, Any]:
    return {
        "id": 12345,
        "country_id": country_id,
        "country": "Ukraine",
        "best": best,
        "type_of_violence": type_of_violence,
        "date_start": date_start,
        "date_end": date_start,
        "latitude": 48.5,
        "longitude": 35.0,
    }


def _make_response(
    events: list[dict[str, Any]],
    total_count: int | None = None,
    total_pages: int = 1,
) -> dict[str, Any]:
    return {
        "TotalCount": total_count or len(events),
        "TotalPages": total_pages,
        "Result": events,
    }


def _fixed_now() -> datetime:
    return datetime(2024, 7, 1, 12, 0, 0, tzinfo=UTC)


def _no_sleep(_: float) -> None:
    pass


class TestUCDPAdapterNoToken:
    """Tests for graceful degradation when no API token is available."""

    def test_no_token_returns_failed_result(self):
        adapter = UCDPAdapter(
            api_token="",
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        # Also clear env var
        env_backup = os.environ.pop("UCDP_API_TOKEN", None)
        try:
            result = adapter.fetch()
        finally:
            if env_backup is not None:
                os.environ["UCDP_API_TOKEN"] = env_backup

        assert not result.is_success
        assert "ucdp_no_api_token" in result.diagnostics
        assert "UCDP_API_TOKEN" in result.diagnostics
        assert result.records == []

    def test_token_from_env_var(self):
        """Adapter should pick up token from environment."""
        calls: list[str] = []

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            calls.append(url)
            assert headers["x-ucdp-access-token"] == "test-token-123"
            return _make_response([])

        adapter = UCDPAdapter(
            api_token="",
            api_token_env_var="UCDP_API_TOKEN",
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        env_backup = os.environ.get("UCDP_API_TOKEN")
        os.environ["UCDP_API_TOKEN"] = "test-token-123"
        try:
            result = adapter.fetch()
        finally:
            if env_backup is not None:
                os.environ["UCDP_API_TOKEN"] = env_backup
            else:
                os.environ.pop("UCDP_API_TOKEN", None)

        assert result.is_success
        assert len(calls) == 1


class TestUCDPAdapterFetch:
    """Tests for successful data fetching and aggregation."""

    def test_single_page_ukraine_events(self):
        events = [
            _make_event(country_id=369, best=5, type_of_violence=1, date_start="2024-06-15"),
            _make_event(country_id=369, best=3, type_of_violence=2, date_start="2024-06-14"),
            _make_event(country_id=369, best=0, type_of_violence=1, date_start="2024-06-13"),
        ]

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            return _make_response(events, total_pages=1)

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert "ucdp_fetch_ok" in result.diagnostics
        assert len(result.records) > 0

        # Check aggregated signals
        signals = {r["signal_key"]: r["value"] for r in result.records}
        assert signals["armed_conflict_events"] == 3.0
        assert signals["battle_deaths_best"] == 8.0  # 5 + 3 + 0
        assert signals["state_based_events"] == 2.0  # type_of_violence == 1

        # All records should be for UKR
        assert all(r["country_id"] == "UKR" for r in result.records)
        assert all(r["quality_flag"] == "ucdp_ged" for r in result.records)

    def test_country_filter_excludes_others(self):
        events = [
            _make_event(country_id=369, best=5),  # UKR
            _make_event(country_id=365, best=3),  # RUS
        ]

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            return _make_response(events, total_pages=1)

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert all(r["country_id"] == "UKR" for r in result.records)

    def test_no_country_filter_includes_all(self):
        events = [
            _make_event(country_id=369, best=5),  # UKR
            _make_event(country_id=365, best=3),  # RUS
        ]

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            return _make_response(events, total_pages=1)

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids=None,
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        countries = {r["country_id"] for r in result.records}
        assert "UKR" in countries
        assert "RUS" in countries

    def test_multi_page_pagination(self):
        page_0_events = [_make_event(country_id=369, best=1) for _ in range(3)]
        page_1_events = [_make_event(country_id=369, best=2) for _ in range(2)]

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            if "page=0" in url:
                return _make_response(page_0_events, total_pages=2)
            elif "page=1" in url:
                return _make_response(page_1_events, total_pages=2)
            return _make_response([])

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        signals = {r["signal_key"]: r["value"] for r in result.records}
        assert signals["armed_conflict_events"] == 5.0  # 3 + 2
        assert signals["battle_deaths_best"] == 7.0  # 3*1 + 2*2

    def test_freshness_hours_computed(self):
        events = [
            _make_event(country_id=369, date_start="2024-06-30"),
        ]

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            return _make_response(events, total_pages=1)

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,  # 2024-07-01 12:00
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        # 2024-06-30 00:00 to 2024-07-01 12:00 = 36 hours
        for record in result.records:
            assert record["freshness_hours"] == 36

    def test_unknown_country_id_skipped(self):
        events = [
            _make_event(country_id=99999, best=5),  # Unknown UCDP country ID
        ]

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            return _make_response(events, total_pages=1)

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids=None,
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert result.records == []


class TestUCDPAdapterRetry:
    """Tests for retry and error handling behavior."""

    def test_retry_on_failure(self):
        call_count = 0

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("network error")
            return _make_response([_make_event()], total_pages=1)

        adapter = UCDPAdapter(
            api_token="test-token",
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
        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            raise ConnectionError("persistent failure")

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            max_retries=2,
        )
        result = adapter.fetch()

        assert not result.is_success
        assert "ucdp_fetch_failed" in result.diagnostics

    def test_source_id_and_domain(self):
        adapter = UCDPAdapter()
        assert adapter.source_id == "SRC-UCDP-GED"
        assert adapter.domain == "B"


class TestISO3Mapping:
    """Tests for ISO-3 to UCDP numeric ID mapping completeness."""

    def test_pilot_countries_mapped(self):
        pilot = {"UKR", "RUS", "ISR", "TUR", "IND", "PAK", "GEO", "IRN", "CHN", "POL"}
        for iso3 in pilot:
            assert iso3 in _ISO3_TO_UCDP_COUNTRY_ID, f"Missing UCDP mapping for {iso3}"

    def test_mapping_values_unique(self):
        values = list(_ISO3_TO_UCDP_COUNTRY_ID.values())
        assert len(values) == len(set(values)), "Duplicate UCDP country IDs in mapping"
