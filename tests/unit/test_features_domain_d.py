from siasa.data.normalized_models import NormalizedRecord
from siasa.features.domain_d import DomainDFeatureService


def _record(signal_key: str, value: float, source_id: str, country_id: str = "UKR", **quality_context: float) -> NormalizedRecord:
    return NormalizedRecord(
        normalized_id=f"N-{country_id}-{signal_key}-{source_id}",
        country_id=country_id,
        timestamp="2026-05-11T14:00:00Z",
        domain="D",
        signal_key=signal_key,
        value=value,
        provenance_source_id=source_id,
        quality_context=quality_context,
    )


def test_domain_d_feature_service_emits_trade_energy_macro_and_food_indicators() -> None:
    service = DomainDFeatureService()
    records = [
        _record("trade_volume_change", -5.0, "SRC-TRADE", expected_source_count=5, freshness_hours=72),
        _record("energy_price_stress", 1.4, "SRC-ENERGY", expected_source_count=5, freshness_hours=48),
        _record("gdp_growth", 2.1, "SRC-MACRO", expected_source_count=5, freshness_hours=720),
        _record("food_price_proxy", 1.8, "SRC-FOOD", expected_source_count=5, freshness_hours=96),
    ]

    features = {feature.feature_id: feature for feature in service.compute(records)}

    assert features["D_trade_volume_change"].value == -5.0
    assert features["D_energy_price_stress"].value == 1.4
    assert features["D_gdp_growth"].value == 2.1
    assert features["D_food_price_proxy"].value == 1.8
    assert features["D_macro_data_freshness"].value == 720
    assert features["D_trade_volume_change"].coverage == 0.8
    assert features["D_trade_volume_change"].confidence_inputs["source_count"] == 4



def test_domain_d_feature_service_groups_outputs_per_country() -> None:
    service = DomainDFeatureService()
    records = [
        _record("gdp_growth", 2.1, "SRC-MACRO", country_id="UKR", expected_source_count=2, freshness_hours=720),
        _record("trade_volume_change", -5.0, "SRC-TRADE", country_id="UKR", expected_source_count=2, freshness_hours=72),
        _record("gdp_growth", 1.5, "SRC-MACRO", country_id="POL", expected_source_count=2, freshness_hours=360),
        _record("trade_volume_change", 0.7, "SRC-TRADE", country_id="POL", expected_source_count=2, freshness_hours=48),
    ]

    features = service.compute(records)
    gdp_growth_by_country = {
        feature.country_id: feature.value for feature in features if feature.feature_id == "D_gdp_growth"
    }

    assert gdp_growth_by_country == {"UKR": 2.1, "POL": 1.5}



def test_domain_d_feature_service_keeps_feature_specific_freshness_horizons() -> None:
    service = DomainDFeatureService()
    records = [
        _record(
            "gdp_growth",
            2.1,
            "SRC-MACRO",
            expected_source_count=2,
            freshness_hours=8760,
            freshness_horizon_hours=8760,
        ),
        _record(
            "trade_volume_change",
            -5.0,
            "SRC-TRADE",
            expected_source_count=2,
            freshness_hours=240,
        ),
    ]

    features = {feature.feature_id: feature for feature in service.compute(records)}

    assert features["D_gdp_growth"].confidence_inputs["freshness_horizon_hours"] == 8760
    assert "freshness_horizon_hours" not in features["D_trade_volume_change"].confidence_inputs
