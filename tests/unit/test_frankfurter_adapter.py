"""Tests for FrankfurterAdapter — ECB exchange rates via Frankfurter API.

Traceability: SwR-ADAPTER-FRANKFURTER, AP-11.2
"""
from __future__ import annotations

from datetime import UTC, datetime

from siasa.adapters.base import FetchResult
from siasa.adapters.frankfurter import FrankfurterAdapter, _ISO3_TO_CURRENCY, _SUPPORTED_CURRENCIES


class StubFetcher:
    def __init__(self, response: object = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.urls: list[str] = []

    def __call__(self, url: str) -> object:
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        return self.response


class SequenceFetcher:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.urls: list[str] = []

    def __call__(self, url: str) -> object:
        self.urls.append(url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


FIXED_NOW = datetime(2026, 6, 22, 10, 0, 0, tzinfo=UTC)


def _fixed_now() -> datetime:
    return FIXED_NOW


def _make_latest_response(rates: dict[str, float], date: str = "2026-06-20") -> dict:
    return {
        "amount": 1.0,
        "base": "USD",
        "date": date,
        "rates": rates,
    }


# --- Happy path ---

def test_frankfurter_fetch_success_single_country() -> None:
    payload = _make_latest_response({"PLN": 3.95})
    fetcher = StubFetcher(response=payload)
    adapter = FrankfurterAdapter(
        country_ids=("POL",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert isinstance(result, FetchResult)
    assert result.is_success is True
    assert len(result.records) == 1
    rec = result.records[0]
    assert rec["country_id"] == "POL"
    assert rec["signal_key"] == "ecb_fx_pln_per_usd"
    assert rec["value"] == 3.95
    assert rec["currency"] == "PLN"
    assert rec["period"] == "2026-06-20"
    assert rec["quality_flag"] == "ecb_frankfurter_api"
    assert "frankfurter_fetch_ok" in result.diagnostics
    assert len(fetcher.urls) == 1
    assert "symbols=PLN" in fetcher.urls[0]


def test_frankfurter_fetch_success_multiple_countries() -> None:
    payload = _make_latest_response({"EUR": 0.87, "PLN": 3.95, "GBP": 0.76})
    fetcher = StubFetcher(response=payload)
    adapter = FrankfurterAdapter(
        country_ids=("DEU", "POL", "GBR"),
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 3
    countries = [r["country_id"] for r in result.records]
    assert countries == ["DEU", "GBR", "POL"]  # sorted
    currencies = [r["currency"] for r in result.records]
    assert currencies == ["EUR", "GBP", "PLN"]


def test_frankfurter_fetch_eurozone_countries_share_eur() -> None:
    """Multiple eurozone countries should all get EUR rate."""
    payload = _make_latest_response({"EUR": 0.87})
    fetcher = StubFetcher(response=payload)
    adapter = FrankfurterAdapter(
        country_ids=("DEU", "FRA", "ITA"),
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 3
    for rec in result.records:
        assert rec["currency"] == "EUR"
        assert rec["value"] == 0.87
    # Should be a single API call (one unique currency)
    assert len(fetcher.urls) == 1


def test_frankfurter_usa_gets_base_rate_1() -> None:
    """USA uses USD (base currency) → rate should be 1.0."""
    payload = _make_latest_response({"PLN": 3.95})
    fetcher = StubFetcher(response=payload)
    adapter = FrankfurterAdapter(
        country_ids=("USA", "POL"),
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    usa_records = [r for r in result.records if r["country_id"] == "USA"]
    assert len(usa_records) == 1
    assert usa_records[0]["value"] == 1.0
    assert usa_records[0]["signal_key"] == "ecb_fx_usd_per_usd"


def test_frankfurter_all_usa_returns_base_only() -> None:
    """If only USA is requested, no API call needed."""
    fetcher = StubFetcher(response=None)  # Should not be called
    adapter = FrankfurterAdapter(
        country_ids=("USA",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 1
    assert result.records[0]["value"] == 1.0
    assert "frankfurter_base_only" in result.diagnostics
    assert len(fetcher.urls) == 0  # No API call made


def test_frankfurter_unmapped_country_skipped() -> None:
    """Countries without ISO3→currency mapping are silently skipped."""
    payload = _make_latest_response({"PLN": 3.95})
    fetcher = StubFetcher(response=payload)
    adapter = FrankfurterAdapter(
        country_ids=("POL", "XXX"),  # XXX not in mapping
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 1
    assert result.records[0]["country_id"] == "POL"


def test_frankfurter_no_mapped_countries() -> None:
    """All countries unmapped → empty but success."""
    fetcher = StubFetcher(response=None)
    adapter = FrankfurterAdapter(
        country_ids=("XXX", "YYY"),
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 0
    assert "frankfurter_no_mapped_currencies" in result.diagnostics


# --- Error handling ---

def test_frankfurter_network_error_returns_failed_fetch_result() -> None:
    fetcher = StubFetcher(error=ConnectionError("network down"))
    adapter = FrankfurterAdapter(
        country_ids=("POL",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
        max_retries=0,
    )

    result = adapter.fetch()

    assert result.is_success is False
    assert "frankfurter_fetch_failed" in result.diagnostics
    assert "network down" in result.diagnostics


def test_frankfurter_retry_on_transient_error() -> None:
    payload = _make_latest_response({"PLN": 3.95})
    fetcher = SequenceFetcher([
        ConnectionError("transient"),
        payload,
    ])
    sleep_calls: list[float] = []
    adapter = FrankfurterAdapter(
        country_ids=("POL",),
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
    assert sleep_calls[0] == 0.5  # first retry: 0.5 * 2^0


def test_frankfurter_exhausted_retries_returns_failure() -> None:
    fetcher = SequenceFetcher([
        ConnectionError("fail1"),
        ConnectionError("fail2"),
        ConnectionError("fail3"),
    ])
    sleep_calls: list[float] = []
    adapter = FrankfurterAdapter(
        country_ids=("POL",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
        retry_sleep=sleep_calls.append,
        max_retries=2,
        retry_backoff_seconds=1.0,
    )

    result = adapter.fetch()

    assert result.is_success is False
    assert "fail3" in result.diagnostics
    assert len(sleep_calls) == 2


def test_frankfurter_invalid_payload_returns_failure() -> None:
    fetcher = StubFetcher(response="not a dict")
    adapter = FrankfurterAdapter(
        country_ids=("POL",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
        max_retries=0,
    )

    result = adapter.fetch()

    assert result.is_success is False
    assert "frankfurter_fetch_failed" in result.diagnostics


def test_frankfurter_missing_rates_key_returns_failure() -> None:
    fetcher = StubFetcher(response={"amount": 1.0, "base": "USD", "date": "2026-06-20"})
    adapter = FrankfurterAdapter(
        country_ids=("POL",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
        max_retries=0,
    )

    result = adapter.fetch()

    assert result.is_success is False


# --- Currency mapping consistency ---

def test_iso3_to_currency_map_values_are_supported() -> None:
    """All mapped currencies should be in the supported set or be USD."""
    for iso3, currency in _ISO3_TO_CURRENCY.items():
        assert currency in _SUPPORTED_CURRENCIES or currency == "USD", (
            f"{iso3} maps to {currency} which is not in supported set"
        )


def test_frankfurter_record_schema() -> None:
    """Verify all required fields are present in output records."""
    payload = _make_latest_response({"PLN": 3.95})
    fetcher = StubFetcher(response=payload)
    adapter = FrankfurterAdapter(
        country_ids=("POL",),
        fetch_json=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    rec = result.records[0]
    required_keys = {
        "country_id", "period", "signal_key", "value", "currency",
        "expected_source_count", "freshness_hours", "freshness_horizon_hours",
        "quality_flag",
    }
    assert required_keys.issubset(rec.keys())
