from __future__ import annotations

from datetime import UTC, datetime

from siasa.adapters.base import FetchResult
from siasa.data.normalization_mappings import NormalizationMappingVersion
from siasa.data.normalization_service import normalize_records
from siasa.features.domain_a import DomainAFeatureService
from siasa.adapters.gdelt_doc import GDELTDocAdapter


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


def test_gdelt_doc_adapter_fetch_transforms_artlist_payload_into_article_records() -> None:
    fetcher = SequenceFetcher(
        [
            {
                "articles": [
                    {
                        "url": "https://example.test/a",
                        "title": "Alpha",
                        "seendate": "20260513T060000Z",
                        "domain": "example.test",
                        "language": "English",
                        "sourcecountry": "United States",
                    },
                    {
                        "url": "https://example.test/b",
                        "title": "Beta",
                        "seendate": "20260513T050000Z",
                        "domain": "example.test",
                        "language": "English",
                        "sourcecountry": "United States",
                    },
                ]
            }
        ]
    )
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine"},
        fetch_json=fetcher,
        now_provider=lambda: datetime(2026, 5, 13, 8, 0, tzinfo=UTC),
        retry_sleep=lambda _seconds: None,
    )

    result = adapter.fetch()

    assert isinstance(result, FetchResult)
    assert result.is_success is True
    assert result.records[0] == {
        "country_id": "UKR",
        "timestamp": "2026-05-13T06:00:00Z",
        "signal_key": "article_count",
        "value": 1.0,
        "expected_source_count": 1,
        "freshness_hours": 2,
        "quality_flag": "gdelt_doc_api",
        "url": "https://example.test/a",
        "title": "Alpha",
        "domain": "example.test",
        "language": "English",
        "sourcecountry": "United States",
    }
    assert fetcher.urls == [
        "https://api.gdeltproject.org/api/v2/doc/doc?query=ukraine&mode=ArtList&maxrecords=50&format=json"
    ]


def test_gdelt_doc_adapter_retries_transient_failure_and_supports_domain_a_features() -> None:
    fetcher = SequenceFetcher(
        [
            RuntimeError("HTTP 429: Too Many Requests"),
            {
                "articles": [
                    {
                        "url": "https://example.test/a",
                        "title": "Alpha",
                        "seendate": "20260513T060000Z",
                        "domain": "example.test",
                        "language": "English",
                        "sourcecountry": "United States",
                    }
                ]
            },
        ]
    )
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine"},
        fetch_json=fetcher,
        now_provider=lambda: datetime(2026, 5, 13, 8, 0, tzinfo=UTC),
        retry_sleep=lambda _seconds: None,
    )

    result = adapter.fetch()
    normalized = normalize_records(
        source_id=adapter.source_id,
        domain=adapter.domain,
        raw_records=result.records,
        mappings=[
            NormalizationMappingVersion(
                mapping_id="MAP-GDELT-DOC-v1",
                source_id=adapter.source_id,
                version="v1",
                is_active=True,
            )
        ],
    )
    features = {feature.feature_id: feature for feature in DomainAFeatureService().compute(normalized)}

    assert result.is_success is True
    assert len(fetcher.urls) == 2
    assert features["A_news_volume"].value == 1.0
    assert features["A_source_count"].value == 1.0
    assert features["A_source_diversity_index"].value == 1.0


def test_gdelt_doc_adapter_returns_failed_fetch_result_after_retry_budget_is_exhausted() -> None:
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine"},
        fetch_json=SequenceFetcher([RuntimeError("HTTP 429"), RuntimeError("HTTP 429")]),
        retry_sleep=lambda _seconds: None,
        max_retries=2,
    )

    result = adapter.fetch()

    assert result.records == []
    assert result.is_success is False
    assert "HTTP 429" in result.diagnostics
