"""Tests for Wikipedia Pageviews adapter (SwR-072, AP-14.1).

TC-SwR-072-001: Verify WikipediaPageviewsAdapter fetches daily pageview counts,
normalizes to NormalizedRecord-compatible dicts, handles errors/retries,
and supports injectable fetch functions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from siasa.adapters.wikipedia_pageviews import (
    WikipediaPageviewsAdapter,
    _build_url,
)
from siasa.adapters.base import FetchResult


# ── Fixtures ──────────────────────────────────────────────────────────────

SAMPLE_RESPONSE = {
    "items": [
        {"project": "en.wikipedia", "article": "Ukraine", "views": 45231,
         "timestamp": "2026060100"},
        {"project": "en.wikipedia", "article": "Ukraine", "views": 52100,
         "timestamp": "2026060200"},
        {"project": "en.wikipedia", "article": "Ukraine", "views": 38900,
         "timestamp": "2026060300"},
    ]
}

SINGLE_DAY_RESPONSE = {
    "items": [
        {"project": "en.wikipedia", "article": "Syria", "views": 12000,
         "timestamp": "2026060100"},
    ]
}

EMPTY_RESPONSE: dict = {"items": []}

FIXED_NOW = datetime(2026, 6, 5, 12, 0, 0, tzinfo=timezone.utc)


def _make_adapter(
    fetch_fn=None,
    country_topics=None,
    now_fn=None,
    max_retries=3,
    lookback_days=3,
):
    """Create adapter with injectable dependencies."""
    if country_topics is None:
        country_topics = {"UKR": "Ukraine", "SYR": "Syria"}
    if now_fn is None:
        now_fn = lambda: FIXED_NOW  # noqa: E731
    return WikipediaPageviewsAdapter(
        country_topics=country_topics,
        fetch_json=fetch_fn or (lambda url: SAMPLE_RESPONSE),
        now_provider=now_fn,
        retry_sleep=lambda _: None,
        max_retries=max_retries,
        lookback_days=lookback_days,
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
        required = {"country_id", "period", "signal_key", "value",
                     "quality_flag"}
        assert required.issubset(set(rec.keys()))

    def test_signal_key_is_wiki_pageview_count(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["signal_key"] == "wiki_pageview_count"

    def test_value_is_numeric(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert isinstance(rec["value"], (int, float))
            assert rec["value"] >= 0


# ── 2. Country-topic mapping ─────────────────────────────────────────────

class TestCountryMapping:
    def test_country_id_matches_iso3(self):
        adapter = _make_adapter(
            country_topics={"UKR": "Ukraine"},
            fetch_fn=lambda url: SAMPLE_RESPONSE,
        )
        result = adapter.fetch()
        for rec in result.records:
            assert rec["country_id"] == "UKR"

    def test_multiple_countries_produce_records(self):
        """Each country triggers a separate API call and produces records."""
        calls = []
        def track_fetch(url):
            calls.append(url)
            return SINGLE_DAY_RESPONSE
        adapter = _make_adapter(
            country_topics={"UKR": "Ukraine", "SYR": "Syria"},
            fetch_fn=track_fetch,
        )
        result = adapter.fetch()
        assert len(calls) == 2  # one call per country
        country_ids = {r["country_id"] for r in result.records}
        assert country_ids == {"UKR", "SYR"}

    def test_empty_country_topics_returns_empty(self):
        adapter = _make_adapter(country_topics={})
        result = adapter.fetch()
        assert result.is_success is True
        assert result.records == []


# ── 3. Period / date handling ─────────────────────────────────────────────

class TestPeriodHandling:
    def test_period_format_is_iso_date(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            # Should be YYYY-MM-DD
            datetime.strptime(rec["period"], "%Y-%m-%d")

    def test_lookback_days_affects_url(self):
        urls = []
        def capture(url):
            urls.append(url)
            return SAMPLE_RESPONSE
        adapter = _make_adapter(fetch_fn=capture, lookback_days=7)
        adapter.fetch()
        # URL should contain a date range spanning 7 days
        assert len(urls) > 0
        # The start date should be 7 days before FIXED_NOW
        assert "20260529" in urls[0]  # 2026-06-05 minus 7 days


# ── 4. Aggregation ───────────────────────────────────────────────────────

class TestAggregation:
    def test_multi_day_response_aggregates_to_daily_records(self):
        adapter = _make_adapter(
            country_topics={"UKR": "Ukraine"},
            fetch_fn=lambda url: SAMPLE_RESPONSE,
        )
        result = adapter.fetch()
        # 3 items in SAMPLE_RESPONSE → 3 daily records
        assert len(result.records) == 3

    def test_values_match_source_views(self):
        adapter = _make_adapter(
            country_topics={"UKR": "Ukraine"},
            fetch_fn=lambda url: SAMPLE_RESPONSE,
        )
        result = adapter.fetch()
        values = sorted(r["value"] for r in result.records)
        assert values == sorted([45231, 52100, 38900])


# ── 5. URL construction ─────────────────────────────────────────────────

class TestUrlConstruction:
    def test_build_url_format(self):
        url = _build_url("Ukraine", "20260601", "20260603")
        assert "en.wikipedia.org" in url
        assert "Ukraine" in url
        assert "20260601" in url
        assert "20260603" in url
        assert "/per-article/" in url

    def test_build_url_encodes_spaces(self):
        url = _build_url("South Sudan", "20260601", "20260603")
        assert "South%20Sudan" in url or "South_Sudan" in url


# ── 6. Error handling ────────────────────────────────────────────────────

class TestErrorHandling:
    def test_api_error_returns_unsuccessful_result(self):
        def fail_fetch(url):
            raise ConnectionError("timeout")
        adapter = _make_adapter(fetch_fn=fail_fetch, max_retries=0)
        result = adapter.fetch()
        assert result.is_success is False
        assert result.records == []
        assert "failed" in result.diagnostics.lower() or "error" in result.diagnostics.lower()

    def test_empty_items_returns_empty_records(self):
        adapter = _make_adapter(
            country_topics={"UKR": "Ukraine"},
            fetch_fn=lambda url: EMPTY_RESPONSE,
        )
        result = adapter.fetch()
        assert result.is_success is True
        assert result.records == []

    def test_malformed_response_handled_gracefully(self):
        adapter = _make_adapter(
            country_topics={"UKR": "Ukraine"},
            fetch_fn=lambda url: {"unexpected": "format"},
        )
        result = adapter.fetch()
        # Should not crash — either empty records or is_success=False
        assert isinstance(result, FetchResult)


# ── 7. Retry logic ───────────────────────────────────────────────────────

class TestRetryLogic:
    def test_retries_on_transient_failure(self):
        """Single country — retries until success."""
        call_count = 0
        def flaky_fetch(url):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return SAMPLE_RESPONSE
        adapter = _make_adapter(
            fetch_fn=flaky_fetch, max_retries=3,
            country_topics={"UKR": "Ukraine"},
        )
        result = adapter.fetch()
        assert result.is_success is True
        assert call_count == 3

    def test_max_retries_zero_no_retry(self):
        """Single country, zero retries — fails immediately."""
        call_count = 0
        def always_fail(url):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("permanent")
        adapter = _make_adapter(
            fetch_fn=always_fail, max_retries=0,
            country_topics={"UKR": "Ukraine"},
        )
        result = adapter.fetch()
        assert result.is_success is False
        assert call_count == 1  # no retries

    def test_retry_sleep_called_with_backoff(self):
        """Single country — verify backoff sleep calls."""
        sleep_calls = []
        def fail_fetch(url):
            raise ConnectionError("fail")
        adapter = _make_adapter(
            fetch_fn=fail_fetch, max_retries=2,
            country_topics={"UKR": "Ukraine"},
        )
        adapter.retry_sleep = lambda d: sleep_calls.append(d)
        adapter.fetch()
        assert len(sleep_calls) == 2
        # Exponential backoff: first <= second
        assert sleep_calls[0] <= sleep_calls[1]


# ── 8. Source metadata ───────────────────────────────────────────────────

class TestSourceMetadata:
    def test_source_id(self):
        adapter = _make_adapter()
        assert adapter.source_id == "SRC-WIKIPEDIA-PAGEVIEWS"

    def test_domain_is_A(self):
        adapter = _make_adapter()
        assert adapter.domain == "A"

    def test_quality_flag_in_records(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert rec["quality_flag"] == "wikipedia_pageviews_api"


# ── 9. Diagnostics ──────────────────────────────────────────────────────

class TestDiagnostics:
    def test_success_diagnostics_contain_count(self):
        adapter = _make_adapter(
            country_topics={"UKR": "Ukraine"},
            fetch_fn=lambda url: SAMPLE_RESPONSE,
        )
        result = adapter.fetch()
        assert "records=" in result.diagnostics or "ok" in result.diagnostics.lower()

    def test_empty_topics_diagnostics(self):
        adapter = _make_adapter(country_topics={})
        result = adapter.fetch()
        assert "no" in result.diagnostics.lower() or "empty" in result.diagnostics.lower()


# ── 10. Integration-style: full cycle ────────────────────────────────────

class TestFullCycle:
    def test_full_fetch_cycle_multiple_countries(self):
        """End-to-end: multiple countries → multiple daily records."""
        responses = {
            "Ukraine": SAMPLE_RESPONSE,
            "Syria": SINGLE_DAY_RESPONSE,
        }
        def route_fetch(url):
            for topic, resp in responses.items():
                if topic in url:
                    return resp
            return EMPTY_RESPONSE

        adapter = _make_adapter(
            country_topics={"UKR": "Ukraine", "SYR": "Syria"},
            fetch_fn=route_fetch,
        )
        result = adapter.fetch()
        assert result.is_success is True
        # UKR: 3 records, SYR: 1 record = 4 total
        assert len(result.records) == 4
        ukr_records = [r for r in result.records if r["country_id"] == "UKR"]
        syr_records = [r for r in result.records if r["country_id"] == "SYR"]
        assert len(ukr_records) == 3
        assert len(syr_records) == 1

    def test_freshness_hours_in_records(self):
        adapter = _make_adapter()
        result = adapter.fetch()
        for rec in result.records:
            assert "freshness_hours" in rec or "freshness_horizon_hours" in rec
