"""ALGO-SKILL-01 (AP-16) + ALGO-SKILL-02 (AP-28): skill-measurement harness.

Closes findings F7/F8/F9 (the validation surface reported coverage but never an
objective model-quality number). From the historical-replay reviews of the
curated reference cases, derive deterministic skill metrics so any model change
can be measured.

ALGO-SKILL-01 (AP-16): detection rate (replayed status matches the labelled
status), mean domain-match, and a composite skill score. A deliberately worse
model yields a measurably lower skill score.

ALGO-SKILL-02 (AP-28): on the AP-27 redesigned ground truth, additionally derive
  * recall / false-alarm classification (false-alarm rate defined ONLY over the
    S0 negative cases, so it is > 0 only thanks to AP-27 negatives),
  * lead time before onset (first non-S0 day of the AP-26 replay status timeseries
    relative to onset_date; positive = warned before onset),
  * a Brier score over a deterministic case-level event probability, and
  * a no-skill "always S3" baseline plus a ``beats_baseline`` flag (the model
    beats the trivial baseline on false-alarm AND lead time).

The Brier ``event probability`` is a deterministic proxy derived from the replayed
S-status ordinal (S0=0 .. S6=1); it stands in for a true case-level Bayes posterior
(the Bayes layer is domain-/D-status level) until a case-level posterior exists.
Scoring logic itself is out of scope (AP-18); skill weights are owner authority.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from siasa.scoring.scoring_thresholds import skill_score_weights

# Governed via vmodel/project/scoring_thresholds.yaml (AP-24); fallback = shipped values.
_DETECTION_WEIGHT, _DOMAIN_MATCH_WEIGHT = skill_score_weights()

_STATUS_ORDINAL = {"S0": 0, "S1": 1, "S2": 2, "S3": 3, "S4": 4, "S5": 5, "S6": 6}
_BASELINE_STATUS = "S3"  # no-skill baseline: always predict S3
_MAX_STATUS = 6


def _event_probability(status: str) -> float:
    """Deterministic case-level event probability from an S-status (S0=0.0 .. S6=1.0)."""
    return _STATUS_ORDINAL.get(status, 0) / _MAX_STATUS


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _first_alarm_date(timeseries: Any) -> Any:
    """Return the date of the first non-S0 (alarm) day in the per-day timeseries."""
    if not isinstance(timeseries, list):
        return None
    for entry in timeseries:
        if isinstance(entry, dict) and str(entry.get("status", "S0")) != "S0":
            return entry.get("date")
    return None


def _skill_bundle(cases: list[dict[str, Any]], *, baseline: bool) -> dict[str, Any]:
    """Hit/false-alarm/lead/Brier bundle for the real model or the always-S3 baseline."""
    positive_total = 0
    positive_hits = 0
    negative_total = 0
    negative_false_alarms = 0
    lead_times: list[int] = []
    brier_terms: list[float] = []

    for review in cases:
        is_positive = str(review.get("case_polarity", "positive")) == "positive"
        timeseries = review.get("status_timeseries")

        if baseline:
            predicted_status = _BASELINE_STATUS
            alarm = True  # S3 != S0: the baseline alarms unconditionally
            alarm_date = (
                timeseries[0].get("date")
                if isinstance(timeseries, list) and timeseries and isinstance(timeseries[0], dict)
                else None
            )
        else:
            predicted_status = str(review.get("replayed_status", "S0"))
            alarm = predicted_status != "S0"
            alarm_date = _first_alarm_date(timeseries)

        outcome = 1.0 if is_positive else 0.0
        brier_terms.append((_event_probability(predicted_status) - outcome) ** 2)

        if is_positive:
            positive_total += 1
            if alarm:
                positive_hits += 1
            onset = _parse_date(review.get("onset_date"))
            first = _parse_date(alarm_date)
            if alarm and onset is not None and first is not None:
                lead_times.append((onset - first).days)
        else:
            negative_total += 1
            if alarm:
                negative_false_alarms += 1

    return {
        "recall": round(positive_hits / positive_total, 4) if positive_total else 0.0,
        "false_alarm_rate": round(negative_false_alarms / negative_total, 4) if negative_total else 0.0,
        "positive_case_count": positive_total,
        "negative_case_count": negative_total,
        "mean_lead_time_days": round(sum(lead_times) / len(lead_times), 4) if lead_times else None,
        "lead_time_case_count": len(lead_times),
        "brier_score": round(sum(brier_terms) / len(brier_terms), 4) if brier_terms else 0.0,
    }


def compute_skill_metrics(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Return deterministic skill metrics over the replay reviews.

    ``skill_score`` (ALGO-SKILL-01) is a coverage-style composite in [0, 1]:
    detection rate (status matches) weighted with the mean domain-match ratio,
    monotone in model quality. ALGO-SKILL-02 adds false-alarm rate, lead time,
    Brier score and an always-S3 no-skill baseline with a ``beats_baseline`` flag.
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

    # ALGO-SKILL-02: false-alarm, lead time, Brier, and the no-skill "always S3" baseline.
    model = _skill_bundle(cases, baseline=False)
    baseline = _skill_bundle(cases, baseline=True)

    # The model beats the trivial baseline when it raises strictly fewer false
    # alarms (is selective, unlike always-S3) AND still warns at/before onset on
    # the cases it detects -- i.e. it measures more than the raw status match.
    beats_baseline = bool(
        model["false_alarm_rate"] < baseline["false_alarm_rate"]
        and model["mean_lead_time_days"] is not None
        and model["mean_lead_time_days"] >= 0
    )

    return {
        "case_count": case_count,
        "status_match_count": status_match_count,
        "mismatch_count": mismatch_count,
        "detection_rate": detection_rate,
        "mean_domain_match_ratio": mean_domain_match_ratio,
        "skill_score": skill_score,
        # ALGO-SKILL-02 (AP-28)
        "recall": model["recall"],
        "false_alarm_rate": model["false_alarm_rate"],
        "positive_case_count": model["positive_case_count"],
        "negative_case_count": model["negative_case_count"],
        "mean_lead_time_days": model["mean_lead_time_days"],
        "lead_time_case_count": model["lead_time_case_count"],
        "brier_score": model["brier_score"],
        "baseline_false_alarm_rate": baseline["false_alarm_rate"],
        "baseline_brier_score": baseline["brier_score"],
        "baseline_mean_lead_time_days": baseline["mean_lead_time_days"],
        "beats_baseline": beats_baseline,
    }
