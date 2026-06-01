"""Tests for cross-domain evidence fusion."""

from __future__ import annotations

import pytest

from siasa.scoring.cross_domain_fusion import (
    ContradictionResult,
    EvidenceWeight,
    FusionResult,
    compute_evidence_weights,
    detect_cross_domain_contradictions,
    fuse_domain_evidence,
)
from siasa.scoring.data_sufficiency import DataSufficiencyResult
from siasa.scoring.domain_status import DomainStatusResult


def _make_result(
    domain: str,
    status: str,
    anomaly_score: float = 0.5,
    is_sufficient: bool = True,
) -> DomainStatusResult:
    sufficiency = DataSufficiencyResult(
        is_sufficient=is_sufficient,
        coverage=1.0 if is_sufficient else 0.0,
        freshness_hours=24.0 if is_sufficient else None,
        reasons=[] if is_sufficient else ["no data"],
    )
    return DomainStatusResult(
        domain=domain,
        status=status,
        anomaly_score=anomaly_score,
        drivers=["anomaly_score"],
        uncertainty_indicators=[],
        rule_references=["SwR-021"],
        sufficiency=sufficiency,
    )


class TestDetectContradictions:
    """Tests for contradiction detection between domain pairs."""

    def test_no_contradiction_when_similar(self):
        results = [
            _make_result("A", "D2", 0.35),
            _make_result("D", "D2", 0.30),
        ]
        contradictions = detect_cross_domain_contradictions(results)
        assert len(contradictions) == 0

    def test_contradiction_a_vs_d_large_gap(self):
        results = [
            _make_result("A", "D4", 1.2),  # Critical political
            _make_result("D", "D1", 0.1),  # Calm economic
        ]
        contradictions = detect_cross_domain_contradictions(results)
        assert len(contradictions) == 1
        assert contradictions[0].domain_a == "A"
        assert contradictions[0].domain_b == "D"
        assert contradictions[0].severity_gap == 3

    def test_contradiction_b_vs_d(self):
        results = [
            _make_result("B", "D3", 0.7),  # Security elevated
            _make_result("D", "D1", 0.1),  # Economic calm
        ]
        contradictions = detect_cross_domain_contradictions(results)
        assert len(contradictions) == 1
        assert contradictions[0].severity_gap == 2

    def test_no_contradiction_with_insufficient_data(self):
        results = [
            _make_result("A", "D0", 0.0, is_sufficient=False),
            _make_result("D", "D4", 1.5),
        ]
        contradictions = detect_cross_domain_contradictions(results)
        assert len(contradictions) == 0

    def test_multiple_contradictions(self):
        results = [
            _make_result("A", "D4", 1.2),
            _make_result("B", "D4", 1.0),
            _make_result("D", "D1", 0.1),
        ]
        contradictions = detect_cross_domain_contradictions(results)
        # A vs D and B vs D should both fire
        pairs = {(c.domain_a, c.domain_b) for c in contradictions}
        assert ("A", "D") in pairs
        assert ("B", "D") in pairs

    def test_gap_threshold_exactly_2(self):
        results = [
            _make_result("A", "D3", 0.7),  # sev=2
            _make_result("D", "D1", 0.1),  # sev=0
        ]
        contradictions = detect_cross_domain_contradictions(results)
        assert len(contradictions) == 1
        assert contradictions[0].severity_gap == 2

    def test_gap_threshold_below_2_no_contradiction(self):
        results = [
            _make_result("A", "D2", 0.35),  # sev=1
            _make_result("D", "D1", 0.1),   # sev=0
        ]
        contradictions = detect_cross_domain_contradictions(results)
        assert len(contradictions) == 0


class TestComputeEvidenceWeights:
    """Tests for evidence weight computation."""

    def test_all_sufficient(self):
        results = [
            _make_result("A", "D2", 0.3),
            _make_result("B", "D2", 0.4),
            _make_result("D", "D1", 0.1),
        ]
        weights = compute_evidence_weights(results)
        assert len(weights) == 3
        assert all(w.basis == "sufficient" for w in weights)
        total = sum(w.weight for w in weights)
        assert abs(total - 1.0) < 0.01

    def test_mixed_sufficiency(self):
        results = [
            _make_result("A", "D2", 0.3, is_sufficient=True),
            _make_result("B", "D0", 0.0, is_sufficient=False),
        ]
        weights = compute_evidence_weights(results)
        weight_a = next(w for w in weights if w.domain == "A")
        weight_b = next(w for w in weights if w.domain == "B")
        assert weight_a.weight > weight_b.weight
        assert weight_a.basis == "sufficient"
        assert weight_b.basis == "insufficient"

    def test_weights_normalize_to_one(self):
        results = [
            _make_result("A", "D2", 0.3),
            _make_result("B", "D3", 0.6),
            _make_result("C", "D1", 0.1),
            _make_result("D", "D2", 0.3),
            _make_result("E", "D1", 0.1),
        ]
        weights = compute_evidence_weights(results)
        total = sum(w.weight for w in weights)
        assert abs(total - 1.0) < 0.01


class TestFuseDomainEvidence:
    """Tests for the full fusion pipeline."""

    def test_basic_fusion_no_contradictions(self):
        results = [
            _make_result("A", "D2", 0.35),
            _make_result("B", "D2", 0.30),
            _make_result("D", "D2", 0.25),
        ]
        fusion = fuse_domain_evidence(results)

        assert isinstance(fusion, FusionResult)
        assert fusion.fusion_method == "weighted_sufficiency"
        assert not fusion.contradiction_detected
        assert len(fusion.contradictions) == 0
        assert fusion.confidence == 1.0  # All sufficient
        assert 0.25 <= fusion.fused_score <= 0.35

    def test_fusion_with_contradictions(self):
        results = [
            _make_result("A", "D4", 1.2),
            _make_result("D", "D1", 0.1),
        ]
        fusion = fuse_domain_evidence(results)

        assert fusion.contradiction_detected
        assert len(fusion.contradictions) == 1
        assert fusion.confidence < 1.0  # Reduced by contradiction

    def test_fusion_confidence_reduced_by_insufficient_data(self):
        results = [
            _make_result("A", "D2", 0.3, is_sufficient=True),
            _make_result("B", "D0", 0.0, is_sufficient=False),
        ]
        fusion = fuse_domain_evidence(results)

        assert fusion.confidence < 1.0

    def test_empty_input(self):
        fusion = fuse_domain_evidence([])

        assert fusion.fused_score == 0.0
        assert fusion.confidence == 0.0
        assert fusion.fusion_method == "empty"

    def test_contributing_domains_listed(self):
        results = [
            _make_result("A", "D2", 0.3),
            _make_result("B", "D3", 0.6),
            _make_result("C", "D1", 0.1),
        ]
        fusion = fuse_domain_evidence(results)

        assert set(fusion.contributing_domains) == {"A", "B", "C"}

    def test_weights_in_fusion_result(self):
        results = [
            _make_result("A", "D2", 0.3),
            _make_result("D", "D2", 0.3),
        ]
        fusion = fuse_domain_evidence(results)

        assert len(fusion.weights) == 2
        assert all(isinstance(w, EvidenceWeight) for w in fusion.weights)
