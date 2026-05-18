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
    expected_signal_pattern: str
    reference_sources: list[str]
    validation_goal: str
    known_limitations: list[str]
    validation_metrics: list[str]

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
        "reference_sources": list(validation_case.reference_sources),
        "validation_goal": validation_case.validation_goal,
        "validation_metrics": list(validation_case.validation_metrics),
        "known_limitations": list(validation_case.known_limitations),
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
            expected_signal_pattern=str(record.get("expected_signal_pattern", "")),
            reference_sources=[str(item) for item in record.get("reference_sources", [])],
            validation_goal=str(record.get("validation_goal", "")),
            known_limitations=[str(item) for item in record.get("known_limitations", [])],
            validation_metrics=[str(item) for item in record.get("validation_metrics", [])],
        )
        for record in case_records
        if isinstance(record, dict)
    ]


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
