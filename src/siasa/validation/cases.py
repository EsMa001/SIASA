from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ValidationCase:
    case_id: str
    country_id: str
    case_name: str
    case_type: str
    time_start: str
    time_end: str
    expected_domains: list[str]
    expected_status: str
    expected_signal_pattern: str
    reference_sources: list[str]
    validation_goal: str
    known_limitations: list[str]
    validation_metrics: list[str]
    evidence_tier: str = "curated_public_source"
    historical_observed_domains: list[str] | None = None
    historical_observed_status: str | None = None
    # AP-27 ground-truth redesign (SwR-088), all optional / backward-compatible:
    onset_date: str | None = None
    expected_trajectory: list[str] | None = None
    dataset_split: str = "unassigned"
    case_polarity: str = "positive"

    def __post_init__(self) -> None:
        if not self.case_id or not self.country_id:
            raise ValueError("case_id and country_id are required")


def validation_case_to_dict(validation_case: ValidationCase) -> dict[str, object]:
    return {
        "case_id": validation_case.case_id,
        "country_id": validation_case.country_id,
        "case_name": validation_case.case_name,
        "case_type": validation_case.case_type,
        "time_range": {
            "start": validation_case.time_start,
            "end": validation_case.time_end,
        },
        "expected_domains": list(validation_case.expected_domains),
        "expected_status": validation_case.expected_status,
        "reference_sources": list(validation_case.reference_sources),
        "validation_goal": validation_case.validation_goal,
        "validation_metrics": list(validation_case.validation_metrics),
        "known_limitations": list(validation_case.known_limitations),
        "evidence_tier": validation_case.evidence_tier,
        "historical_observed_domains": list(validation_case.historical_observed_domains or []),
        "historical_observed_status": validation_case.historical_observed_status,
        "onset_date": validation_case.onset_date,
        "expected_trajectory": list(validation_case.expected_trajectory or []),
        "dataset_split": validation_case.dataset_split,
        "case_polarity": validation_case.case_polarity,
    }


def load_validation_case_library(path: Path) -> list[ValidationCase]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    case_records = data.get("validation_cases", [])
    if not isinstance(case_records, list):
        raise ValueError("validation_cases must be a list")
    return [
        ValidationCase(
            case_id=str(record["case_id"]),
            country_id=str(record["country_id"]),
            case_name=str(record["case_name"]),
            case_type=str(record["case_type"]),
            time_start=str(record["time_start"]),
            time_end=str(record["time_end"]),
            expected_domains=[str(item) for item in record.get("expected_domains", [])],
            expected_status=str(record.get("expected_status", "S0")),
            expected_signal_pattern=str(record.get("expected_signal_pattern", "")),
            reference_sources=[str(item) for item in record.get("reference_sources", [])],
            validation_goal=str(record.get("validation_goal", "")),
            known_limitations=[str(item) for item in record.get("known_limitations", [])],
            validation_metrics=[str(item) for item in record.get("validation_metrics", [])],
            evidence_tier=str(record.get("evidence_tier", "curated_public_source")),
            historical_observed_domains=[str(item) for item in record.get("historical_observed_domains", [])],
            historical_observed_status=(
                str(record.get("historical_observed_status"))
                if record.get("historical_observed_status") is not None
                else None
            ),
            onset_date=(str(record["onset_date"]) if record.get("onset_date") is not None else None),
            expected_trajectory=(
                [str(item) for item in record.get("expected_trajectory", [])]
                if record.get("expected_trajectory") is not None
                else None
            ),
            dataset_split=str(record.get("dataset_split", "unassigned")),
            case_polarity=str(record.get("case_polarity", "positive")),
        )
        for record in case_records
        if isinstance(record, dict)
    ]


_VALID_DATASET_SPLITS = {"tuning", "holdout", "unassigned"}
_VALID_CASE_POLARITIES = {"positive", "negative"}


def validate_reference_case_library(cases: list[ValidationCase]) -> dict[str, object]:
    """ALGO/validator for AP-27 (SwR-090): check ground-truth integrity.

    Surfaces the F15 defects explicitly rather than silently:
    - ``onset_date`` (where present) must lie within ``[time_start, time_end]``;
    - ``dataset_split`` / ``case_polarity`` must use governed values (so tuning and
      holdout sets stay disjoint and well-formed);
    - anti-circularity: a positive case whose ``historical_observed_status`` is
      mechanically identical to its ``expected_status`` is flagged (the circular
      label that makes a positive trivially "predictable").

    Structural problems (onset/split/polarity) drive ``is_valid``; circular labels
    and the negative/S0 counts are reported as quality signals for owner curation.
    Deterministic.
    """
    onset_out_of_window: list[str] = []
    invalid_split: list[str] = []
    invalid_polarity: list[str] = []
    circular_label_case_ids: list[str] = []
    for case in cases:
        if case.onset_date is not None and not (case.time_start <= case.onset_date <= case.time_end):
            onset_out_of_window.append(case.case_id)
        if case.dataset_split not in _VALID_DATASET_SPLITS:
            invalid_split.append(case.case_id)
        if case.case_polarity not in _VALID_CASE_POLARITIES:
            invalid_polarity.append(case.case_id)
        if (
            case.case_polarity == "positive"
            and case.historical_observed_status is not None
            and case.historical_observed_status == case.expected_status
        ):
            circular_label_case_ids.append(case.case_id)
    return {
        "case_count": len(cases),
        "negative_case_count": sum(1 for case in cases if case.case_polarity == "negative"),
        "s0_negative_count": sum(
            1 for case in cases if case.case_polarity == "negative" and case.expected_status == "S0"
        ),
        "dataset_splits_present": sorted({case.dataset_split for case in cases}),
        "onset_out_of_window": sorted(onset_out_of_window),
        "invalid_split": sorted(invalid_split),
        "invalid_polarity": sorted(invalid_polarity),
        "circular_label_case_ids": sorted(circular_label_case_ids),
        "is_valid": not (onset_out_of_window or invalid_split or invalid_polarity),
    }


def compare_expected_vs_observed(
    validation_case: ValidationCase,
    observed_domains: list[str],
    observed_status: str,
    expected_status: str,
) -> dict[str, object]:
    expected_domain_set = set(validation_case.expected_domains)
    observed_domain_set = set(observed_domains)
    match_count = len(expected_domain_set & observed_domain_set)
    domain_match_ratio = match_count / len(expected_domain_set) if expected_domain_set else 0.0
    return {
        "case_id": validation_case.case_id,
        "domain_match_ratio": domain_match_ratio,
        "status_match": observed_status == expected_status,
        "observed_domains": sorted(observed_domain_set),
        "expected_domains": sorted(expected_domain_set),
    }
