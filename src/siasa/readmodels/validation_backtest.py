from __future__ import annotations

from collections import Counter

from siasa.validation.cases import ValidationCase, validation_case_to_dict


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


def _evidence_tier_score(evidence_tier: str) -> float:
    return {
        "verified_multi_source": 1.0,
        "corroborated_multi_source": 0.8,
        "curated_public_source": 0.6,
        "provisional": 0.4,
    }.get(evidence_tier, 0.5)


def build_historical_reference_reviews(reference_case_library: list[ValidationCase | dict[str, object]]) -> list[dict[str, object]]:
    reviews: list[dict[str, object]] = []
    for item in reference_case_library:
        case_dict = validation_case_to_dict(item) if isinstance(item, ValidationCase) else dict(item)
        expected_domains = [str(domain) for domain in case_dict.get("expected_domains", [])]
        observed_domains = [str(domain) for domain in case_dict.get("historical_observed_domains", [])]
        expected_domain_set = set(expected_domains)
        observed_domain_set = set(observed_domains)
        match_count = len(expected_domain_set & observed_domain_set)
        domain_match_ratio = match_count / len(expected_domain_set) if expected_domain_set else 0.0
        expected_status = str(case_dict.get("expected_status", "S0"))
        observed_status = case_dict.get("historical_observed_status")
        status_match = observed_status == expected_status if observed_status is not None else False
        missing_expected_domains = [domain for domain in expected_domains if domain not in observed_domains]
        unexpected_observed_domains = [domain for domain in observed_domains if domain not in expected_domains]
        review_verdict = (
            "historical_alignment_confirmed"
            if status_match and not missing_expected_domains and not unexpected_observed_domains
            else "historical_alignment_with_gaps"
            if status_match
            else "historical_alignment_mismatch"
        )
        evidence_tier = str(case_dict.get("evidence_tier", "curated_public_source"))
        evidence_score = round(_evidence_tier_score(evidence_tier), 2)
        reviews.append(
            {
                "case_id": str(case_dict.get("case_id", "")),
                "country_id": str(case_dict.get("country_id", "")),
                "case_type": str(case_dict.get("case_type", "")),
                "expected_status": expected_status,
                "historical_observed_status": observed_status,
                "expected_domains": expected_domains,
                "historical_observed_domains": observed_domains,
                "domain_match_ratio": domain_match_ratio,
                "status_match": status_match,
                "review_verdict": review_verdict,
                "evidence_tier": evidence_tier,
                "evidence_score": evidence_score,
                "missing_expected_domains": missing_expected_domains,
                "unexpected_observed_domains": unexpected_observed_domains,
            }
        )
    return reviews


def build_historical_reference_review_summary(reference_case_library: list[ValidationCase | dict[str, object]]) -> dict[str, object]:
    reviews = build_historical_reference_reviews(reference_case_library)
    verdict_counts = Counter(str(review.get("review_verdict")) for review in reviews if review.get("review_verdict"))
    evidence_tier_counts = Counter(str(review.get("evidence_tier")) for review in reviews if review.get("evidence_tier"))
    evidence_scores = [float(review.get("evidence_score")) for review in reviews if isinstance(review.get("evidence_score"), (int, float))]
    countries_covered = sorted({str(review.get("country_id")) for review in reviews if review.get("country_id")})
    average_evidence_score = round(sum(evidence_scores) / len(evidence_scores), 2) if evidence_scores else 0.0
    return {
        "case_count": len(reviews),
        "countries_covered": countries_covered,
        "review_verdict_counts": dict(sorted(verdict_counts.items())),
        "evidence_tier_counts": dict(sorted(evidence_tier_counts.items())),
        "average_evidence_score": average_evidence_score,
    }



def build_historical_replay_summary(historical_replay_reviews: list[dict[str, object]]) -> dict[str, object]:
    verdict_counts = Counter(
        str(review.get("review_verdict"))
        for review in historical_replay_reviews
        if isinstance(review, dict) and review.get("review_verdict")
    )
    review_basis_counts = Counter(
        str(review.get("review_basis"))
        for review in historical_replay_reviews
        if isinstance(review, dict) and review.get("review_basis")
    )
    countries_covered = sorted(
        {
            str(review.get("country_id"))
            for review in historical_replay_reviews
            if isinstance(review, dict) and review.get("country_id")
        }
    )
    domain_match_ratios = [
        float(review.get("domain_match_ratio"))
        for review in historical_replay_reviews
        if isinstance(review, dict) and isinstance(review.get("domain_match_ratio"), (int, float))
    ]
    status_match_count = len(
        [review for review in historical_replay_reviews if isinstance(review, dict) and review.get("status_match") is True]
    )
    return {
        "case_count": len([review for review in historical_replay_reviews if isinstance(review, dict)]),
        "countries_covered": countries_covered,
        "review_verdict_counts": dict(sorted(verdict_counts.items())),
        "status_match_count": status_match_count,
        "average_domain_match_ratio": round(sum(domain_match_ratios) / len(domain_match_ratios), 2) if domain_match_ratios else 0.0,
        "review_basis_counts": dict(sorted(review_basis_counts.items())),
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
    historical_reference_reviews: list[dict[str, object]] | None = None,
    historical_reference_review_summary: dict[str, object] | None = None,
    historical_replay_reviews: list[dict[str, object]] | None = None,
    historical_replay_summary: dict[str, object] | None = None,
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
        historical_reviews = historical_reference_reviews or build_historical_reference_reviews(reference_case_library)
        read_model["historical_reference_reviews"] = historical_reviews
        read_model["historical_reference_review_summary"] = (
            historical_reference_review_summary or build_historical_reference_review_summary(reference_case_library)
        )
    if historical_replay_reviews is not None:
        read_model["historical_replay_reviews"] = historical_replay_reviews
        read_model["historical_replay_summary"] = (
            historical_replay_summary or build_historical_replay_summary(historical_replay_reviews)
        )
    return read_model
