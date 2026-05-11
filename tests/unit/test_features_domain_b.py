from pytest import approx

from siasa.data.normalized_models import NormalizedRecord
from siasa.features.domain_b import DomainBFeatureService


def _record(signal_key: str, value: float, source_id: str, **quality_context: float) -> NormalizedRecord:
    return NormalizedRecord(
        normalized_id=f"N-{signal_key}-{source_id}",
        country_id="UKR",
        timestamp="2026-05-11T14:00:00Z",
        domain="B",
        signal_key=signal_key,
        value=value,
        provenance_source_id=source_id,
        quality_context=quality_context,
    )


def test_domain_b_feature_service_emits_event_conflict_protest_violence_and_disaster_indicators() -> None:
    service = DomainBFeatureService()
    records = [
        _record("conflict_event_count", 4.0, "SRC-1", expected_source_count=4, freshness_hours=8),
        _record("protest_event_count", 2.0, "SRC-2", expected_source_count=4, freshness_hours=10),
        _record("violent_event_count", 1.0, "SRC-2", expected_source_count=4, freshness_hours=10),
        _record("disaster_alert_level", 3.0, "SRC-3", expected_source_count=4, freshness_hours=24),
    ]

    features = {feature.feature_id: feature for feature in service.compute(records)}

    assert features["B_event_count"].value == 7.0
    assert features["B_violent_event_count"].value == 1.0
    assert features["B_protest_event_count"].value == 2.0
    assert features["B_violent_event_share"].value == approx(1.0 / 7.0)
    assert features["B_disaster_alert_level"].value == 3.0
    assert features["B_event_type_distribution"].value == {
        "conflict": approx(4.0 / 7.0),
        "protest": approx(2.0 / 7.0),
        "violent": approx(1.0 / 7.0),
    }
    assert features["B_event_count"].coverage == 0.75
    assert features["B_event_count"].confidence_inputs["freshness_hours"] == 24
