from __future__ import annotations

from siasa.validation.cases import ValidationCase


def build_validation_backtest_read_model(
    validation_case: ValidationCase,
    comparison: dict[str, object],
    reprocessing_comparison: dict[str, object] | None = None,
) -> dict[str, object]:
    expected_domains = list(validation_case.expected_domains)
    observed_domains = list(comparison.get("observed_domains", []))
    missing_expected_domains = [domain for domain in expected_domains if domain not in observed_domains]
    unexpected_observed_domains = [domain for domain in observed_domains if domain not in expected_domains]
    status_match = comparison.get("status_match")
    if status_match and not missing_expected_domains and not unexpected_observed_domains:
        review_verdict = "match"
    elif status_match:
        review_verdict = "match_with_gaps"
    else:
        review_verdict = "mismatch"
    return {
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
