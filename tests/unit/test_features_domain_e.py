from siasa.data.normalized_models import NormalizedRecord
from siasa.features.domain_e import DomainEFeatureService


def _record(
    signal_key: str, value: float, source_id: str, country_id: str = "UKR", **quality_context: float
) -> NormalizedRecord:
    return NormalizedRecord(
        normalized_id=f"N-{country_id}-{signal_key}-{source_id}",
        country_id=country_id,
        timestamp="2026-05-30T10:00:00Z",
        domain="E",
        signal_key=signal_key,
        value=value,
        provenance_source_id=source_id,
        quality_context=quality_context,
    )


def test_domain_e_feature_service_emits_cyber_info_ops_tech_and_diversity() -> None:
    """SwR-053: Domain E feature extraction produces expected features from GDELT-like records."""
    service = DomainEFeatureService()
    records = [
        _record("cyber_mention_count", 150.0, "SRC-GDELT-DOC", expected_source_count=2, freshness_hours=6),
        _record("info_ops_tone", -1.5, "SRC-GDELT-DOC", expected_source_count=2, freshness_hours=6),
        _record("tech_disruption_count", 12.0, "SRC-GDELT-EVENTS", expected_source_count=2, freshness_hours=12),
    ]

    features = {f.feature_id: f for f in service.compute(records)}

    assert "E_cyber_mention_volume" in features
    assert features["E_cyber_mention_volume"].value == 150.0
    assert "E_info_ops_tone" in features
    assert features["E_info_ops_tone"].value == -1.5
    assert "E_tech_disruption_signals" in features
    assert features["E_tech_disruption_signals"].value == 12.0
    assert "E_source_diversity_cyber" in features
    assert features["E_source_diversity_cyber"].value > 0.0
    assert "E_data_freshness" in features
    assert features["E_data_freshness"].value == 12


def test_domain_e_feature_service_groups_per_country() -> None:
    service = DomainEFeatureService()
    records = [
        _record("cyber_mention_count", 100.0, "SRC-GDELT-DOC", country_id="UKR", expected_source_count=1, freshness_hours=6),
        _record("cyber_mention_count", 50.0, "SRC-GDELT-DOC", country_id="CHN", expected_source_count=1, freshness_hours=12),
    ]

    features = service.compute(records)
    cyber_by_country = {
        f.country_id: f.value for f in features if f.feature_id == "E_cyber_mention_volume"
    }

    assert cyber_by_country == {"UKR": 100.0, "CHN": 50.0}


def test_domain_e_feature_service_returns_empty_for_no_domain_e_records() -> None:
    service = DomainEFeatureService()
    records = [
        NormalizedRecord(
            normalized_id="N-UKR-tone-SRC",
            country_id="UKR",
            timestamp="2026-05-30T10:00:00Z",
            domain="A",
            signal_key="tone",
            value=-2.0,
            provenance_source_id="SRC-GDELT",
        )
    ]

    assert service.compute(records) == []


def test_domain_e_feature_service_handles_single_source() -> None:
    service = DomainEFeatureService()
    records = [
        _record("cyber_mention_count", 80.0, "SRC-GDELT-DOC", expected_source_count=1, freshness_hours=3),
    ]

    features = {f.feature_id: f for f in service.compute(records)}

    assert features["E_cyber_mention_volume"].value == 80.0
    assert features["E_source_diversity_cyber"].value == 1.0  # 1 source / 1 record
    assert features["E_data_freshness"].value == 3


def test_domain_e_feature_service_supports_live_runtime_fallback_signals() -> None:
    service = DomainEFeatureService()
    records = [
        _record("article_count", 4.0, "SRC-GDELT-DOC-E", expected_source_count=1, freshness_hours=2),
        _record("tone", -0.8, "SRC-GDELT-DOC-E", expected_source_count=1, freshness_hours=2),
        _record("cyber_kev_overdue_count", 12.0, "SRC-CISA-KEV", expected_source_count=1, freshness_hours=0),
    ]

    features = {f.feature_id: f for f in service.compute(records)}

    assert features["E_cyber_mention_volume"].value == 4.0
    assert features["E_info_ops_tone"].value == -0.8
    assert features["E_tech_disruption_signals"].value == 12.0
