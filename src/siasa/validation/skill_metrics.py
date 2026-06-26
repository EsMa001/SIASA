"""ALGO-SKILL-01 (AP-16): skill-measurement harness over reference-case replays.

Closes findings F7/F8/F9 (the validation surface reported coverage but never an
objective model-quality number). From the historical-replay reviews of the
curated reference cases, derive deterministic skill metrics so any model change
can be measured: detection rate (replayed status matches the labelled status),
mean domain-match, and a composite skill score. A deliberately worse model
yields a measurably lower skill score.

Scope boundary: this is the harness scaffold. The metrics that require AP-27's
redesigned ground truth — false-alarm rate (needs S0 negatives), lead time
before onset, and Brier score on the Bayes posterior — are added by AP-28
(ALGO-SKILL-02). Scoring logic itself is out of scope (AP-18). Weights are
project-owner authority.
"""
from __future__ import annotations

from typing import Any

from siasa.scoring.scoring_thresholds import skill_score_weights

# Governed via vmodel/project/scoring_thresholds.yaml (AP-24); fallback = shipped values.
_DETECTION_WEIGHT, _DOMAIN_MATCH_WEIGHT = skill_score_weights()


def compute_skill_metrics(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Return deterministic skill metrics over the replay reviews.

    ``skill_score`` is a coverage-style composite in [0, 1]: detection rate
    (status matches) weighted with the mean domain-match ratio. It is monotone
    in model quality — more mismatches or weaker domain match lower it.
    """
    cases = [review for review in reviews if isinstance(review, dict)]
    case_count = len(cases)
    status_match_count = sum(1 for review in cases if review.get("status_match") is True)
    mismatch_count = case_count - status_match_count
    detection_rate = round(status_match_count / case_count, 4) if case_count else 0.0

    domain_match_ratios = [
        float(review["domain_match_ratio"])
        for review in cases
        if isinstance(review.get("domain_match_ratio"), (int, float))
    ]
    mean_domain_match_ratio = (
        round(sum(domain_match_ratios) / len(domain_match_ratios), 4) if domain_match_ratios else 0.0
    )

    skill_score = round(
        _DETECTION_WEIGHT * detection_rate + _DOMAIN_MATCH_WEIGHT * mean_domain_match_ratio,
        4,
    )
    return {
        "case_count": case_count,
        "status_match_count": status_match_count,
        "mismatch_count": mismatch_count,
        "detection_rate": detection_rate,
        "mean_domain_match_ratio": mean_domain_match_ratio,
        "skill_score": skill_score,
    }
