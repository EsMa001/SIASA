"""Unit tests for ALGO-SKILL-01 (AP-16) + ALGO-SKILL-02 (AP-28): the skill harness.

Verifies SwR-039 (detection rate, domain match, composite skill score) and the
AP-28 extension SwR-091..094: false-alarm rate on S0 negatives, lead time before
onset, Brier score, and the always-S3 no-skill baseline with beats_baseline.
"""
from __future__ import annotations

from siasa.validation.skill_metrics import compute_skill_metrics


def _review(status_match: bool, domain_match_ratio: float = 1.0) -> dict:
    return {"status_match": status_match, "domain_match_ratio": domain_match_ratio}


def _case(
    polarity: str,
    replayed_status: str,
    *,
    status_match: bool = True,
    domain_match_ratio: float = 1.0,
    onset_date: str | None = None,
    timeseries: list[dict] | None = None,
) -> dict:
    return {
        "case_polarity": polarity,
        "replayed_status": replayed_status,
        "status_match": status_match,
        "domain_match_ratio": domain_match_ratio,
        "onset_date": onset_date,
        "status_timeseries": timeseries or [],
    }


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

    html_out = _render_validation_kpi_grid(
        {}, {}, {}, "replay_match", {"skill_score": 0.83, "false_alarm_rate": 0.5, "beats_baseline": True}
    )
    assert "Skill Score" in html_out
    assert "0.83" in html_out
    assert "False-Alarm Rate" in html_out
    assert "0.5" in html_out


# --- ALGO-SKILL-02 (AP-28): false-alarm, lead time, Brier, no-skill baseline ---


def test_false_alarm_rate_is_defined_only_on_s0_negatives():
    # SwR-091: false-alarm rate counts only the S0 negative cases.
    reviews = [
        _case("positive", "S3"),  # positive alarm -> hit, not a false alarm
        _case("negative", "S2"),  # negative alarm -> false alarm
        _case("negative", "S0"),  # negative quiet -> true negative
    ]
    metrics = compute_skill_metrics(reviews)
    assert metrics["positive_case_count"] == 1
    assert metrics["negative_case_count"] == 2
    assert metrics["false_alarm_rate"] == 0.5
    assert metrics["recall"] == 1.0


def test_false_alarm_rate_is_zero_without_negatives():
    # acceptance 3: only AP-27 negatives make the false-alarm rate measurable.
    metrics = compute_skill_metrics([_case("positive", "S3"), _case("positive", "S0")])
    assert metrics["negative_case_count"] == 0
    assert metrics["false_alarm_rate"] == 0.0


def test_lead_time_before_onset_from_timeseries():
    # SwR-092: lead time = onset_date - first non-S0 day of the replay timeseries.
    timeseries = [
        {"date": "2024-01-10", "status": "S0", "confidence": 0.9},
        {"date": "2024-01-12", "status": "S2", "confidence": 0.9},
        {"date": "2024-01-15", "status": "S3", "confidence": 0.9},
    ]
    metrics = compute_skill_metrics([_case("positive", "S3", onset_date="2024-01-20", timeseries=timeseries)])
    assert metrics["lead_time_case_count"] == 1
    assert metrics["mean_lead_time_days"] == 8.0


def test_brier_score_uses_status_event_probability():
    # SwR-092: perfect calibration -> Brier 0; fully wrong -> Brier 1.
    assert compute_skill_metrics([_case("positive", "S6"), _case("negative", "S0")])["brier_score"] == 0.0
    assert compute_skill_metrics([_case("positive", "S0")])["brier_score"] == 1.0


def test_selective_model_beats_always_s3_baseline():
    # SwR-093: a selective model (quiet on the negative) beats the always-S3 baseline.
    timeseries = [{"date": "2024-01-05", "status": "S2", "confidence": 0.9}]
    reviews = [
        _case("positive", "S3", onset_date="2024-01-10", timeseries=timeseries),
        _case("negative", "S0"),
    ]
    metrics = compute_skill_metrics(reviews)
    assert metrics["false_alarm_rate"] == 0.0
    assert metrics["baseline_false_alarm_rate"] == 1.0
    assert metrics["mean_lead_time_days"] == 5.0
    assert metrics["beats_baseline"] is True


def test_degraded_model_does_not_beat_baseline_and_lowers_skill():
    # acceptance 1+2: a degraded model lowers the skill score and stops beating the baseline.
    timeseries = [{"date": "2024-01-05", "status": "S2", "confidence": 0.9}]
    good = [
        _case("positive", "S3", status_match=True, onset_date="2024-01-10", timeseries=timeseries),
        _case("negative", "S0", status_match=True),
    ]
    degraded = [
        _case("positive", "S0", status_match=False, onset_date="2024-01-10",
              timeseries=[{"date": "2024-01-05", "status": "S0", "confidence": 0.0}]),
        _case("negative", "S4", status_match=False),
    ]
    good_metrics = compute_skill_metrics(good)
    degraded_metrics = compute_skill_metrics(degraded)
    assert degraded_metrics["skill_score"] < good_metrics["skill_score"]
    assert good_metrics["beats_baseline"] is True
    assert degraded_metrics["beats_baseline"] is False


def test_extended_metrics_are_deterministic_and_json_serializable():
    # SwR-094: deterministic artifact serialization of the extended metrics.
    import json

    timeseries = [{"date": "2024-01-05", "status": "S2", "confidence": 0.9}]
    reviews = [_case("positive", "S3", onset_date="2024-01-10", timeseries=timeseries), _case("negative", "S0")]
    metrics = compute_skill_metrics(reviews)
    assert metrics == compute_skill_metrics(reviews)
    for key in ("recall", "false_alarm_rate", "mean_lead_time_days", "brier_score",
                "beats_baseline", "baseline_false_alarm_rate"):
        assert key in metrics
    json.dumps(metrics, sort_keys=True)

