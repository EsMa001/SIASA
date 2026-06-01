"""SIASA cross-domain evidence fusion.

Detects contradictions between domains (e.g., Domain A signals conflict
escalation while Domain D shows economic stability), applies explicit
evidence weighting, and produces a fused assessment with contradiction
flags and confidence-weighted domain contributions.

Key APIs:
- ``detect_cross_domain_contradictions(domain_results)`` — find A vs D etc.
- ``compute_evidence_weights(domain_results)`` — weight by data quality
- ``fuse_domain_evidence(domain_results)`` — weighted fusion with contradiction flags

Requirement trace: AP-F22, StR-045..050 (Evidenzfusion und Cross-Domain-Kontrastierung)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from siasa.scoring.domain_status import DomainStatusResult


# Domain pairs that should be checked for contradictions
_CONTRADICTION_PAIRS = [
    ("A", "D"),  # Political conflict (A) vs Economic stability (D)
    ("A", "B"),  # Political conflict (A) vs Security (B) — usually aligned but divergence is notable
    ("B", "D"),  # Security (B) vs Economic (D) — security crisis with economic stability is contradictory
    ("C", "B"),  # Physical disaster (C) vs Security (B) — disaster without security impact is notable
]

# Status levels ordered from calm to critical
_STATUS_SEVERITY = {"D0": -1, "D1": 0, "D2": 1, "D3": 2, "D4": 3, "D5": 4}


@dataclass(frozen=True)
class ContradictionResult:
    """A detected contradiction between two domains."""
    domain_a: str
    domain_b: str
    status_a: str
    status_b: str
    severity_gap: int
    description: str


@dataclass(frozen=True)
class EvidenceWeight:
    """Weight assigned to a domain's evidence."""
    domain: str
    weight: float
    basis: str  # "sufficient", "partial", "insufficient"


@dataclass(frozen=True)
class FusionResult:
    """Result of cross-domain evidence fusion."""
    fused_score: float
    confidence: float
    contradictions: list[ContradictionResult]
    weights: list[EvidenceWeight]
    contributing_domains: list[str]
    contradiction_detected: bool
    fusion_method: str


def detect_cross_domain_contradictions(
    domain_results: list[DomainStatusResult],
) -> list[ContradictionResult]:
    """Detect contradictions between domain pairs.

    A contradiction exists when two related domains show significantly
    divergent status levels (severity gap >= 2).
    """
    result_by_domain = {r.domain: r for r in domain_results}
    contradictions: list[ContradictionResult] = []

    for dom_a, dom_b in _CONTRADICTION_PAIRS:
        res_a = result_by_domain.get(dom_a)
        res_b = result_by_domain.get(dom_b)
        if res_a is None or res_b is None:
            continue

        sev_a = _STATUS_SEVERITY.get(res_a.status, -1)
        sev_b = _STATUS_SEVERITY.get(res_b.status, -1)

        # Skip if either has insufficient data
        if sev_a < 0 or sev_b < 0:
            continue

        gap = abs(sev_a - sev_b)
        if gap >= 2:
            higher = dom_a if sev_a > sev_b else dom_b
            lower = dom_b if sev_a > sev_b else dom_a
            contradictions.append(ContradictionResult(
                domain_a=dom_a,
                domain_b=dom_b,
                status_a=res_a.status,
                status_b=res_b.status,
                severity_gap=gap,
                description=(
                    f"Domain {higher} ({result_by_domain[higher].status}) "
                    f"significantly elevated vs Domain {lower} "
                    f"({result_by_domain[lower].status}) — "
                    f"severity gap {gap}"
                ),
            ))

    return contradictions


def compute_evidence_weights(
    domain_results: list[DomainStatusResult],
) -> list[EvidenceWeight]:
    """Compute evidence weights based on data sufficiency.

    Domains with sufficient data get weight 1.0, partial gets 0.6,
    insufficient gets 0.2. Weights are normalized to sum to 1.0.
    """
    raw_weights: list[tuple[str, float, str]] = []

    for result in domain_results:
        if result.sufficiency.is_sufficient:
            raw_weights.append((result.domain, 1.0, "sufficient"))
        elif result.status == "D0":
            raw_weights.append((result.domain, 0.2, "insufficient"))
        else:
            raw_weights.append((result.domain, 0.6, "partial"))

    total = sum(w for _, w, _ in raw_weights)
    if total <= 0:
        total = 1.0

    return [
        EvidenceWeight(
            domain=domain,
            weight=round(raw / total, 4),
            basis=basis,
        )
        for domain, raw, basis in raw_weights
    ]


def fuse_domain_evidence(
    domain_results: list[DomainStatusResult],
) -> FusionResult:
    """Fuse evidence from multiple domains into a weighted assessment.

    Combines anomaly scores using data-quality weights, detects
    contradictions, and computes a fusion confidence score.
    """
    if not domain_results:
        return FusionResult(
            fused_score=0.0,
            confidence=0.0,
            contradictions=[],
            weights=[],
            contributing_domains=[],
            contradiction_detected=False,
            fusion_method="empty",
        )

    contradictions = detect_cross_domain_contradictions(domain_results)
    weights = compute_evidence_weights(domain_results)
    weight_lookup = {w.domain: w.weight for w in weights}

    # Weighted fusion of anomaly scores
    weighted_sum = 0.0
    total_weight = 0.0
    for result in domain_results:
        w = weight_lookup.get(result.domain, 0.0)
        weighted_sum += result.anomaly_score * w
        total_weight += w

    fused_score = round(weighted_sum / max(total_weight, 1e-9), 4)

    # Confidence based on data completeness and contradiction presence
    sufficient_count = sum(1 for w in weights if w.basis == "sufficient")
    confidence = round(sufficient_count / max(len(weights), 1), 4)
    if contradictions:
        # Reduce confidence when contradictions exist
        max_gap = max(c.severity_gap for c in contradictions)
        confidence = round(confidence * max(0.3, 1.0 - 0.15 * max_gap), 4)

    return FusionResult(
        fused_score=fused_score,
        confidence=confidence,
        contradictions=contradictions,
        weights=weights,
        contributing_domains=[r.domain for r in domain_results],
        contradiction_detected=len(contradictions) > 0,
        fusion_method="weighted_sufficiency",
    )
