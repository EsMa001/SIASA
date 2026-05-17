from siasa.features.base import FeatureValue
from siasa.scoring.data_sufficiency import evaluate_data_sufficiency



def _feature(
    feature_id: str,
    coverage: float,
    freshness_hours: float | None,
    freshness_horizon_hours: float | None = None,
) -> FeatureValue:
    confidence_inputs = {"record_count": 2, "source_count": 2}
    if freshness_hours is not None:
        confidence_inputs["freshness_hours"] = freshness_hours
    if freshness_horizon_hours is not None:
        confidence_inputs["freshness_horizon_hours"] = freshness_horizon_hours
    return FeatureValue(
        feature_id=feature_id,
        country_id="UKR",
        domain="A",
        value=1.0,
        provenance_source_ids=["SRC-1", "SRC-2"],
        coverage=coverage,
        confidence_inputs=confidence_inputs,
    )



def test_evaluate_data_sufficiency_reports_explicit_insufficiency_reasons() -> None:
    result = evaluate_data_sufficiency(
        [
            _feature("A_news_volume", coverage=0.4, freshness_hours=240),
            _feature("A_tone_mean", coverage=0.5, freshness_hours=240),
        ],
        minimum_coverage=0.6,
        maximum_freshness_hours=168.0,
        minimum_feature_count=2,
    )

    assert result.is_sufficient is False
    assert result.coverage == 0.45
    assert result.freshness_hours == 240.0
    assert result.reasons == ["coverage below threshold", "freshness beyond threshold"]



def test_evaluate_data_sufficiency_accepts_governed_inputs_when_thresholds_are_met() -> None:
    result = evaluate_data_sufficiency(
        [
            _feature("A_news_volume", coverage=0.8, freshness_hours=24),
            _feature("A_tone_mean", coverage=0.7, freshness_hours=24),
        ]
    )

    assert result.is_sufficient is True
    assert result.coverage == 0.75
    assert result.freshness_hours == 24.0
    assert result.reasons == []



def test_evaluate_data_sufficiency_does_not_let_annual_horizon_mask_stale_short_horizon_features() -> None:
    result = evaluate_data_sufficiency(
        [
            _feature("D_gdp_growth", coverage=1.0, freshness_hours=8760, freshness_horizon_hours=8760),
            _feature("A_news_volume", coverage=1.0, freshness_hours=240),
        ],
        maximum_freshness_hours=168.0,
    )

    assert result.is_sufficient is False
    assert result.reasons == ["freshness beyond threshold"]
    assert result.freshness_hours == 8760.0
