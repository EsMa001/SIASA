"""Tests for VoidlyAdapter — internet censorship scores via Voidly Atlas API.

Traceability: SwR-ADAPTER-VOIDLY, AP-11.3
"""
from __future__ import annotations

from datetime import UTC, datetime

from siasa.adapters.base import FetchResult
from siasa.adapters.voidly import VoidlyAdapter, _ISO2_TO_ISO3


class StubFetcher:
    def __init__(self, response: object = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url: str, headers: dict[str, str] | None = None) -> object:
        self.calls.append((url, headers or {}))
        if self.error is not None:
            raise self.error
        return self.response


class SequenceFetcher:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url: str, headers: dict[str, str] | None = None) -> object:
        self.calls.append((url, headers or {}))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


FIXED_NOW = datetime(2026, 6, 22, 10, 0, 0, tzinfo=UTC)


def _fixed_now() -> datetime:
    return FIXED_NOW


def _make_scores_response(scores: list[dict]) -> dict:
    return {
        "scores": scores,
        "totalCountries": len(scores),
        "dataSource": "hybrid",
        "modelVersion": "v2_hybrid",
        "timestamp": "2026-06-22T10:00:00Z",
    }


# --- Happy path ---

def test_voidly_fetch_success_single_country() -> None:
    payload = _make_scores_response([
        {"country": "CN", "name": "China", "score": 0.65, "confidence": 0.88, "samples": 38256, "lastUpdated": "2026-06-22T05:00:00Z"},
        {"country": "RU", "name": "Russia", "score": 0.32, "confidence": 0.87, "samples": 36651, "lastUpdated": "2026-06-22T05:00:00Z"},
    ])
    fetcher = StubFetcher(response=payload)
    adapter = VoidlyAdapter(
        country_ids=("CHN",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert isinstance(result, FetchResult)
    assert result.is_success is True
    assert len(result.records) == 1
    rec = result.records[0]
    assert rec["country_id"] == "CHN"
    assert rec["signal_key"] == "censorship_score"
    assert rec["value"] == 0.65
    assert rec["confidence"] == 0.88
    assert rec["samples"] == 38256
    assert rec["period"] == "2026-06-22"
    assert rec["quality_flag"] == "voidly_atlas_api"
    assert "voidly_fetch_ok" in result.diagnostics


def test_voidly_fetch_multiple_countries() -> None:
    payload = _make_scores_response([
        {"country": "CN", "name": "China", "score": 0.65, "confidence": 0.88, "samples": 38256, "lastUpdated": "2026-06-22T05:00:00Z"},
        {"country": "RU", "name": "Russia", "score": 0.32, "confidence": 0.87, "samples": 36651, "lastUpdated": "2026-06-22T05:00:00Z"},
        {"country": "IR", "name": "Iran", "score": 0.21, "confidence": 0.55, "samples": 4707, "lastUpdated": "2026-06-22T05:00:00Z"},
    ])
    fetcher = StubFetcher(response=payload)
    adapter = VoidlyAdapter(
        country_ids=("CHN", "RUS", "IRN"),
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 3
    countries = [r["country_id"] for r in result.records]
    assert countries == ["CHN", "IRN", "RUS"]  # sorted


def test_voidly_filters_unrequested_countries() -> None:
    """Only returns records for requested countries."""
    payload = _make_scores_response([
        {"country": "CN", "name": "China", "score": 0.65, "confidence": 0.88, "samples": 38256, "lastUpdated": "2026-06-22T05:00:00Z"},
        {"country": "RU", "name": "Russia", "score": 0.32, "confidence": 0.87, "samples": 36651, "lastUpdated": "2026-06-22T05:00:00Z"},
    ])
    fetcher = StubFetcher(response=payload)
    adapter = VoidlyAdapter(
        country_ids=("CHN",),  # Only China requested
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 1
    assert result.records[0]["country_id"] == "CHN"


def test_voidly_unmapped_country_in_response_skipped() -> None:
    """Countries in API response but not in ISO2→ISO3 map are skipped."""
    payload = _make_scores_response([
        {"country": "XX", "name": "Unknown", "score": 0.5, "confidence": 0.5, "samples": 100, "lastUpdated": "2026-06-22T05:00:00Z"},
    ])
    fetcher = StubFetcher(response=payload)
    adapter = VoidlyAdapter(
        country_ids=("XXX",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 0


def test_voidly_no_matching_countries() -> None:
    """Requested countries not in API response → empty records but success."""
    payload = _make_scores_response([
        {"country": "CN", "name": "China", "score": 0.65, "confidence": 0.88, "samples": 38256, "lastUpdated": "2026-06-22T05:00:00Z"},
    ])
    fetcher = StubFetcher(response=payload)
    adapter = VoidlyAdapter(
        country_ids=("POL",),  # Poland not in Voidly
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 0
    assert "matched=0" in result.diagnostics


def test_voidly_passes_api_key_in_header() -> None:
    payload = _make_scores_response([])
    fetcher = StubFetcher(response=payload)
    adapter = VoidlyAdapter(
        country_ids=("CHN",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
        api_key="test_key_123",
    )

    adapter.fetch()

    assert len(fetcher.calls) == 1
    _, headers = fetcher.calls[0]
    assert headers.get("X-API-Key") == "test_key_123"


# --- Error handling ---

def test_voidly_network_error_returns_failed() -> None:
    fetcher = StubFetcher(error=ConnectionError("timeout"))
    adapter = VoidlyAdapter(
        country_ids=("CHN",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
        max_retries=0,
    )

    result = adapter.fetch()

    assert result.is_success is False
    assert "voidly_fetch_failed" in result.diagnostics
    assert "timeout" in result.diagnostics


def test_voidly_retry_on_transient_error() -> None:
    payload = _make_scores_response([
        {"country": "CN", "name": "China", "score": 0.65, "confidence": 0.88, "samples": 38256, "lastUpdated": "2026-06-22T05:00:00Z"},
    ])
    fetcher = SequenceFetcher([
        ConnectionError("transient"),
        payload,
    ])
    sleep_calls: list[float] = []
    adapter = VoidlyAdapter(
        country_ids=("CHN",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
        retry_sleep=sleep_calls.append,
        max_retries=2,
        retry_backoff_seconds=0.5,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 1
    assert len(sleep_calls) == 1


def test_voidly_invalid_payload_returns_failure() -> None:
    fetcher = StubFetcher(response="not a dict")
    adapter = VoidlyAdapter(
        country_ids=("CHN",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
        max_retries=0,
    )

    result = adapter.fetch()

    assert result.is_success is False


def test_voidly_missing_scores_key_returns_failure() -> None:
    fetcher = StubFetcher(response={"totalCountries": 0})
    adapter = VoidlyAdapter(
        country_ids=("CHN",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
        max_retries=0,
    )

    result = adapter.fetch()

    assert result.is_success is False


# --- Schema & mapping consistency ---

def test_iso2_to_iso3_map_coverage() -> None:
    """Map should have at least 40 entries."""
    assert len(_ISO2_TO_ISO3) >= 40


def test_voidly_record_schema() -> None:
    payload = _make_scores_response([
        {"country": "DE", "name": "Germany", "score": 0.02, "confidence": 0.95, "samples": 50000, "lastUpdated": "2026-06-22T05:00:00Z"},
    ])
    fetcher = StubFetcher(response=payload)
    adapter = VoidlyAdapter(
        country_ids=("DEU",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    rec = result.records[0]
    required_keys = {
        "country_id", "period", "signal_key", "value", "confidence",
        "samples", "expected_source_count", "freshness_hours",
        "freshness_horizon_hours", "quality_flag",
    }
    assert required_keys.issubset(rec.keys())
