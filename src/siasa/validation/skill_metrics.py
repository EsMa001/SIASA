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
  * a no-skill "always S3" classification comparator.

SwR-114 (AP-34.8) replaced the reference used for the skill verdict: skill is now
measured against CLIMATOLOGY (the observed base rate, Brier = p(1-p)) via the
Brier Skill Score, because the always-S3 comparator alarms on every control by
construction and is trivially beatable. ``beats_baseline`` therefore requires
positive BSS **and** selectivity against always-S3 **and** at least one pre-onset
warning. Every binomial rate carries a 95% Wilson interval, absent exactly when
the rate is undefined.

SwR-113 (AP-34.6) governs what counts as an alarm; SwR-115 (AP-34.9) makes the
statuses S5 (contradictory) and S6 (data insufficient) abstentions rather than
severity levels — see ``_ABSTENTION_STATUSES``.

The Brier ``event probability`` is a deterministic proxy derived from the ordinal
part of the S-status scale (S0=0.0 .. S4=1.0); it stands in for a true case-level
Bayes posterior (the Bayes layer is domain-/D-status level) until a case-level
posterior exists.
Scoring logic itself is out of scope (AP-18); skill weights are owner authority.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any

from siasa.scoring.scoring_thresholds import skill_alarm_minimum_status, skill_score_weights

# Governed via vmodel/project/scoring_thresholds.yaml (AP-24); resolved PER CALL
# (SwR-109) so overrides and sensitivity sweeps reach this module.

# SwR-115: the S-scale is ordinal by severity ONLY up to S4. Per the governed
# glossary (vmodel/project/glossary.yaml) S5 means "contradictory / ambiguous
# pattern" and S6 means "data insufficient" — both are qualitative categories,
# not severity levels above S4. Treating them as ordinal made a data outage the
# single most confident conflict prediction the system can emit.
_SEVERITY_ORDINAL = {"S0": 0, "S1": 1, "S2": 2, "S3": 3, "S4": 4}
_MAX_SEVERITY = 4

#: Statuses that express *inability to assess*, not a degree of threat. They are
#: abstentions: excluded from recall, false-alarm rate and Brier, and counted
#: separately so the abstention is visible instead of silently scored.
_ABSTENTION_STATUSES = {"S5": "contradictory", "S6": "data_insufficient"}

_BASELINE_STATUS = "S3"  # trivial classification baseline: always predict S3

# SwR-114 (audit A-10): 95% two-sided normal quantile for Wilson score intervals.
_WILSON_Z = 1.959963984540054


def _wilson_interval(successes: int, total: int) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion; None when undefined.

    At the curated set's size (8 negatives) a naive 0/8 false-alarm rate carries
    a 95% Wilson upper bound of 0.3244 — reporting the point estimate alone would
    imply a precision the sample cannot support (audit A-10). Wilson is
    deliberately narrower than the Clopper-Pearson exact bound (0.3694) and the
    rule-of-three approximation (0.375); do not quote those figures for this
    function.
    """
    if total <= 0:
        return None
    proportion = successes / total
    denominator = 1.0 + _WILSON_Z**2 / total
    center = (proportion + _WILSON_Z**2 / (2 * total)) / denominator
    half_width = (_WILSON_Z / denominator) * math.sqrt(
        proportion * (1.0 - proportion) / total + _WILSON_Z**2 / (4 * total**2)
    )
    return (round(max(0.0, center - half_width), 4), round(min(1.0, center + half_width), 4))


def _is_abstention(status: str) -> bool:
    """SwR-115: S5/S6 state that the case cannot be assessed, not how severe it is."""
    return status in _ABSTENTION_STATUSES


def _event_probability(status: str) -> float:
    """Deterministic case-level event probability from an S-status (S0=0.0 .. S4=1.0).

    Only defined for the ordinal part of the scale; abstentions carry no
    probability statement and are filtered out before this is called (SwR-115).
    """
    return _SEVERITY_ORDINAL.get(status, 0) / _MAX_SEVERITY


def _is_alarm(status: str, alarm_minimum: str) -> bool:
    """SwR-113: an alarm is a status at or above the governed minimum.

    SwR-115: an abstention (S5/S6) is never an alarm — "I cannot assess this"
    must not be read as "I am warning about this".
    """
    if _is_abstention(status):
        return False
    return _SEVERITY_ORDINAL.get(status, 0) >= _SEVERITY_ORDINAL.get(alarm_minimum, 1)


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _first_alarm_date(timeseries: Any, alarm_minimum: str) -> Any:
    """Return the date of the first at-or-above-threshold day in the per-day timeseries."""
    if not isinstance(timeseries, list):
        return None
    for entry in timeseries:
        if isinstance(entry, dict) and _is_alarm(str(entry.get("status", "S0")), alarm_minimum):
            return entry.get("date")
    return None


def _skill_bundle(cases: list[dict[str, Any]], *, baseline: bool) -> dict[str, Any]:
    """Hit/false-alarm/lead/Brier bundle for the real model or the always-S3 baseline.

    SwR-113 (audit A-16): the alarm threshold is governed (``alarm_minimum_status``)
    instead of the implicit "!= S0"; lead time counts ONLY alarms raised at or
    before onset (a warning), while alarms first raised after onset are reported
    separately as nowcast detections, and positives never alarmed are reported as
    missed — nothing is silently dropped from the denominator.
    """
    alarm_minimum = skill_alarm_minimum_status()
    positive_present = 0
    negative_present = 0
    positive_total = 0
    positive_hits = 0
    negative_total = 0
    negative_false_alarms = 0
    lead_times: list[int] = []
    post_onset_detections = 0
    missed_positives = 0
    undatable_alarms = 0
    abstentions: dict[str, int] = {kind: 0 for kind in set(_ABSTENTION_STATUSES.values())}
    brier_terms: list[float] = []

    for review in cases:
        is_positive = str(review.get("case_polarity", "positive")) == "positive"
        timeseries = review.get("status_timeseries")

        # Presence counts cover EVERY case of that polarity, scored or not, so an
        # all-abstained set stays distinguishable from an empty one (SwR-115).
        if is_positive:
            positive_present += 1
        else:
            negative_present += 1

        # SwR-115: a case the model declined to assess (S5 contradictory, S6 data
        # insufficient) carries no forecast. Scoring it would credit a data
        # outage as a confident prediction — on a positive case that previously
        # produced recall 1.0 and Brier 0.0 for having seen nothing at all.
        if not baseline:
            declared_status = str(review.get("replayed_status", "S0"))
            if _is_abstention(declared_status):
                abstentions[_ABSTENTION_STATUSES[declared_status]] += 1
                continue

        if baseline:
            predicted_status = _BASELINE_STATUS
            alarm = _is_alarm(predicted_status, alarm_minimum)  # S3: alarms unconditionally
            alarm_date = (
                timeseries[0].get("date")
                if isinstance(timeseries, list) and timeseries and isinstance(timeseries[0], dict)
                else None
            )
        else:
            predicted_status = str(review.get("replayed_status", "S0"))
            alarm = _is_alarm(predicted_status, alarm_minimum)
            alarm_date = _first_alarm_date(timeseries, alarm_minimum)

        outcome = 1.0 if is_positive else 0.0
        brier_terms.append((_event_probability(predicted_status) - outcome) ** 2)

        if is_positive:
            positive_total += 1
            if alarm:
                positive_hits += 1
                onset = _parse_date(review.get("onset_date"))
                first = _parse_date(alarm_date)
                if onset is None or first is None:
                    undatable_alarms += 1
                elif first <= onset:
                    lead_times.append((onset - first).days)  # warning: >= 0 by construction
                else:
                    post_onset_detections += 1  # nowcast, not a warning
            else:
                missed_positives += 1
        else:
            negative_total += 1
            if alarm:
                negative_false_alarms += 1

    return {
        "recall": round(positive_hits / positive_total, 4) if positive_total else 0.0,
        "false_alarm_rate": round(negative_false_alarms / negative_total, 4) if negative_total else 0.0,
        # SwR-114: point estimates alone overstate precision at n=8; the interval
        # is None exactly when the rate is undefined (zero SCORED cases).
        "recall_ci_95": _wilson_interval(positive_hits, positive_total),
        "false_alarm_rate_ci_95": _wilson_interval(negative_false_alarms, negative_total),
        # Cases present in the set, regardless of whether the model assessed them.
        "positive_case_count": positive_present,
        "negative_case_count": negative_present,
        # SwR-115: the denominators the rates above actually used.
        "scored_positive_count": positive_total,
        "scored_negative_count": negative_total,
        "mean_lead_time_days": round(sum(lead_times) / len(lead_times), 4) if lead_times else None,
        "lead_time_case_count": len(lead_times),
        "pre_onset_alarm_count": len(lead_times),
        "post_onset_detection_count": post_onset_detections,
        "missed_positive_count": missed_positives,
        "undatable_alarm_count": undatable_alarms,
        "alarm_minimum_status": alarm_minimum,
        # SwR-115: abstentions are excluded from every rate above and reported
        # here, so a shrinking denominator is visible rather than flattering.
        "abstained_case_count": sum(abstentions.values()),
        "abstained_contradictory_count": abstentions["contradictory"],
        "abstained_data_insufficient_count": abstentions["data_insufficient"],
        "brier_score": round(sum(brier_terms) / len(brier_terms), 4) if brier_terms else 0.0,
    }


def _climatology_reference(cases: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    """Base rate and Brier score of the climatology forecast (SwR-114, audit A-09).

    Forecast verification defines skill relative to a *reference*, and the honest
    reference for a rare event is climatology: predict the observed base rate for
    every case. Its Brier score reduces exactly to ``p(1-p)``. The always-S3
    baseline is a straw man — it alarms on every control by construction and is
    therefore trivially beatable on false alarms; it is retained only as the
    classification comparator.

    NB on this curated set the base rate is ~0.5 by design (matched pairs), not
    the true prevalence of conflict onset. A climatology fitted to the real base
    rate is a materially harder reference and belongs with AP-30.4 data.

    SwR-115: callers pass the SCORED cases only. Comparing a model Brier taken
    over the assessed subset against a climatology taken over the full set
    (abstentions included) would compare different populations.
    """
    if not cases:
        return None, None
    positives = sum(1 for review in cases if str(review.get("case_polarity", "positive")) == "positive")
    base_rate = positives / len(cases)
    return round(base_rate, 4), round(base_rate * (1.0 - base_rate), 4)


def compute_skill_metrics(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Return deterministic skill metrics over the replay reviews.

    ``skill_score`` (ALGO-SKILL-01) is a coverage-style composite in [0, 1]:
    detection rate (status matches) weighted with the mean domain-match ratio,
    monotone in model quality. ALGO-SKILL-02 adds false-alarm rate, lead time and
    a Brier score; SwR-114 adds the climatology reference, the Brier Skill Score
    and Wilson intervals, and makes ``beats_baseline`` require positive BSS in
    addition to selectivity and a pre-onset warning.
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

    detection_weight, domain_match_weight = skill_score_weights()
    skill_score = round(
        detection_weight * detection_rate + domain_match_weight * mean_domain_match_ratio,
        4,
    )

    # ALGO-SKILL-02: false-alarm, lead time, Brier, and the no-skill "always S3" baseline.
    model = _skill_bundle(cases, baseline=False)
    baseline = _skill_bundle(cases, baseline=True)

    # SwR-114 (audit A-09): skill is measured against CLIMATOLOGY, not against
    # the always-S3 straw man. The Brier Skill Score is the standard form
    # BSS = 1 - B_model / B_reference; > 0 means the model carries information
    # the base rate alone does not.
    scored_cases = [
        review
        for review in cases
        if not _is_abstention(str(review.get("replayed_status", "S0")))
    ]
    climatology_base_rate, climatology_brier = _climatology_reference(scored_cases)
    brier_skill_score = (
        round(1.0 - model["brier_score"] / climatology_brier, 4)
        if climatology_brier
        else None
    )

    # The model beats the reference when it (1) carries probabilistic skill over
    # climatology, (2) is selective where the trivial always-S3 baseline is not,
    # and (3) actually warned before onset at least once -- an early-warning
    # system that only ever detects after the fact has not warned.
    beats_baseline = bool(
        brier_skill_score is not None
        and brier_skill_score > 0
        and model["false_alarm_rate"] < baseline["false_alarm_rate"]
        and model["mean_lead_time_days"] is not None
    )

    return {
        "case_count": case_count,
        "status_match_count": status_match_count,
        "mismatch_count": mismatch_count,
        "detection_rate": detection_rate,
        # SwR-114: detection_rate is a binomial proportion over case_count and
        # needs its interval as much as recall does. mean_domain_match_ratio is a
        # mean of continuous ratios, not a proportion, so a Wilson interval would
        # be the wrong estimator and is deliberately not fabricated for it.
        "detection_rate_ci_95": _wilson_interval(status_match_count, case_count),
        "mean_domain_match_ratio": mean_domain_match_ratio,
        "skill_score": skill_score,
        # ALGO-SKILL-02 (AP-28)
        "recall": model["recall"],
        "false_alarm_rate": model["false_alarm_rate"],
        # SwR-114: intervals sit next to every rate; None = rate undefined (n=0).
        "recall_ci_95": model["recall_ci_95"],
        "false_alarm_rate_ci_95": model["false_alarm_rate_ci_95"],
        "positive_case_count": model["positive_case_count"],
        "negative_case_count": model["negative_case_count"],
        "scored_positive_count": model["scored_positive_count"],
        "scored_negative_count": model["scored_negative_count"],
        "mean_lead_time_days": model["mean_lead_time_days"],
        "lead_time_case_count": model["lead_time_case_count"],
        # SwR-113: warning vs nowcast vs miss, nothing silently dropped.
        "pre_onset_alarm_count": model["pre_onset_alarm_count"],
        "post_onset_detection_count": model["post_onset_detection_count"],
        "missed_positive_count": model["missed_positive_count"],
        "undatable_alarm_count": model["undatable_alarm_count"],
        "alarm_minimum_status": model["alarm_minimum_status"],
        # SwR-115: S5/S6 are abstentions, not severity levels.
        "abstained_case_count": model["abstained_case_count"],
        "abstained_contradictory_count": model["abstained_contradictory_count"],
        "abstained_data_insufficient_count": model["abstained_data_insufficient_count"],
        "brier_score": model["brier_score"],
        "baseline_false_alarm_rate": baseline["false_alarm_rate"],
        "baseline_false_alarm_rate_ci_95": baseline["false_alarm_rate_ci_95"],
        "baseline_brier_score": baseline["brier_score"],
        "baseline_mean_lead_time_days": baseline["mean_lead_time_days"],
        # SwR-114 (audit A-09): the honest reference and the standard skill score.
        "climatology_base_rate": climatology_base_rate,
        "climatology_brier_score": climatology_brier,
        "brier_skill_score": brier_skill_score,
        "beats_baseline": beats_baseline,
    }
