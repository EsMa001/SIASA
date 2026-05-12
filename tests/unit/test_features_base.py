from siasa.data.normalized_models import NormalizedRecord
from siasa.features.base import FeatureServiceRegistry, build_feature_value



def _record(signal_key: str, value: float, source_id: str, domain: str = "C", **quality_context: float) -> NormalizedRecord:
    return NormalizedRecord(
        normalized_id=f"N-{signal_key}-{source_id}",
        country_id="UKR",
        timestamp="2026-05-11T14:00:00Z",
        domain=domain,
        signal_key=signal_key,
        value=value,
        provenance_source_id=source_id,
        quality_context=quality_context,
    )



def test_build_feature_value_emits_provenance_coverage_and_confidence_inputs() -> None:
    records = [
        _record("signal_a", 1.0, "SRC-1", expected_source_count=4, freshness_hours=6),
        _record("signal_b", 2.0, "SRC-2", expected_source_count=4, freshness_hours=12),
    ]

    feature = build_feature_value("C_test_feature", "C", 3.0, records)

    assert feature.feature_id == "C_test_feature"
    assert feature.country_id == "UKR"
    assert feature.domain == "C"
    assert feature.value == 3.0
    assert feature.provenance_source_ids == ["SRC-1", "SRC-2"]
    assert feature.coverage == 0.5
    assert feature.confidence_inputs == {
        "record_count": 2,
        "source_count": 2,
        "freshness_hours": 12,
    }



def test_feature_registry_executes_registered_optional_hook_for_selective_c_and_e_processing() -> None:
    registry = FeatureServiceRegistry()
    records = [_record("hook_signal", 5.0, "SRC-1", domain="C")]

    registry.register_optional_hook("C", lambda items: [build_feature_value("C_hook_feature", "C", 5.0, items)])

    features = registry.execute_optional_hook("C", records)

    assert len(features) == 1
    assert features[0].feature_id == "C_hook_feature"
    assert registry.execute_optional_hook("E", records) == []
