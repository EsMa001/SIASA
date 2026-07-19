"""TC-SwR-109-001: every governed threshold must be resolved at call time.

Audit finding A-02 (docs/research/wissenschaftliches-fundament-audit-2026-07.md):
8 of 10 consumer modules bound governed thresholds to module constants at import
time, so ``override_thresholds`` — the mechanism the sensitivity sweep, tests and
runtime configuration rely on — silently never reached them. Production followed
the YAML only because module import happened to run after the loader.

These tests prove, per family, that an override is visible in the *behaviour*
of the consuming function, not merely in the loader's return value.
"""

from __future__ import annotations

from types import SimpleNamespace

from siasa.analysis.info_epidemiology import SpreadObservation, detect_amplification
from siasa.scoring.anomaly import compute_feature_driven_anomaly
from siasa.scoring.cross_domain_fusion import (
    compute_evidence_weights,
    detect_cross_domain_contradictions,
    fuse_domain_evidence,
)
from siasa.scoring.data_sufficiency import DataSufficiencyResult
from siasa.scoring.domain_status import DomainStatusResult
from siasa.scoring.probabilistic import compute_bayesian_status
from siasa.scoring.scoring_thresholds import override_thresholds
from siasa.validation.backtesting import _compare_scores
from siasa.validation.historical_replay import (
    _replay_evidence_score,
    _replay_evidence_tier,
)
from siasa.validation.skill_metrics import compute_skill_metrics


def _sufficiency(is_sufficient: bool = True) -> DataSufficiencyResult:
    return DataSufficiencyResult(
        is_sufficient=is_sufficient,
        coverage=1.0 if is_sufficient else 0.0,
        freshness_hours=1.0,
        reasons=[] if is_sufficient else ["insufficient"],
    )


def _domain_result(domain: str, status: str, *, sufficient: bool = True) -> DomainStatusResult:
    return DomainStatusResult(
        domain=domain,
        status=status,
        anomaly_score=0.5,
        drivers=[],
        uncertainty_indicators=[],
        rule_references=[],
        sufficiency=_sufficiency(sufficient),
    )


def _record(value: float, ts: str, signal: str = "sig") -> SimpleNamespace:
    return SimpleNamespace(
        domain="B",
        signal_key=signal,
        value=value,
        timestamp=ts,
        normalized_id=f"n-{ts}",
        provenance_source_id="SRC-X",
        quality_context={"expected_source_count": 1},
    )


class TestAnomalyFamilyResolvesPerCall:
    def test_upper_bound_override_caps_the_result(self):
        # 4 points, last one an extreme spike -> |z| far above any small cap.
        records = [_record(1.0, "t1"), _record(1.0, "t2"), _record(1.0, "t3"), _record(100.0, "t4")]
        baseline = compute_feature_driven_anomaly("B", records)
        assert baseline > 0.07  # sanity: uncapped default exceeds the probe cap
        with override_thresholds({("anomaly", "upper_bound"): 0.07}):
            assert compute_feature_driven_anomaly("B", records) == 0.07

    def test_min_series_points_override_admits_short_series(self):
        records = [_record(1.0, "t1"), _record(100.0, "t2")]
        assert compute_feature_driven_anomaly("B", records) == 0.0  # default: 2 < 4
        with override_thresholds({("anomaly", "min_series_points"): 2}):
            assert compute_feature_driven_anomaly("B", records) > 0.0


class TestBayesianFamilyResolvesPerCall:
    def test_sigma_override_sharpens_the_posterior(self):
        default_conf = compute_bayesian_status(0.35).confidence
        with override_thresholds({("bayesian_status", "sigma"): 0.01}):
            sharp_conf = compute_bayesian_status(0.35).confidence
        assert sharp_conf > 0.99
        assert sharp_conf > default_conf

    def test_centers_override_moves_the_map_status(self):
        assert compute_bayesian_status(0.0).map_status == "D0"
        shifted = {"D0": 5.0, "D1": 6.0, "D2": 7.0, "D3": 8.0, "D4": 0.0}
        with override_thresholds({("bayesian_status", "centers"): shifted}):
            assert compute_bayesian_status(0.0).map_status == "D4"

    def test_credible_interval_tail_override_changes_the_interval(self):
        default_interval = compute_bayesian_status(0.35).confidence_interval
        with override_thresholds({("bayesian_status", "credible_interval_tail"): 0.5}):
            tight_interval = compute_bayesian_status(0.35).confidence_interval
        assert tight_interval != default_interval


class TestCrossDomainFamilyResolvesPerCall:
    def test_reliability_weights_override_changes_evidence_weights(self):
        results = [_domain_result("A", "D2", sufficient=True), _domain_result("B", "D1", sufficient=False)]
        default_weights = {w.domain: w.weight for w in compute_evidence_weights(results)}
        with override_thresholds(
            {
                ("cross_domain_fusion", "reliability_sufficient"): 0.5,
                ("cross_domain_fusion", "reliability_partial"): 0.5,
            }
        ):
            flat_weights = {w.domain: w.weight for w in compute_evidence_weights(results)}
        assert default_weights["A"] > default_weights["B"]
        assert flat_weights["A"] == flat_weights["B"]

    def test_contradiction_gap_override_flags_smaller_gaps(self):
        results = [_domain_result("A", "D2"), _domain_result("B", "D1")]  # severity gap 1
        assert detect_cross_domain_contradictions(results) == []
        with override_thresholds({("cross_domain_fusion", "contradiction_gap"): 1}):
            assert len(detect_cross_domain_contradictions(results)) == 1

    def test_confidence_discount_override_lowers_fusion_confidence(self):
        results = [_domain_result("A", "D4"), _domain_result("B", "D1")]  # gap 3 -> contradiction
        default_conf = fuse_domain_evidence(results).confidence
        with override_thresholds(
            {
                ("cross_domain_fusion", "confidence_discount_per_gap"): 0.3,
                ("cross_domain_fusion", "confidence_floor"): 0.0,
            }
        ):
            discounted_conf = fuse_domain_evidence(results).confidence
        assert discounted_conf < default_conf


class TestSkillFamilyResolvesPerCall:
    def test_skill_score_weights_override_changes_the_composite(self):
        reviews = [{"status_match": True, "domain_match_ratio": 0.0}]
        assert compute_skill_metrics(reviews)["skill_score"] == 0.6  # default detection weight
        with override_thresholds(
            {
                ("skill_validation_metrics", "detection_weight"): 0.2,
                ("skill_validation_metrics", "domain_match_weight"): 0.8,
            }
        ):
            assert compute_skill_metrics(reviews)["skill_score"] == 0.2


class TestReplayEvidenceFamilyResolvesPerCall:
    def test_evidence_weights_override_changes_the_score(self):
        kwargs = dict(
            status_match=True,
            domain_match_ratio=0.0,
            replay_source_coverage_ratio=0.0,
            replay_provenance_completeness_ratio=0.0,
        )
        assert _replay_evidence_score(**kwargs) == 0.4  # default status weight
        with override_thresholds({("skill_validation_metrics", "evidence_status_match_weight"): 0.9}):
            assert _replay_evidence_score(**kwargs) == 0.9

    def test_tier_override_reclassifies_the_same_score(self):
        assert _replay_evidence_tier(0.6) == "partial_replay_evidence"
        with override_thresholds({("skill_validation_metrics", "tier_partial"): 0.7}):
            assert _replay_evidence_tier(0.6) == "weak_replay_evidence"


class TestRegressionFamilyResolvesPerCall:
    def test_score_drop_override_changes_regression_detection(self):
        baseline = SimpleNamespace(score=1.0, status="D2")
        current = SimpleNamespace(score=0.95, status="D2")  # drop of 0.05
        assert _compare_scores("UKR", "B", baseline, current).regression_detected is False
        with override_thresholds({("skill_validation_metrics", "regression_score_drop"): 0.01}):
            assert _compare_scores("UKR", "B", baseline, current).regression_detected is True


class TestAmplificationFamilyResolvesPerCall:
    def test_amplification_ratio_override_changes_detection(self):
        observations = [
            SpreadObservation("SRC-1", "sig", 0.0, 10.0),
            SpreadObservation("SRC-2", "sig", 1.0, 13.0),  # factor 1.3
        ]
        assert detect_amplification(observations) == []
        with override_thresholds({("information_epidemiology", "amplification_ratio"): 1.2}):
            assert len(detect_amplification(observations)) == 1
