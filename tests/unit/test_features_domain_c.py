from siasa.data.normalized_models import NormalizedRecord
from siasa.features.domain_c import DomainCFeatureService


def _record(
    signal_key: str, value: float, source_id: str, country_id: str = "UKR", **quality_context: float
) -> NormalizedRecord:
    return NormalizedRecord(
        normalized_id=f"N-{country_id}-{signal_key}-{source_id}",
        country_id=country_id,
        timestamp="2026-05-30T10:00:00Z",
        domain="C",
        signal_key=signal_key,
        value=value,
        provenance_source_id=source_id,
        quality_context=quality_context,
    )


def test_domain_c_feature_service_emits_event_count_severity_max_source_and_freshness() -> None:
    """SwR-052: Domain C feature extraction produces expected features from GDACS-like records."""
    service = DomainCFeatureService()
    records = [
        _record("disaster_alert_level", 3.0, "SRC-GDACS", expected_source_count=1, freshness_hours=12),
        _record("disaster_alert_level", 2.0, "SRC-GDACS-2", expected_source_count=1, freshness_hours=48),
    ]

    features = {feature.feature_id: feature for feature in service.compute(records)}

    assert "C_event_count" in features
    assert features["C_event_count"].value == 5.0  # sum_signal: 3.0 + 2.0
    assert "C_event_severity_mean" in features
    assert features["C_event_severity_mean"].value == 2.5  # mean: (3.0 + 2.0) / 2
    assert "C_max_alert_level" in features
    assert features["C_max_alert_level"].value == 3.0
    assert "C_affected_source_count" in features
    assert features["C_affected_source_count"].value == 2.0
    assert "C_data_freshness" in features
    assert features["C_data_freshness"].value == 48


def test_domain_c_feature_service_groups_per_country() -> None:
    service = DomainCFeatureService()
    records = [
        _record("disaster_alert_level", 3.0, "SRC-GDACS", country_id="UKR", expected_source_count=1, freshness_hours=12),
        _record("disaster_alert_level", 1.0, "SRC-GDACS", country_id="POL", expected_source_count=1, freshness_hours=24),
    ]

    features = service.compute(records)
    max_by_country = {
        f.country_id: f.value for f in features if f.feature_id == "C_max_alert_level"
    }

    assert max_by_country == {"UKR": 3.0, "POL": 1.0}


def test_domain_c_feature_service_returns_empty_for_no_domain_c_records() -> None:
    service = DomainCFeatureService()
    # Records with domain D, not C
    records = [
        NormalizedRecord(
            normalized_id="N-UKR-trade-SRC",
            country_id="UKR",
            timestamp="2026-05-30T10:00:00Z",
            domain="D",
            signal_key="trade_volume_change",
            value=-5.0,
            provenance_source_id="SRC-TRADE",
        )
    ]

    features = service.compute(records)
    assert features == []


def test_domain_c_feature_service_handles_single_record() -> None:
    service = DomainCFeatureService()
    records = [
        _record("disaster_alert_level", 2.0, "SRC-GDACS", expected_source_count=1, freshness_hours=6),
    ]

    features = {f.feature_id: f for f in service.compute(records)}

    assert features["C_event_count"].value == 2.0  # sum_signal of single value
    assert features["C_event_severity_mean"].value == 2.0
    assert features["C_max_alert_level"].value == 2.0
    assert features["C_affected_source_count"].value == 1.0
    assert features["C_data_freshness"].value == 6


def test_domain_c_feature_service_supports_displacement_fallback_signals() -> None:
    service = DomainCFeatureService()
    records = [
        _record("displacement_total", 1250.0, "SRC-UNHCR-POP", expected_source_count=1, freshness_hours=24),
        _record("humanitarian_report_count", 7.0, "SRC-RELIEFWEB", expected_source_count=1, freshness_hours=12),
    ]

    features = {f.feature_id: f for f in service.compute(records)}

    assert features["C_event_count"].value == 1250.0
    assert features["C_displacement_total"].value == 1250.0
    assert features["C_affected_source_count"].value == 2.0
