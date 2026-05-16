from __future__ import annotations

from datetime import UTC, datetime

from siasa.adapters.base import FetchResult
from siasa.data.normalization_mappings import NormalizationMappingVersion
from siasa.data.normalization_service import normalize_records
from siasa.features.domain_d import DomainDFeatureService
from siasa.adapters.world_bank import WorldBankIndicatorsAdapter


class StubFetcher:
    def __init__(self, responses: dict[str, object], error: Exception | None = None) -> None:
        self.responses = responses
        self.error = error
        self.urls: list[str] = []

    def __call__(self, url: str) -> object:
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        return self.responses[url]


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


class FakeRateLimitError(RuntimeError):
    def __init__(self, message: str, *, retry_after: str | None = None) -> None:
        super().__init__(message)
        self.code = 429
        self.headers = {} if retry_after is None else {"Retry-After": retry_after}


def test_world_bank_adapter_fetch_transforms_indicator_payloads_into_domain_d_records() -> None:
    responses = {
        "https://api.worldbank.org/v2/country/UKR;POL/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=1000&mrv=1": [
            {"page": 1, "pages": 1},
            [
                {"country": {"id": "UKR"}, "date": "2024", "value": 3.2},
                {"country": {"id": "POL"}, "date": "2024", "value": 2.8},
            ],
        ],
        "https://api.worldbank.org/v2/country/UKR;POL/indicator/NE.EXP.GNFS.KD.ZG?format=json&per_page=1000&mrv=1": [
            {"page": 1, "pages": 1},
            [
                {"country": {"id": "UKR"}, "date": "2024", "value": -4.5},
                {"country": {"id": "POL"}, "date": "2024", "value": 1.1},
            ],
        ],
    }
    fetcher = StubFetcher(responses)
    adapter = WorldBankIndicatorsAdapter(country_ids=("UKR", "POL"), fetch_json=fetcher)

    result = adapter.fetch()

    assert isinstance(result, FetchResult)
    assert result.is_success is True
    assert [record["signal_key"] for record in result.records] == [
        "gdp_growth",
        "gdp_growth",
        "trade_volume_change",
        "trade_volume_change",
    ]
    assert result.records[0] == {
        "country_id": "UKR",
        "period": "2024",
        "signal_key": "gdp_growth",
        "value": 3.2,
        "expected_source_count": 1,
        "freshness_hours": 8760,
        "quality_flag": "world_bank_api",
    }
    assert fetcher.urls == list(responses)


def test_world_bank_adapter_prefers_countryiso3code_from_live_like_payload() -> None:
    responses = {
        "https://api.worldbank.org/v2/country/UKR/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=1000&mrv=1": [
            {"page": 1, "pages": 1},
            [
                {
                    "country": {"id": "UA"},
                    "countryiso3code": "UKR",
                    "date": "2024",
                    "value": 3.2,
                },
            ],
        ],
        "https://api.worldbank.org/v2/country/UKR/indicator/NE.EXP.GNFS.KD.ZG?format=json&per_page=1000&mrv=1": [
            {"page": 1, "pages": 1},
            [
                {
                    "country": {"id": "UA"},
                    "countryiso3code": "UKR",
                    "date": "2024",
                    "value": 1.1,
                },
            ],
        ],
    }
    adapter = WorldBankIndicatorsAdapter(country_ids=("UKR",), fetch_json=StubFetcher(responses))

    result = adapter.fetch()

    assert result.is_success is True
    assert {record["country_id"] for record in result.records} == {"UKR"}



def test_world_bank_adapter_skips_empty_values_and_supports_domain_d_feature_computation() -> None:
    responses = {
        "https://api.worldbank.org/v2/country/UKR/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=1000&mrv=1": [
            {"page": 1, "pages": 1},
            [
                {"country": {"id": "UKR"}, "date": "2024", "value": 3.2},
            ],
        ],
        "https://api.worldbank.org/v2/country/UKR/indicator/NE.EXP.GNFS.KD.ZG?format=json&per_page=1000&mrv=1": [
            {"page": 1, "pages": 1},
            [
                {"country": {"id": "UKR"}, "date": "2024", "value": None},
            ],
        ],
    }
    adapter = WorldBankIndicatorsAdapter(country_ids=("UKR",), fetch_json=StubFetcher(responses))

    result = adapter.fetch()
    normalized = normalize_records(
        source_id=adapter.source_id,
        domain=adapter.domain,
        raw_records=result.records,
        mappings=[
            NormalizationMappingVersion(
                mapping_id="MAP-WB-INDICATORS-v1",
                source_id=adapter.source_id,
                version="v1",
                is_active=True,
            )
        ],
    )
    features = {feature.feature_id: feature for feature in DomainDFeatureService().compute(normalized)}

    assert len(result.records) == 1
    assert result.records[0]["signal_key"] == "gdp_growth"
    assert features["D_gdp_growth"].value == 3.2
    assert features["D_macro_data_freshness"].value == 8760


def test_world_bank_adapter_returns_failed_fetch_result_when_provider_call_fails() -> None:
    adapter = WorldBankIndicatorsAdapter(country_ids=("UKR",), fetch_json=StubFetcher({}, error=RuntimeError("provider down")))

    result = adapter.fetch()

    assert result.records == []
    assert result.is_success is False
    assert "provider down" in result.diagnostics



def test_world_bank_adapter_honors_numeric_retry_after_for_rate_limit_backoff() -> None:
    sleep_calls: list[float] = []
    payload = [
        {"page": 1, "pages": 1},
        [
            {"country": {"id": "UKR"}, "date": "2024", "value": 3.2},
        ],
    ]
    adapter = WorldBankIndicatorsAdapter(
        country_ids=("UKR",),
        fetch_json=SequenceFetcher(
            [
                FakeRateLimitError("HTTP 429: Too Many Requests", retry_after="7"),
                payload,
                payload,
            ]
        ),
        retry_sleep=sleep_calls.append,
        max_retries=2,
        retry_backoff_seconds=1.0,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert sleep_calls == [7.0]



def test_world_bank_adapter_honors_http_date_retry_after_for_rate_limit_backoff() -> None:
    sleep_calls: list[float] = []
    payload = [
        {"page": 1, "pages": 1},
        [
            {"country": {"id": "UKR"}, "date": "2024", "value": 3.2},
        ],
    ]
    adapter = WorldBankIndicatorsAdapter(
        country_ids=("UKR",),
        fetch_json=SequenceFetcher(
            [
                FakeRateLimitError(
                    "HTTP 429: Too Many Requests",
                    retry_after="Wed, 13 May 2026 08:00:07 GMT",
                ),
                payload,
                payload,
            ]
        ),
        retry_sleep=sleep_calls.append,
        now_provider=lambda: datetime(2026, 5, 13, 8, 0, 0, tzinfo=UTC),
        max_retries=2,
        retry_backoff_seconds=1.0,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert sleep_calls == [7.0]



def test_world_bank_adapter_returns_failed_fetch_result_for_invalid_retry_configuration() -> None:
    adapter = WorldBankIndicatorsAdapter(
        country_ids=("UKR",),
        fetch_json=SequenceFetcher([]),
        max_retries=0,
    )

    result = adapter.fetch()

    assert result.records == []
    assert result.is_success is False
    assert "max_retries" in result.diagnostics
