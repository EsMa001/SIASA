"""Tests for HDXInformRiskAdapter — INFORM Risk Index via HDX CSV.

Traceability: SwR-ADAPTER-HDX-INFORM, AP-11.6
"""
from __future__ import annotations

from datetime import UTC, datetime

from siasa.adapters.base import FetchResult
from siasa.adapters.hdx_inform import HDXInformRiskAdapter, _TARGET_INDICATORS


class StubFetcher:
    def __init__(self, response: str = "", error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.urls: list[str] = []

    def __call__(self, url: str) -> str:
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        return self.response


class SequenceFetcher:
    def __init__(self, responses: list) -> None:
        self.responses = list(responses)
        self.urls: list[str] = []

    def __call__(self, url: str) -> str:
        self.urls.append(url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


FIXED_NOW = datetime(2026, 6, 22, 10, 0, 0, tzinfo=UTC)


def _fixed_now() -> datetime:
    return FIXED_NOW


def _make_csv(rows: list[dict]) -> str:
    """Build a CSV string from row dicts (trends format)."""
    header = "CountryName,Iso3,GNAYear,IndicatorId,FullName,IndicatorScore\n"
    lines = []
    for r in rows:
        lines.append(
            f"{r.get('name','')},{r.get('iso3','')},{r.get('year','2025')},"
            f"{r.get('indicator_id','')},{r.get('full_name', r.get('indicator',''))},{r.get('score','')}\n"
        )
    return header + "".join(lines)


# --- Happy path ---

def test_hdx_inform_fetch_success_single_country() -> None:
    csv = _make_csv([
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "5.2"},
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "VU", "full_name": "Vulnerability Index", "score": "4.8"},
        {"name": "Poland", "iso3": "POL", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "2.1"},
    ])
    fetcher = StubFetcher(response=csv)
    adapter = HDXInformRiskAdapter(
        country_ids=("UKR",),
        fetch_text=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert isinstance(result, FetchResult)
    assert result.is_success is True
    assert len(result.records) == 2
    signals = {r["signal_key"] for r in result.records}
    assert "inform_risk" in signals
    assert "vulnerability" in signals
    assert all(r["country_id"] == "UKR" for r in result.records)
    assert "hdx_inform_fetch_ok" in result.diagnostics


def test_hdx_inform_multiple_countries() -> None:
    csv = _make_csv([
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "5.2"},
        {"name": "Poland", "iso3": "POL", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "2.1"},
        {"name": "Germany", "iso3": "DEU", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "1.5"},
    ])
    fetcher = StubFetcher(response=csv)
    adapter = HDXInformRiskAdapter(
        country_ids=("UKR", "POL", "DEU"),
        fetch_text=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 3
    countries = sorted(set(r["country_id"] for r in result.records))
    assert countries == ["DEU", "POL", "UKR"]


def test_hdx_inform_filters_unrequested_countries() -> None:
    csv = _make_csv([
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "5.2"},
        {"name": "Poland", "iso3": "POL", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "2.1"},
    ])
    fetcher = StubFetcher(response=csv)
    adapter = HDXInformRiskAdapter(
        country_ids=("UKR",),
        fetch_text=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 1
    assert result.records[0]["country_id"] == "UKR"


def test_hdx_inform_filters_non_target_indicators() -> None:
    csv = _make_csv([
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "5.2"},
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "DROUGHT", "full_name": "Drought affected", "score": "886000"},
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "SFM-E1", "full_name": "SFM Indicator E-1 Score", "score": "6.8"},
    ])
    fetcher = StubFetcher(response=csv)
    adapter = HDXInformRiskAdapter(
        country_ids=("UKR",),
        fetch_text=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 1
    assert result.records[0]["signal_key"] == "inform_risk"


def test_hdx_inform_exact_indicator_id_matching() -> None:
    csv = _make_csv([
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "5.2"},
    ])
    fetcher = StubFetcher(response=csv)
    adapter = HDXInformRiskAdapter(
        country_ids=("UKR",),
        fetch_text=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 1


def test_hdx_inform_skips_invalid_scores() -> None:
    csv = _make_csv([
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "n/a"},
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "VU", "full_name": "Vulnerability Index", "score": ""},
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "HA", "full_name": "Hazard & Exposure Index", "score": "3.5"},
    ])
    fetcher = StubFetcher(response=csv)
    adapter = HDXInformRiskAdapter(
        country_ids=("UKR",),
        fetch_text=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 1
    assert result.records[0]["signal_key"] == "hazard_exposure"


# --- Error handling ---

def test_hdx_inform_network_error_returns_failed() -> None:
    fetcher = StubFetcher(error=ConnectionError("timeout"))
    adapter = HDXInformRiskAdapter(
        country_ids=("UKR",),
        fetch_text=fetcher,
        now_provider=_fixed_now,
        max_retries=0,
    )

    result = adapter.fetch()

    assert result.is_success is False
    assert "hdx_inform_fetch_failed" in result.diagnostics


def test_hdx_inform_retry_on_transient_error() -> None:
    csv = _make_csv([
        {"name": "Ukraine", "iso3": "UKR", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "5.2"},
    ])
    fetcher = SequenceFetcher([
        ConnectionError("transient"),
        csv,
    ])
    sleep_calls: list[float] = []
    adapter = HDXInformRiskAdapter(
        country_ids=("UKR",),
        fetch_text=fetcher,
        now_provider=_fixed_now,
        retry_sleep=sleep_calls.append,
        max_retries=2,
        retry_backoff_seconds=1.0,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(sleep_calls) == 1


def test_hdx_inform_empty_csv_returns_empty() -> None:
    csv = "CountryName,Iso3,ValidityYear,IndicatorName,IndicatorScore,Unit\n"
    fetcher = StubFetcher(response=csv)
    adapter = HDXInformRiskAdapter(
        country_ids=("UKR",),
        fetch_text=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 0


# --- Schema ---

def test_hdx_inform_record_schema() -> None:
    csv = _make_csv([
        {"name": "Ukraine", "iso3": "UKR", "year": "2025", "indicator_id": "INFORM", "full_name": "INFORM Risk Index", "score": "5.2"},
    ])
    fetcher = StubFetcher(response=csv)
    adapter = HDXInformRiskAdapter(
        country_ids=("UKR",),
        fetch_text=fetcher,
        now_provider=_fixed_now,
    )

    result = adapter.fetch()

    assert result.is_success is True
    rec = result.records[0]
    required_keys = {
        "country_id", "period", "signal_key", "value", "indicator_name",
        "expected_source_count", "freshness_hours", "freshness_horizon_hours",
        "quality_flag",
    }
    assert required_keys.issubset(rec.keys())
    assert rec["period"] == "2025"
    assert rec["quality_flag"] == "hdx_inform_risk_index"


def test_target_indicators_has_core_set() -> None:
    """Ensure at minimum the composite risk + 3 dimensions are targeted."""
    assert "INFORM" in _TARGET_INDICATORS
    assert "HA" in _TARGET_INDICATORS
    assert "VU" in _TARGET_INDICATORS
    assert "CC" in _TARGET_INDICATORS
