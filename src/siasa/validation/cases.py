from __future__ import annotations

from dataclasses import dataclass


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
