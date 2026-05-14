from pytest import approx

from siasa.data.normalized_models import NormalizedRecord
from siasa.features.base import FeatureServiceRegistry
from siasa.features.domain_a import DomainAFeatureService


def _record(signal_key: str, value: float, source_id: str, country_id: str = "UKR", **quality_context: float) -> NormalizedRecord:
    return NormalizedRecord(
        normalized_id=f"N-{country_id}-{signal_key}-{source_id}",
        country_id=country_id,
        timestamp="2026-05-11T14:00:00Z",
        domain="A",
        signal_key=signal_key,
        value=value,
        provenance_source_id=source_id,
        quality_context=quality_context,
    )


def test_domain_a_feature_service_emits_volume_tone_topic_and_source_context_metrics() -> None:
    service = DomainAFeatureService()
    records = [
        _record("article_count", 3.0, "SRC-1", expected_source_count=4, freshness_hours=6),
        _record("tone", -0.2, "SRC-2", expected_source_count=4, freshness_hours=12),
        _record("topic:security", 2.0, "SRC-1", expected_source_count=4, freshness_hours=6),
        _record("topic:economy", 1.0, "SRC-2", expected_source_count=4, freshness_hours=12),
    ]

    features = {feature.feature_id: feature for feature in service.compute(records)}

    assert features["A_news_volume"].value == 3.0
    assert features["A_source_count"].value == 2.0
    assert features["A_source_diversity_index"].value == approx(2.0 / 3.0)
    assert features["A_tone_mean"].value == -0.2
    assert features["A_topic_distribution"].value == {"economy": approx(1.0 / 3.0), "security": approx(2.0 / 3.0)}
    assert features["A_news_volume"].coverage == 0.5
    assert features["A_news_volume"].confidence_inputs["freshness_hours"] == 12
    assert features["A_news_volume"].provenance_source_ids == ["SRC-1", "SRC-2"]


def test_domain_a_feature_service_groups_outputs_per_country() -> None:
    service = DomainAFeatureService()
    records = [
        _record("article_count", 3.0, "SRC-1", country_id="UKR", expected_source_count=2, freshness_hours=6),
        _record("tone", -0.2, "SRC-1", country_id="UKR", expected_source_count=2, freshness_hours=6),
        _record("article_count", 5.0, "SRC-2", country_id="POL", expected_source_count=2, freshness_hours=12),
        _record("tone", 0.1, "SRC-2", country_id="POL", expected_source_count=2, freshness_hours=12),
    ]

    features = service.compute(records)
    news_volume_by_country = {
        feature.country_id: feature.value for feature in features if feature.feature_id == "A_news_volume"
    }

    assert news_volume_by_country == {"UKR": 3.0, "POL": 5.0}



def test_feature_registry_supports_selective_optional_hooks_for_c_and_e() -> None:
    registry = FeatureServiceRegistry()
    registry.register_optional_hook("C", lambda records: [])

    assert registry.has_optional_hook("C") is True
    assert registry.has_optional_hook("E") is False
