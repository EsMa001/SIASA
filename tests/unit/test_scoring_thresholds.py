"""Unit tests for AP-24 governed scoring thresholds (F11).

Verifies the threshold loader (graceful fallback + config override) and that the
anomaly / domain-status modules are wired to it behaviour-preservingly.
"""
from __future__ import annotations

from siasa.scoring.data_sufficiency import DataSufficiencyResult
from siasa.scoring.domain_status import derive_domain_status
from siasa.scoring.scoring_thresholds import (
    amplification_ratio,
    anomaly_min_series_points,
    anomaly_upper_bound,
    bayesian_status_centers,
    bayesian_status_credible_interval_tail,
    bayesian_status_sigma,
    clear_threshold_cache,
    cross_domain_confidence_discount_per_gap,
    cross_domain_confidence_floor,
    cross_domain_contradiction_gap,
    cross_domain_reliability_weights,
    data_sufficiency_maximum_freshness_hours,
    data_sufficiency_minimum_coverage,
    data_sufficiency_minimum_feature_count,
    domain_status_cutpoints,
    override_thresholds,
    regression_thresholds,
    replay_evidence_tiers,
    replay_evidence_weights,
    skill_score_weights,
    uncertainty_ci_z,
    uncertainty_stage_noise,
)


def test_loader_falls_back_to_defaults_when_config_missing(tmp_path):
    missing = tmp_path / "nope.yaml"
    assert anomaly_upper_bound(missing) == 1.5
    assert anomaly_min_series_points(missing) == 4
    assert domain_status_cutpoints(missing) == (0.2, 0.5, 1.0)


def test_loader_reads_overridden_values_from_config(tmp_path):
    cfg = tmp_path / "scoring_thresholds.yaml"
    cfg.write_text(
        "anomaly:\n  upper_bound: 3.0\n  min_series_points: 20\n"
        "domain_status:\n  d1_max: 1.0\n  d2_max: 2.0\n  d3_max: 3.0\n",
        encoding="utf-8",
    )
    assert anomaly_upper_bound(cfg) == 3.0
    assert anomaly_min_series_points(cfg) == 20
    assert domain_status_cutpoints(cfg) == (1.0, 2.0, 3.0)


def test_governed_config_preserves_shipped_behaviour():
    # The committed vmodel/project/scoring_thresholds.yaml holds the current values.
    clear_threshold_cache()
    assert anomaly_upper_bound() == 1.5
    assert anomaly_min_series_points() == 4
    assert domain_status_cutpoints() == (0.2, 0.5, 1.0)


def test_override_thresholds_restores_previous_config():
    clear_threshold_cache()
    assert domain_status_cutpoints() == (0.2, 0.5, 1.0)
    with override_thresholds({("domain_status", "d3_max"): 3.0, ("anomaly", "upper_bound"): 3.0}):
        assert domain_status_cutpoints() == (0.2, 0.5, 3.0)
        assert anomaly_upper_bound() == 3.0
    assert domain_status_cutpoints() == (0.2, 0.5, 1.0)
    assert anomaly_upper_bound() == 1.5


def test_anomaly_module_constants_are_wired_to_governed_thresholds():
    from siasa.scoring import anomaly

    assert anomaly.ANOMALY_UPPER_BOUND == anomaly_upper_bound()
    assert anomaly._MIN_SERIES_POINTS == anomaly_min_series_points()


def test_domain_status_uses_governed_cutpoints():
    sufficient = DataSufficiencyResult(is_sufficient=True, coverage=1.0, freshness_hours=None, reasons=[])
    d1_max, d2_max, d3_max = domain_status_cutpoints()

    def status_for(score: float) -> str:
        return derive_domain_status("A", anomaly_score=score, sufficiency=sufficient).status

    assert status_for(d1_max - 0.01) == "D1"
    assert status_for(d1_max) == "D2"
    assert status_for(d2_max - 0.01) == "D2"
    assert status_for(d2_max) == "D3"
    assert status_for(d3_max - 0.01) == "D3"
    assert status_for(d3_max) == "D4"


def test_new_family_getters_fall_back_to_shipped_defaults(tmp_path):
    missing = tmp_path / "nope.yaml"
    assert data_sufficiency_minimum_coverage(missing) == 0.6
    assert data_sufficiency_maximum_freshness_hours(missing) == 168.0
    assert data_sufficiency_minimum_feature_count(missing) == 2
    assert bayesian_status_centers(missing) == {"D0": 0.0, "D1": 0.1, "D2": 0.35, "D3": 0.75, "D4": 1.0}
    assert bayesian_status_sigma(missing) == 0.2
    assert bayesian_status_credible_interval_tail(missing) == 0.1
    assert cross_domain_reliability_weights(missing) == (1.0, 0.6, 0.2)
    assert cross_domain_contradiction_gap(missing) == 2
    assert cross_domain_confidence_floor(missing) == 0.3
    assert cross_domain_confidence_discount_per_gap(missing) == 0.15
    assert uncertainty_ci_z(missing) == 1.645
    assert uncertainty_stage_noise(missing) == (0.10, 0.15, 0.05)
    assert skill_score_weights(missing) == (0.6, 0.4)
    assert replay_evidence_weights(missing) == (0.4, 0.3, 0.2, 0.1)
    assert replay_evidence_tiers(missing) == (0.95, 0.75, 0.5)
    assert regression_thresholds(missing) == (0.1, 0.1, 0.3)
    assert amplification_ratio(missing) == 1.5


def test_new_family_getters_read_overrides(tmp_path):
    cfg = tmp_path / "scoring_thresholds.yaml"
    cfg.write_text(
        "data_sufficiency: {minimum_coverage: 0.8}\n"
        "bayesian_status: {sigma: 0.3}\n"
        "cross_domain_fusion: {contradiction_gap: 3}\n"
        "uncertainty_propagation: {ci_z: 1.96}\n"
        "information_epidemiology: {amplification_ratio: 2.0}\n",
        encoding="utf-8",
    )
    assert data_sufficiency_minimum_coverage(cfg) == 0.8
    assert bayesian_status_sigma(cfg) == 0.3
    assert cross_domain_contradiction_gap(cfg) == 3
    assert uncertainty_ci_z(cfg) == 1.96
    assert amplification_ratio(cfg) == 2.0
    # keys absent from the override keep their shipped defaults
    assert data_sufficiency_minimum_feature_count(cfg) == 2


def test_consumer_modules_are_wired_to_governed_thresholds():
    clear_threshold_cache()
    from siasa.analysis import info_epidemiology
    from siasa.scoring import cross_domain_fusion, probabilistic
    from siasa.validation import backtesting, historical_replay, skill_metrics

    assert probabilistic._STATUS_SIGMA == bayesian_status_sigma()
    assert probabilistic._STATUS_ANOMALY_CENTERS == bayesian_status_centers()
    assert cross_domain_fusion._CONTRADICTION_GAP == cross_domain_contradiction_gap()
    assert cross_domain_fusion._RELIABILITY_SUFFICIENT == cross_domain_reliability_weights()[0]
    assert (skill_metrics._DETECTION_WEIGHT, skill_metrics._DOMAIN_MATCH_WEIGHT) == skill_score_weights()
    assert historical_replay._TIER_VERIFIED == replay_evidence_tiers()[0]
    assert (
        backtesting._SCORE_REGRESSION_THRESHOLD,
        backtesting._REGRESSION_RATE_WARNING,
        backtesting._REGRESSION_RATE_FAIL,
    ) == regression_thresholds()
    assert info_epidemiology._AMPLIFICATION_RATIO == amplification_ratio()
