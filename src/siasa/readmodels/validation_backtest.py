from __future__ import annotations

from collections import Counter

from siasa.validation.cases import ValidationCase


def build_validation_portfolio_summary(validation_cases: list[dict[str, object]]) -> dict[str, object]:
    countries_covered = sorted(
        {
            str(case.get("country_id"))
            for case in validation_cases
            if isinstance(case, dict) and case.get("country_id")
        }
    )
    verdict_counts = Counter(
        str(case.get("review_verdict"))
        for case in validation_cases
        if isinstance(case, dict) and case.get("review_verdict")
    )
    cases_with_gaps = [
        {
            "case_id": str(case.get("case_id")),
            "country_id": str(case.get("country_id")),
            "review_verdict": str(case.get("review_verdict")),
        }
        for case in validation_cases
        if isinstance(case, dict) and str(case.get("review_verdict")) in {"support_check_with_gaps", "match_with_gaps", "mismatch"}
    ]
    return {
        "case_count": len([case for case in validation_cases if isinstance(case, dict)]),
        "countries_covered": countries_covered,
        "review_verdict_counts": dict(sorted(verdict_counts.items())),
        "cases_with_gaps": cases_with_gaps,
    }


def build_reference_case_library_summary(reference_case_library: list[ValidationCase | dict[str, object]]) -> dict[str, object]:
    normalized_cases: list[dict[str, object]] = []
    for item in reference_case_library:
        if isinstance(item, ValidationCase):
            normalized_cases.append(
                {
                    "case_id": item.case_id,
                    "country_id": item.country_id,
                    "case_type": item.case_type,
                    "time_start": item.time_start,
                    "time_end": item.time_end,
                }
            )
        elif isinstance(item, dict):
            time_range = item.get("time_range", {}) if isinstance(item.get("time_range", {}), dict) else {}
            normalized_cases.append(
                {
                    "case_id": item.get("case_id"),
                    "country_id": item.get("country_id"),
                    "case_type": item.get("case_type"),
                    "time_start": item.get("time_start", time_range.get("start")),
                    "time_end": item.get("time_end", time_range.get("end")),
                }
            )
    countries_covered = sorted(
        {
            str(case.get("country_id"))
            for case in normalized_cases
            if case.get("country_id")
        }
    )
    case_type_counts = Counter(
        str(case.get("case_type"))
        for case in normalized_cases
        if case.get("case_type")
    )
    time_starts = sorted(str(case.get("time_start")) for case in normalized_cases if case.get("time_start"))
    time_ends = sorted(str(case.get("time_end")) for case in normalized_cases if case.get("time_end"))
    return {
        "case_count": len(normalized_cases),
        "countries_covered": countries_covered,
        "case_type_counts": dict(sorted(case_type_counts.items())),
        "time_range": {
            "start": time_starts[0] if time_starts else "n/a",
            "end": time_ends[-1] if time_ends else "n/a",
        },
    }


def build_validation_backtest_read_model(
    validation_case: ValidationCase,
    comparison: dict[str, object],
    reprocessing_comparison: dict[str, object] | None = None,
    validation_cases: list[dict[str, object]] | None = None,
    portfolio_summary: dict[str, object] | None = None,
    reference_case_library: list[dict[str, object]] | None = None,
    reference_case_library_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    expected_domains = list(validation_case.expected_domains)
    observed_domains = list(comparison.get("observed_domains", []))
    missing_expected_domains = [domain for domain in expected_domains if domain not in observed_domains]
    unexpected_observed_domains = [domain for domain in observed_domains if domain not in expected_domains]
    status_match = comparison.get("status_match")
    if status_match is None:
        review_verdict = "support_check" if not missing_expected_domains and not unexpected_observed_domains else "support_check_with_gaps"
    elif status_match and not missing_expected_domains and not unexpected_observed_domains:
        review_verdict = "match"
    elif status_match:
        review_verdict = "match_with_gaps"
    else:
        review_verdict = "mismatch"
    read_model = {
        "case_id": validation_case.case_id,
        "country_id": validation_case.country_id,
        "case_name": validation_case.case_name,
        "case_type": validation_case.case_type,
        "time_range": {
            "start": validation_case.time_start,
            "end": validation_case.time_end,
        },
        "expected_domains": expected_domains,
        "observed_domains": observed_domains,
        "domain_match_ratio": comparison.get("domain_match_ratio"),
        "status_match": status_match,
        "review_verdict": review_verdict,
        "missing_expected_domains": missing_expected_domains,
        "unexpected_observed_domains": unexpected_observed_domains,
        "expected_pattern": validation_case.expected_signal_pattern,
        "validation_goal": validation_case.validation_goal,
        "reference_sources": list(validation_case.reference_sources),
        "validation_metrics": list(validation_case.validation_metrics),
        "known_limitations": list(validation_case.known_limitations),
        "reprocessing_comparison": reprocessing_comparison or {},
    }
    if validation_cases is not None:
        read_model["validation_cases"] = validation_cases
        read_model["portfolio_summary"] = portfolio_summary or build_validation_portfolio_summary(validation_cases)
    if reference_case_library is not None:
        read_model["reference_case_library"] = reference_case_library
        read_model["reference_case_library_summary"] = (
            reference_case_library_summary or build_reference_case_library_summary(reference_case_library)
        )
    return read_model
