"""Unit tests for ALGO-SKILL-01 (AP-16): the skill-measurement harness.

Verifies SwR-039: from the curated reference-case replay reviews, derive
objective skill metrics (detection rate, domain match, composite skill score)
so any model change can be measured. False-alarm / lead-time / Brier metrics
are AP-28 (they need AP-27's S0-negatives, onset dates and posterior).
"""
from __future__ import annotations

from siasa.validation.skill_metrics import compute_skill_metrics


def _review(status_match: bool, domain_match_ratio: float = 1.0) -> dict:
    return {"status_match": status_match, "domain_match_ratio": domain_match_ratio}


def test_metrics_over_at_least_four_cases_each_have_a_value():
    reviews = [_review(True), _review(True), _review(False), _review(True)]
    metrics = compute_skill_metrics(reviews)
    assert metrics["case_count"] == 4
    assert metrics["status_match_count"] == 3
    assert metrics["mismatch_count"] == 1
    assert metrics["detection_rate"] == 0.75
    assert metrics["mean_domain_match_ratio"] == 1.0
    assert 0.0 <= metrics["skill_score"] <= 1.0


def test_degraded_model_lowers_skill_score():
    good = [_review(True, 1.0) for _ in range(4)]
    degraded = [_review(False, 0.5) for _ in range(4)]
    assert compute_skill_metrics(degraded)["skill_score"] < compute_skill_metrics(good)["skill_score"]


def test_partial_degradation_lowers_skill_score_monotonically():
    strong = [_review(True, 1.0) for _ in range(4)]
    mixed = [_review(True, 1.0), _review(True, 1.0), _review(False, 0.5), _review(False, 0.5)]
    weak = [_review(False, 0.0) for _ in range(4)]
    scores = [compute_skill_metrics(r)["skill_score"] for r in (strong, mixed, weak)]
    assert scores[0] > scores[1] > scores[2]


def test_is_deterministic_and_rounded():
    reviews = [_review(True, 0.8), _review(False, 0.3), _review(True, 1.0), _review(True, 0.6)]
    first = compute_skill_metrics(reviews)
    assert first == compute_skill_metrics(reviews)
    assert first["skill_score"] == round(first["skill_score"], 4)


def test_empty_reviews_yield_zero():
    metrics = compute_skill_metrics([])
    assert metrics["case_count"] == 0
    assert metrics["status_match_count"] == 0
    assert metrics["detection_rate"] == 0.0
    assert metrics["skill_score"] == 0.0


def test_skill_score_is_visible_in_the_validation_kpi_grid():
    # acceptance 3: the skill metric is surfaced in the GUI validation view.
    from siasa.gui.local_app import _render_validation_kpi_grid

    html_out = _render_validation_kpi_grid({}, {}, {}, "replay_match", {"skill_score": 0.83})
    assert "Skill Score" in html_out
    assert "0.83" in html_out

