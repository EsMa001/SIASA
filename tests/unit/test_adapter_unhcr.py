"""Tests for the UNHCR Population Statistics adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from siasa.adapters.unhcr import UNHCRPopulationAdapter, _safe_int


def _make_item(
    coo_iso: str = "UKR",
    year: int = 2024,
    refugees: int | str = 6000000,
    asylum_seekers: int | str = 200000,
    idps: int | str = 3500000,
) -> dict[str, Any]:
    return {
        "year": year,
        "coo_id": 200,
        "coo_name": "Ukraine",
        "coo": coo_iso,
        "coo_iso": coo_iso,
        "coa_id": "-",
        "coa_name": "-",
        "coa": "-",
        "coa_iso": "-",
        "refugees": refugees,
        "asylum_seekers": asylum_seekers,
        "returned_refugees": "0",
        "idps": idps,
        "returned_idps": "0",
        "stateless": "0",
        "ooc": "0",
        "oip": "-",
        "hst": "0",
    }


def _make_response(
    items: list[dict[str, Any]],
    page: int = 1,
    max_pages: int = 1,
) -> dict[str, Any]:
    return {
        "page": page,
        "maxPages": max_pages,
        "total": [],
        "items": items,
    }


def _fixed_now() -> datetime:
    return datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)


def _no_sleep(_: float) -> None:
    pass


class TestUNHCRAdapterFetch:
    """Tests for successful data fetching and aggregation."""

    def test_single_country_aggregation(self):
        """Aggregate refugees, asylum seekers, IDPs from Ukraine."""
        items = [
            _make_item(coo_iso="UKR", year=2024, refugees=4000000, asylum_seekers=100000, idps=3000000),
            _make_item(coo_iso="UKR", year=2024, refugees=2000000, asylum_seekers=50000, idps=500000),
        ]

        call_log: list[str] = []

        def mock_fetch(url: str) -> Any:
            call_log.append(url)
            return _make_response(items)

        adapter = UNHCRPopulationAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert "unhcr_fetch_ok" in result.diagnostics
        assert len(result.records) > 0

        signals = {r["signal_key"]: r["value"] for r in result.records}
        assert signals["refugee_population"] == 6000000.0  # 4M + 2M
        assert signals["asylum_seeker_population"] == 150000.0  # 100k + 50k
        assert signals["idp_population"] == 3500000.0  # 3M + 500k
        assert signals["displacement_total"] == 9650000.0  # 6M + 150k + 3.5M

        assert all(r["country_id"] == "UKR" for r in result.records)
        assert all(r["quality_flag"] == "unhcr_population" for r in result.records)

    def test_uses_most_recent_year(self):
        """When multiple years exist, use the most recent."""
        items = [
            _make_item(year=2023, refugees=5000000),
            _make_item(year=2024, refugees=6000000),
            _make_item(year=2022, refugees=4000000),
        ]

        def mock_fetch(url: str) -> Any:
            return _make_response(items)

        adapter = UNHCRPopulationAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        signals = {r["signal_key"]: r["value"] for r in result.records}
        # Should use 2024 data only
        assert signals["refugee_population"] == 6000000.0

    def test_country_filter_excludes_others(self):
        items = [
            _make_item(coo_iso="UKR", refugees=6000000),
            _make_item(coo_iso="RUS", refugees=100000),
        ]

        def mock_fetch(url: str) -> Any:
            return _make_response(items)

        adapter = UNHCRPopulationAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert all(r["country_id"] == "UKR" for r in result.records)

    def test_no_country_filter_includes_all(self):
        items = [
            _make_item(coo_iso="UKR", refugees=6000000),
            _make_item(coo_iso="MMR", refugees=1200000),
        ]

        def mock_fetch(url: str) -> Any:
            return _make_response(items)

        adapter = UNHCRPopulationAdapter(
            country_ids=None,
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        countries = {r["country_id"] for r in result.records}
        assert "UKR" in countries
        assert "MMR" in countries

    def test_multi_page_pagination(self):
        page_data = {
            1: _make_response([_make_item(refugees=3000000)], page=1, max_pages=2),
            2: _make_response([_make_item(refugees=3000000)], page=2, max_pages=2),
        }

        def mock_fetch(url: str) -> Any:
            for page_num, resp in page_data.items():
                if f"page={page_num}" in url:
                    return resp
            return _make_response([])

        adapter = UNHCRPopulationAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        signals = {r["signal_key"]: r["value"] for r in result.records}
        assert signals["refugee_population"] == 6000000.0  # 3M + 3M

    def test_freshness_hours_computed(self):
        """Freshness should be hours since end of data year."""
        items = [_make_item(year=2024, refugees=1000)]

        def mock_fetch(url: str) -> Any:
            return _make_response(items)

        adapter = UNHCRPopulationAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,  # 2025-06-15 12:00
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        # 2024-12-31 00:00 to 2025-06-15 12:00 = ~3996 hours
        for record in result.records:
            assert record["freshness_hours"] > 3900
            assert record["freshness_hours"] < 4100

    def test_zero_values_excluded(self):
        """Signals with zero value should not produce records."""
        items = [_make_item(refugees=0, asylum_seekers=0, idps=0)]

        def mock_fetch(url: str) -> Any:
            return _make_response(items)

        adapter = UNHCRPopulationAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert result.records == []

    def test_dash_values_handled(self):
        """UNHCR API sometimes returns '-' for missing values."""
        items = [_make_item(refugees=1000, asylum_seekers="-", idps="-")]

        def mock_fetch(url: str) -> Any:
            return _make_response(items)

        adapter = UNHCRPopulationAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        signals = {r["signal_key"]: r["value"] for r in result.records}
        assert signals["refugee_population"] == 1000.0
        assert "idp_population" not in signals
        assert signals["displacement_total"] == 1000.0


class TestUNHCRAdapterRetry:
    """Tests for retry and error handling."""

    def test_retry_on_failure(self):
        call_count = 0

        def mock_fetch(url: str) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("network error")
            return _make_response([_make_item(refugees=1000)])

        adapter = UNHCRPopulationAdapter(
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

        adapter = UNHCRPopulationAdapter(
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            max_retries=2,
        )
        result = adapter.fetch()

        assert not result.is_success
        assert "unhcr_fetch_failed" in result.diagnostics

    def test_source_id_and_domain(self):
        adapter = UNHCRPopulationAdapter()
        assert adapter.source_id == "SRC-UNHCR-POP"
        assert adapter.domain == "C"


class TestSafeInt:
    """Tests for the _safe_int helper."""

    def test_normal_int(self):
        assert _safe_int(42) == 42.0

    def test_string_int(self):
        assert _safe_int("1000") == 1000.0

    def test_dash(self):
        assert _safe_int("-") == 0.0

    def test_none(self):
        assert _safe_int(None) == 0.0

    def test_empty_string(self):
        assert _safe_int("") == 0.0

    def test_float_string(self):
        assert _safe_int("3.14") == 3.14
