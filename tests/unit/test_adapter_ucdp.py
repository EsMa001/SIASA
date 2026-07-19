"""Tests for the UCDP GED adapter."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
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


class _HTTPStatusError(Exception):
    """Stand-in for urllib's HTTPError, which exposes the status as `.code`."""

    def __init__(self, code: int) -> None:
        super().__init__(f"HTTP {code}")
        self.code = code


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
        """Exclusion happens server-side: only the requested id is asked for."""
        requested_urls: list[str] = []

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            requested_urls.append(url)
            return _make_response([_make_event(country_id=369, best=5)], total_pages=1)

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert "Country=369" in requested_urls[0]
        assert "365" not in requested_urls[0]  # RUS never requested
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
        """Pagination follows NextPageUrl, the documented mechanism."""
        page_0_events = [_make_event(country_id=369, best=1) for _ in range(3)]
        page_1_events = [_make_event(country_id=369, best=2) for _ in range(2)]

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            if "cursor=second" in url:
                return _make_response(page_1_events, total_pages=2)
            response = _make_response(page_0_events, total_pages=2)
            response["NextPageUrl"] = "https://ucdpapi.pcr.uu.se/api/x?cursor=second"
            return response

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

    def test_unrequested_country_reveals_ignored_filter(self):
        """A country we never asked for proves the server-side filter was ignored.

        UCDP silently ignores an unknown filter parameter and answers HTTP 200
        with the full global dataset, so a foreign country in the response is
        the only available signal that the query degraded.
        """
        events = [
            _make_event(country_id=99999, best=5),  # not in the requested set
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

        assert not result.is_success
        assert "ucdp_filter_not_applied" in result.diagnostics
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

    def test_live_runtime_country_list_is_fully_mapped(self):
        """live_runtime keeps its own UCDP country tuple; every entry must map.

        An entry there without a Gleditsch-Ward mapping here would be silently
        dropped from the server-side Country filter and never fetched.
        """
        from siasa.runs.live_runtime import _UCDP_SUPPORTED_LIVE_COUNTRIES

        unmapped = [
            iso3
            for iso3 in _UCDP_SUPPORTED_LIVE_COUNTRIES
            if iso3 not in _ISO3_TO_UCDP_COUNTRY_ID
        ]
        assert unmapped == [], (
            f"countries in _UCDP_SUPPORTED_LIVE_COUNTRIES without a UCDP id "
            f"mapping: {unmapped}"
        )


class TestUCDPAdapterServerSideQuery:
    """The request itself must carry the country and date filters (SwR-108).

    These assertions inspect the URL. The previous test suite discarded it,
    which is why an adapter that never sent a filter passed every test.
    """

    def _capture(self, **kwargs: Any) -> list[str]:
        urls: list[str] = []

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            urls.append(url)
            return _make_response([_make_event(country_id=369)], total_pages=1)

        adapter = UCDPAdapter(
            api_token="test-token",
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            **kwargs,
        )
        result = adapter.fetch()
        assert result.is_success, result.diagnostics
        return urls

    def test_country_filter_is_sent_server_side(self):
        urls = self._capture(country_ids={"UKR"})
        assert "Country=369" in urls[0]

    def test_multiple_countries_are_comma_separated(self):
        urls = self._capture(country_ids={"UKR", "RUS"})
        # Sorted Gleditsch-Ward ids: RUS=365, UKR=369; comma is url-encoded.
        assert "Country=365%2C369" in urls[0]

    def test_response_field_name_is_not_used_as_filter_key(self):
        """`country_id` is the response field; using it as a filter is ignored."""
        urls = self._capture(country_ids={"UKR"})
        assert "country_id=" not in urls[0]

    def test_explicit_date_window_is_sent(self):
        window = (
            datetime(2022, 2, 24, tzinfo=UTC),
            datetime(2022, 12, 31, tzinfo=UTC),
        )
        urls = self._capture(country_ids={"UKR"}, date_window=window)
        assert "StartDate=2022-02-24" in urls[0]
        assert "EndDate=2022-12-31" in urls[0]

    def test_default_window_uses_lookback_days(self):
        urls = self._capture(country_ids={"UKR"}, lookback_days=30)
        expected_start = (_fixed_now() - timedelta(days=30)).strftime("%Y-%m-%d")
        assert f"StartDate={expected_start}" in urls[0]
        assert f"EndDate={_fixed_now():%Y-%m-%d}" in urls[0]

    def test_default_lookback_exceeds_annual_release_lag(self):
        """Annual GED lags up to ~16 months; a shorter default returns nothing."""
        assert UCDPAdapter().lookback_days >= 500

    def test_configured_api_version_is_used(self):
        urls = self._capture(country_ids={"UKR"}, api_version="25.1")
        assert "/gedevents/25.1?" in urls[0]

    def test_default_api_version_is_current_annual_release(self):
        assert UCDPAdapter().api_version == "26.1"

    def test_pagesize_is_capped_at_api_maximum(self):
        urls = self._capture(country_ids={"UKR"}, page_size=5000)
        assert "pagesize=1000" in urls[0]


class TestUCDPAdapterWindowStability:
    """The requested window must not drift while paginating (SwR-108)."""

    def test_window_is_identical_on_every_page(self):
        """A clock-derived default window must be resolved once, not per page."""
        ticks = iter(range(100))

        def advancing_now() -> datetime:
            # Each call jumps a full day, so a per-page re-derivation of the
            # default lookback window would be plainly visible in the URLs.
            return datetime(2024, 7, 1, 12, 0, 0, tzinfo=UTC) + timedelta(days=next(ticks))

        urls: list[str] = []

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            urls.append(url)
            if "cursor=second" in url:
                return _make_response([_make_event(country_id=369)], total_pages=2)
            response = _make_response([_make_event(country_id=369)], total_pages=2)
            response["NextPageUrl"] = "https://ucdpapi.pcr.uu.se/api/x?cursor=second"
            return response

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=advancing_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert len(urls) == 2
        # Page 2 is a server-supplied cursor URL, so compare against the
        # window echoed in the diagnostics instead of re-parsing it.
        assert "StartDate=" in urls[0]
        window = result.diagnostics.split("window=")[1].split(" ")[0]
        start = window.split("..")[0]
        assert f"StartDate={start}" in urls[0]

    def test_page_fallback_reuses_the_same_window(self):
        """Without NextPageUrl the adapter appends `page`, keeping the window."""
        ticks = iter(range(100))

        def advancing_now() -> datetime:
            return datetime(2024, 7, 1, 12, 0, 0, tzinfo=UTC) + timedelta(days=next(ticks))

        urls: list[str] = []

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            urls.append(url)
            return _make_response([_make_event(country_id=369)], total_pages=3)

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=advancing_now,
            retry_sleep=_no_sleep,
            max_pages=3,
        )
        result = adapter.fetch()

        assert result.is_success
        assert len(urls) == 3

        def window_of(url: str) -> tuple[str, str]:
            start = url.split("StartDate=")[1].split("&")[0]
            end = url.split("EndDate=")[1].split("&")[0]
            return start, end

        assert window_of(urls[0]) == window_of(urls[1]) == window_of(urls[2])
        assert "page=1" in urls[1]
        assert "page=2" in urls[2]


class TestUCDPAdapterTruncation:
    """Stopping at max_pages must be reported, never silent (SwR-108)."""

    def test_truncated_crawl_fails_and_discards_partial_records(self):
        """An undercount looks like calm, so a partial crawl must not succeed."""

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            response = _make_response([_make_event(country_id=369)], total_pages=99)
            response["NextPageUrl"] = "https://ucdpapi.pcr.uu.se/api/x?cursor=more"
            return response

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            max_pages=2,
        )
        result = adapter.fetch()

        assert not result.is_success
        assert "ucdp_truncated" in result.diagnostics
        assert "max_pages=2" in result.diagnostics
        assert result.records == []

    def test_last_page_carrying_next_page_url_is_not_truncated(self):
        """TotalPages completes the crawl even when NextPageUrl is still set."""

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            response = _make_response([_make_event(country_id=369)], total_pages=1)
            response["NextPageUrl"] = "https://ucdpapi.pcr.uu.se/api/x?cursor=stale"
            return response

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            max_pages=1,
        )
        result = adapter.fetch()

        assert result.is_success, result.diagnostics
        assert "ucdp_truncated" not in result.diagnostics

    def test_empty_next_page_url_terminates_without_truncation(self):
        """An empty NextPageUrl is the documented end-of-data signal."""
        calls = 0

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            nonlocal calls
            calls += 1
            response = _make_response([_make_event(country_id=369)])
            response.pop("TotalPages")  # no TotalPages: NextPageUrl must decide
            response["NextPageUrl"] = ""
            return response

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            max_pages=2,
        )
        result = adapter.fetch()

        assert result.is_success, result.diagnostics
        assert "ucdp_truncated" not in result.diagnostics
        assert calls == 1  # no wasted quota request past the end of the data

    def test_complete_crawl_is_not_marked_truncated(self):
        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            return _make_response([_make_event(country_id=369)], total_pages=1)

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            max_pages=10,
        )
        result = adapter.fetch()

        assert result.is_success
        assert "ucdp_truncated" not in result.diagnostics


class TestUCDPAdapterUnusableCountrySet:
    """A country set that resolves to no GW id must fail, not go global (SwR-108)."""

    def test_unmapped_iso3_refuses_to_query(self):
        calls = 0

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            nonlocal calls
            calls += 1
            return _make_response([])

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"FRA"},  # valid ISO-3, absent from the pilot mapping
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert not result.is_success
        assert "ucdp_no_resolvable_countries" in result.diagnostics
        assert "FRA" in result.diagnostics
        assert calls == 0  # no request was sent, no quota spent

    def test_empty_country_set_refuses_to_query(self):
        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            raise AssertionError("no request may be sent")

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids=set(),
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert not result.is_success
        assert "ucdp_no_resolvable_countries" in result.diagnostics


class TestUCDPAdapterHostPinning:
    """The API token must never follow a pagination link off-host (SwR-108)."""

    def test_off_host_next_page_url_is_refused(self):
        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            response = _make_response([_make_event(country_id=369)], total_pages=5)
            response["NextPageUrl"] = "https://evil.example.com/api/steal?cursor=x"
            return response

        adapter = UCDPAdapter(
            api_token="secret-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert not result.is_success
        assert "ucdp_unexpected_host" in result.diagnostics
        assert "evil.example.com" in result.diagnostics

    def test_same_host_next_page_url_is_followed(self):
        urls: list[str] = []

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            urls.append(url)
            if "cursor=second" in url:
                return _make_response([_make_event(country_id=369)], total_pages=2)
            response = _make_response([_make_event(country_id=369)], total_pages=2)
            response["NextPageUrl"] = "https://ucdpapi.pcr.uu.se/api/gedevents/26.1?cursor=second"
            return response

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success, result.diagnostics
        assert len(urls) == 2


class TestUCDPAdapterQuotaProtection:
    """Authentication failures must not be retried (SwR-108).

    UCDP counts errors against the 5,000 requests/day quota, so retrying a
    rejected token burns four slots per call and can never succeed.
    """

    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_failure_is_terminal_and_not_retried(self, status: int):
        call_count = 0

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            nonlocal call_count
            call_count += 1
            raise _HTTPStatusError(status)

        adapter = UCDPAdapter(
            api_token="bad-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
            max_retries=3,
        )
        result = adapter.fetch()

        assert not result.is_success
        assert call_count == 1

    def test_transient_error_is_still_retried(self):
        call_count = 0

        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _HTTPStatusError(503)
            return _make_response([_make_event(country_id=369)], total_pages=1)

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
        assert call_count == 2


class TestUCDPAdapterDiagnostics:
    """Diagnostics must distinguish 'API returned nothing' from 'filter dropped all'."""

    def test_empty_response_is_reported_as_empty_window(self):
        def mock_fetch(url: str, headers: dict[str, str]) -> Any:
            return _make_response([], total_pages=1)

        adapter = UCDPAdapter(
            api_token="test-token",
            country_ids={"UKR"},
            fetch_json=mock_fetch,
            now_provider=_fixed_now,
            retry_sleep=_no_sleep,
        )
        result = adapter.fetch()

        assert result.is_success
        assert "ucdp_empty_window" in result.diagnostics
        assert result.records == []

    def test_fetched_rows_and_matched_events_can_diverge(self):
        """The two counters must be independent, not two names for one number.

        An event without a country_id passes the filter guard (it cannot be
        attributed to any country) but is dropped locally — the one remaining
        case where the API returns more rows than the adapter keeps.
        """
        anonymous_event = _make_event(country_id=369, best=7)
        del anonymous_event["country_id"]
        events = [
            _make_event(country_id=369, best=5),  # UKR — requested and kept
            anonymous_event,  # returned but unattributable
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
        assert "fetched_rows=2" in result.diagnostics
        assert "matched_events=1 " in result.diagnostics
        # The anonymous event's fatalities must not leak into the aggregate.
        signals = {r["signal_key"]: r["value"] for r in result.records}
        assert signals["battle_deaths_best"] == 5.0
