from __future__ import annotations

from collections import Counter

from siasa.validation.cases import ValidationCase, validation_case_to_dict
from siasa.validation.skill_metrics import compute_skill_metrics


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



def _coerce_string_list(value: object) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None and str(item) != ""]
    return []


def _safe_sortable_ratio(value: object) -> float:
    if value is None:
        return 1.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 1.0


def _attention_owner_hint(attention_reason: str) -> str:
    if attention_reason in {"status_mismatch", "status_mismatch_and_domain_gap", "status_overcall"}:
        return "validation governance"
    if attention_reason == "domain_coverage_gap":
        return "runtime/source coverage"
    if attention_reason == "weak_replay_evidence":
        return "archival replay provenance"
    return "analyst review"


def _attention_level_rank(attention_level: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(attention_level, 9)


def _status_rank(status: str) -> int:
    return {"S0": 0, "S1": 1, "S2": 2, "S3": 3, "S4": 4, "S5": 5, "S6": 6}.get(str(status).upper(), -1)


def _attention_country_summary(attention_cases: list[dict[str, object]]) -> list[dict[str, object]]:
    by_country: dict[str, dict[str, object]] = {}
    for item in attention_cases:
        if not isinstance(item, dict):
            continue
        country_id = str(item.get("country_id", ""))
        if not country_id:
            continue
        entry = by_country.setdefault(
            country_id,
            {
                "country_id": country_id,
                "attention_case_count": 0,
                "highest_attention_level": "low",
                "_highest_attention_rank": 9,
                "case_ids": [],
            },
        )
        attention_level = str(item.get("attention_level", "low"))
        attention_rank = _attention_level_rank(attention_level)
        entry["attention_case_count"] = int(entry["attention_case_count"]) + 1
        if attention_rank < int(entry["_highest_attention_rank"]):
            entry["highest_attention_level"] = attention_level
            entry["_highest_attention_rank"] = attention_rank
        case_id = str(item.get("case_id", ""))
        if case_id:
            entry_case_ids = entry.setdefault("case_ids", [])
            if isinstance(entry_case_ids, list):
                entry_case_ids.append(case_id)
    summaries = []
    for entry in by_country.values():
        case_ids = [str(case_id) for case_id in entry.get("case_ids", []) if case_id]
        summaries.append(
            {
                "country_id": str(entry.get("country_id", "")),
                "attention_case_count": int(entry.get("attention_case_count", 0)),
                "highest_attention_level": str(entry.get("highest_attention_level", "low")),
                "case_ids": case_ids,
                "_highest_attention_rank": int(entry.get("_highest_attention_rank", 9)),
            }
        )
    summaries.sort(
        key=lambda item: (
            int(item.get("_highest_attention_rank", 9)),
            -int(item.get("attention_case_count", 0)),
            str(item.get("country_id", "")),
        )
    )
    return [
        {
            "country_id": str(item.get("country_id", "")),
            "attention_case_count": int(item.get("attention_case_count", 0)),
            "highest_attention_level": str(item.get("highest_attention_level", "low")),
            "case_ids": list(item.get("case_ids", [])),
        }
        for item in summaries
    ]


def _replay_attention_cases(historical_replay_reviews: list[dict[str, object]]) -> list[dict[str, object]]:
    attention_cases: list[dict[str, object]] = []
    for review in historical_replay_reviews:
        if not isinstance(review, dict):
            continue
        review_verdict = str(review.get("review_verdict", ""))
        replay_evidence_tier = str(review.get("replay_evidence_tier", ""))
        if review_verdict == "replay_mismatch":
            missing_expected_domains = _coerce_string_list(review.get("missing_expected_domains"))
            unexpected_observed_domains = _coerce_string_list(review.get("unexpected_observed_domains"))
            has_domain_gap = bool(missing_expected_domains or unexpected_observed_domains)
            attention_level = "high"
            expected_status = str(review.get("expected_status", ""))
            replayed_status = str(review.get("replayed_status", ""))
            is_status_overcall = _status_rank(replayed_status) > _status_rank(expected_status)
            if has_domain_gap:
                attention_reason = "status_mismatch_and_domain_gap"
                if missing_expected_domains and unexpected_observed_domains:
                    suggested_next_action = (
                        "Review missing expected domains, unexpected replayed domains, and archival replay provenance before using this case as a strong validation signal."
                    )
                elif unexpected_observed_domains:
                    suggested_next_action = (
                        "Review unexpected replayed domains and archival replay provenance before using this case as a strong validation signal."
                    )
                else:
                    suggested_next_action = (
                        "Review reference-case expectation alignment and archival replay provenance before using this case as a strong validation signal."
                    )
            elif is_status_overcall:
                attention_reason = "status_overcall"
                suggested_next_action = (
                    "Review why replay evidence escalates above the bounded reference expectation before treating this case as a credible high-severity signal."
                )
            else:
                attention_reason = "status_mismatch"
                suggested_next_action = (
                    "Review reference-case expectation alignment before using this case as a strong validation signal."
                )
        elif review_verdict == "replay_match_with_gaps":
            missing_expected_domains = _coerce_string_list(review.get("missing_expected_domains"))
            unexpected_observed_domains = _coerce_string_list(review.get("unexpected_observed_domains"))
            attention_level = "medium"
            attention_reason = "domain_coverage_gap"
            if missing_expected_domains and unexpected_observed_domains:
                suggested_next_action = (
                    "Review missing expected domains, unexpected replayed domains, and source coverage before treating this replay as fully representative."
                )
            elif unexpected_observed_domains:
                suggested_next_action = (
                    "Review unexpected replayed domains and reference-case scoping before treating this replay as fully representative."
                )
            else:
                suggested_next_action = (
                    "Review missing expected domains and source coverage before treating this replay as fully representative."
                )
        elif replay_evidence_tier == "weak_replay_evidence":
            missing_expected_domains = _coerce_string_list(review.get("missing_expected_domains"))
            unexpected_observed_domains = _coerce_string_list(review.get("unexpected_observed_domains"))
            attention_level = "medium"
            attention_reason = "weak_replay_evidence"
            suggested_next_action = (
                "Review archival replay input quality and provenance completeness before using this case as a strong validation signal."
            )
        else:
            continue
        attention_cases.append(
            {
                "case_id": str(review.get("case_id", "")),
                "country_id": str(review.get("country_id", "")),
                "review_verdict": review_verdict,
                "attention_level": attention_level,
                "attention_reason": attention_reason,
                "owner_hint": _attention_owner_hint(attention_reason),
                "replay_evidence_tier": replay_evidence_tier,
                "replay_source_coverage_ratio": review.get("replay_source_coverage_ratio"),
                "missing_expected_domains": missing_expected_domains,
                "unexpected_observed_domains": unexpected_observed_domains,
                "suggested_next_action": suggested_next_action,
            }
        )
    return sorted(
        attention_cases,
        key=lambda item: (
            _attention_level_rank(str(item.get("attention_level", "low"))),
            _safe_sortable_ratio(item.get("replay_source_coverage_ratio")),
            str(item.get("case_id", "")),
        ),
    )


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
    replay_evidence_tier_counts = Counter(
        str(review.get("replay_evidence_tier"))
        for review in historical_replay_reviews
        if isinstance(review, dict) and review.get("replay_evidence_tier")
    )
    replay_input_source_coverage_counts = Counter(
        str(source_id)
        for review in historical_replay_reviews
        if isinstance(review, dict)
        for source_id in review.get("replay_input_source_ids", [])
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
    replay_evidence_scores = [
        float(review.get("replay_evidence_score"))
        for review in historical_replay_reviews
        if isinstance(review, dict) and isinstance(review.get("replay_evidence_score"), (int, float))
    ]
    replay_source_coverage_ratios = [
        float(review.get("replay_source_coverage_ratio"))
        for review in historical_replay_reviews
        if isinstance(review, dict) and isinstance(review.get("replay_source_coverage_ratio"), (int, float))
    ]
    replay_provenance_completeness_ratios = [
        float(review.get("replay_provenance_completeness_ratio"))
        for review in historical_replay_reviews
        if isinstance(review, dict) and isinstance(review.get("replay_provenance_completeness_ratio"), (int, float))
    ]
    status_match_count = len(
        [review for review in historical_replay_reviews if isinstance(review, dict) and review.get("status_match") is True]
    )
    replay_input_record_total = sum(
        int(review.get("replay_input_record_count", 0))
        for review in historical_replay_reviews
        if isinstance(review, dict) and isinstance(review.get("replay_input_record_count"), (int, float))
    )
    archival_data_file_count = sum(
        len([item for item in review.get("archival_data_files", []) if item])
        for review in historical_replay_reviews
        if isinstance(review, dict)
    )
    attention_cases = _replay_attention_cases(historical_replay_reviews)
    attention_level_counts = Counter(
        str(item.get("attention_level"))
        for item in attention_cases
        if isinstance(item, dict) and item.get("attention_level")
    )
    attention_reason_counts = Counter(
        str(item.get("attention_reason"))
        for item in attention_cases
        if isinstance(item, dict) and item.get("attention_reason")
    )
    attention_owner_counts = Counter(
        str(item.get("owner_hint"))
        for item in attention_cases
        if isinstance(item, dict) and item.get("owner_hint")
    )
    attention_country_summary = _attention_country_summary(attention_cases)
    return {
        "case_count": len([review for review in historical_replay_reviews if isinstance(review, dict)]),
        "countries_covered": countries_covered,
        "review_verdict_counts": dict(sorted(verdict_counts.items())),
        "status_match_count": status_match_count,
        "average_domain_match_ratio": round(sum(domain_match_ratios) / len(domain_match_ratios), 2) if domain_match_ratios else 0.0,
        "average_replay_evidence_score": round(sum(replay_evidence_scores) / len(replay_evidence_scores), 2) if replay_evidence_scores else 0.0,
        "average_replay_source_coverage_ratio": round(sum(replay_source_coverage_ratios) / len(replay_source_coverage_ratios), 2) if replay_source_coverage_ratios else 0.0,
        "average_replay_provenance_completeness_ratio": round(sum(replay_provenance_completeness_ratios) / len(replay_provenance_completeness_ratios), 2) if replay_provenance_completeness_ratios else 0.0,
        "replay_input_record_total": replay_input_record_total,
        "archival_data_file_count": archival_data_file_count,
        "replay_evidence_tier_counts": dict(sorted(replay_evidence_tier_counts.items())),
        "replay_input_source_coverage_counts": dict(sorted(replay_input_source_coverage_counts.items())),
        "review_basis_counts": dict(sorted(review_basis_counts.items())),
        "attention_case_count": len(attention_cases),
        "attention_level_counts": dict(sorted(attention_level_counts.items())),
        "attention_reason_counts": dict(sorted(attention_reason_counts.items())),
        "attention_owner_counts": dict(sorted(attention_owner_counts.items())),
        "attention_country_summary": attention_country_summary,
        "attention_cases": attention_cases,
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
        read_model["skill_metrics"] = compute_skill_metrics(historical_replay_reviews)
        # SwR-112 (audit A-19): report skill per dataset split, with holdout as the
        # designated evaluation split. A split section is only a VALID evaluation
        # when it contains both classes; today the holdout split holds one
        # replay-backed positive (ISR-2023) and zero negatives-with-inputs
        # (audit A-07, AP-34.7), so its section is explicitly marked invalid
        # instead of a 1-positive recall=1.0 masquerading as an evaluation.
        by_split: dict[str, list[dict]] = {}
        for review in historical_replay_reviews:
            if isinstance(review, dict):
                by_split.setdefault(str(review.get("dataset_split", "unassigned")), []).append(review)
        skill_by_split: dict[str, dict] = {}
        for split, split_reviews in sorted(by_split.items()):
            split_metrics = compute_skill_metrics(split_reviews)
            has_both_classes = (
                split_metrics["positive_case_count"] >= 1
                and split_metrics["negative_case_count"] >= 1
            )
            split_metrics["evaluation_valid"] = has_both_classes
            split_metrics["evaluation_invalid_reason"] = (
                None
                if has_both_classes
                else (
                    "degenerate split: needs at least one positive AND one negative "
                    "review (missing replay inputs — audit A-07, AP-34.7)"
                )
            )
            skill_by_split[split] = split_metrics
        read_model["skill_metrics_by_split"] = skill_by_split
        read_model["skill_evaluation_split"] = "holdout"
    return read_model
