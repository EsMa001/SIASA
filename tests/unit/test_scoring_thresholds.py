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


def test_anomaly_module_has_no_import_time_threshold_constants():
    """SwR-109: thresholds are resolved per call, never frozen at import.

    The former module constants (ANOMALY_UPPER_BOUND, _MIN_SERIES_POINTS) made
    override_thresholds silently ineffective for this family (audit A-02).
    """
    from siasa.scoring import anomaly

    assert not hasattr(anomaly, "ANOMALY_UPPER_BOUND")
    assert not hasattr(anomaly, "_MIN_SERIES_POINTS")
    # The getters remain the single source of truth.
    assert anomaly_upper_bound() == 1.5
    assert anomaly_min_series_points() == 4


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


def test_consumer_modules_hold_no_import_time_threshold_constants():
    """SwR-109: no consumer module may freeze governed thresholds at import.

    The former module constants made override_thresholds — and with it every
    sensitivity sweep and test — silently ineffective for 8 of 10 consumer
    families (audit A-02). Behavioural per-call proof lives in
    tests/unit/test_threshold_wiring.py; this guard keeps the constants from
    creeping back in.
    """
    clear_threshold_cache()
    from siasa.analysis import info_epidemiology
    from siasa.scoring import cross_domain_fusion, probabilistic
    from siasa.validation import backtesting, historical_replay, skill_metrics

    banned = {
        probabilistic: ("_STATUS_SIGMA", "_STATUS_ANOMALY_CENTERS", "_CREDIBLE_INTERVAL_TAIL"),
        cross_domain_fusion: (
            "_CONTRADICTION_GAP",
            "_RELIABILITY_SUFFICIENT",
            "_RELIABILITY_PARTIAL",
            "_RELIABILITY_INSUFFICIENT",
            "_CONFIDENCE_FLOOR",
            "_CONFIDENCE_DISCOUNT_PER_GAP",
        ),
        skill_metrics: ("_DETECTION_WEIGHT", "_DOMAIN_MATCH_WEIGHT"),
        historical_replay: (
            "_TIER_VERIFIED",
            "_TIER_STRONG",
            "_TIER_PARTIAL",
            "_EVIDENCE_W_STATUS",
            "_EVIDENCE_W_DOMAIN",
            "_EVIDENCE_W_COVERAGE",
            "_EVIDENCE_W_PROVENANCE",
        ),
        backtesting: (
            "_SCORE_REGRESSION_THRESHOLD",
            "_REGRESSION_RATE_WARNING",
            "_REGRESSION_RATE_FAIL",
        ),
        info_epidemiology: ("_AMPLIFICATION_RATIO",),
    }
    offenders = [
        f"{module.__name__}.{name}"
        for module, names in banned.items()
        for name in names
        if hasattr(module, name)
    ]
    assert offenders == [], f"import-time threshold constants reintroduced: {offenders}"
