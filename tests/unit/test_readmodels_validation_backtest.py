from pathlib import Path

from siasa.readmodels.validation_backtest import (
    build_historical_reference_review_summary,
    build_historical_replay_summary,
    build_reference_case_library_summary,
    build_validation_backtest_read_model,
    build_validation_portfolio_summary,
)
from siasa.runs.reprocessing import build_reprocessing_comparison
from siasa.validation.archival_replay import load_governed_historical_replay_inputs
from siasa.validation.cases import ValidationCase, compare_expected_vs_observed, load_validation_case_library
from siasa.validation.historical_replay import build_historical_replay_reviews, load_historical_replay_inputs


def test_validation_backtest_read_model_exposes_case_context_comparison_and_reprocessing_delta() -> None:
    case = ValidationCase(
        case_id="VAL-UKR-2022-001",
        country_id="UKR",
        case_name="Escalation reference case",
        case_type="military_escalation",
        time_start="2022-02-01",
        time_end="2022-03-01",
        expected_domains=["A", "B", "D"],
        expected_status="S3",
        expected_signal_pattern="Aligned information, event, and economic stress escalation.",
        reference_sources=["SRC-A", "SRC-B"],
        validation_goal="Check multi-domain alignment detection.",
        known_limitations=["historical coverage incomplete"],
        validation_metrics=["Domain Match", "Status Match"],
    )
    comparison = compare_expected_vs_observed(
        validation_case=case,
        observed_domains=["A", "B"],
        observed_status="S3",
        expected_status="S3",
    )
    reprocessing = build_reprocessing_comparison(
        prior_snapshot_id="SNAP-RUN-001-v1",
        new_snapshot_id="SNAP-RUN-001-v2",
        prior_versions={"rule_version": "rules-2026-04", "mapping_version": "mapping-v1", "config_version": "config-v2"},
        new_versions={"rule_version": "rules-2026-05", "mapping_version": "mapping-v2", "config_version": "config-v3"},
    )

    read_model = build_validation_backtest_read_model(
        validation_case=case,
        comparison=comparison,
        reprocessing_comparison=reprocessing,
    )

    assert read_model["case_id"] == "VAL-UKR-2022-001"
    assert read_model["country_id"] == "UKR"
    assert read_model["time_range"] == {"start": "2022-02-01", "end": "2022-03-01"}
    assert read_model["expected_domains"] == ["A", "B", "D"]
    assert read_model["observed_domains"] == ["A", "B"]
    assert read_model["domain_match_ratio"] == 2 / 3
    assert read_model["status_match"] is True
    assert read_model["review_verdict"] == "match_with_gaps"
    assert read_model["missing_expected_domains"] == ["D"]
    assert read_model["unexpected_observed_domains"] == []
    assert read_model["validation_metrics"] == ["Domain Match", "Status Match"]
    assert read_model["reprocessing_comparison"]["changed_versions"] == ["config_version", "mapping_version", "rule_version"]



def test_validation_backtest_read_model_marks_runtime_support_checks_without_status_baseline() -> None:
    case = ValidationCase(
        case_id="VAL-UKR-LIVE-PILOT-SUPPORT",
        country_id="UKR",
        case_name="Governed live runtime support case for UKR",
        case_type="pilot_runtime_support_case",
        time_start="2024",
        time_end="2026-05-15T05:30:00Z",
        expected_domains=["A", "B", "D"],
        expected_status="S3",
        expected_signal_pattern="Governed live pilot should expose the configured active domains and emit a reviewable validation artifact for the current bundle.",
        reference_sources=["SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
        validation_goal="Check validation artifact generation and expected-versus-observed domain visibility for the governed live pilot bundle.",
        known_limitations=["pilot_runtime_support_case_not_historical_backtest"],
        validation_metrics=["Artifact Presence", "Domain Match", "Status Match"],
    )
    read_model = build_validation_backtest_read_model(
        validation_case=case,
        comparison={
            "observed_domains": ["A", "B", "D"],
            "domain_match_ratio": 1.0,
            "status_match": None,
        },
        reprocessing_comparison={},
    )

    assert read_model["status_match"] is None
    assert read_model["review_verdict"] == "support_check"



def test_validation_backtest_portfolio_summary_aggregates_case_counts_verdicts_and_gap_cases() -> None:
    portfolio = build_validation_portfolio_summary(
        [
            {
                "case_id": "VAL-UKR-LIVE-PILOT-SUPPORT",
                "country_id": "UKR",
                "review_verdict": "support_check",
            },
            {
                "case_id": "VAL-POL-LIVE-PILOT-SUPPORT",
                "country_id": "POL",
                "review_verdict": "support_check_with_gaps",
            },
            {
                "case_id": "VAL-ISR-LIVE-PILOT-SUPPORT",
                "country_id": "ISR",
                "review_verdict": "support_check",
            },
        ]
    )

    assert portfolio == {
        "case_count": 3,
        "countries_covered": ["ISR", "POL", "UKR"],
        "review_verdict_counts": {"support_check": 2, "support_check_with_gaps": 1},
        "cases_with_gaps": [
            {
                "case_id": "VAL-POL-LIVE-PILOT-SUPPORT",
                "country_id": "POL",
                "review_verdict": "support_check_with_gaps",
            }
        ],
    }


def test_reference_case_library_summary_aggregates_case_types_countries_and_time_bounds() -> None:
    cases = load_validation_case_library(
        Path(__file__).resolve().parents[2] / "vmodel" / "verification" / "validation_reference_cases.yaml"
    )

    summary = build_reference_case_library_summary(cases)

    assert summary == {
        "case_count": 49,
        "countries_covered": ["AFG", "AZE", "BWA", "CAN", "CHE", "CHN", "CRI", "DEU", "EGY", "EST", "FIN", "GEO", "GHA", "IND", "IRN", "ISR", "JPN", "MMR", "NER", "NGA", "NLD", "NOR", "OMN", "PAK", "POL", "QAT", "RUS", "SAU", "SDN", "SYR", "TUR", "TWN", "UKR", "URY", "USA"],
        "case_type_counts": {
            "armed_conflict_onset": 2,
            "challenge_domain_gap": 3,
            "challenge_mismatch": 3,
            "challenge_overcall": 3,
            "challenge_weak_evidence": 3,
            "coup": 2,
            "disinformation_spike": 1,
            "hybrid_pressure": 3,
            "military_escalation": 1,
            "quiet_control": 8,
            "regime_collapse": 1,
            "state_collapse": 1,
            "strategic_posturing": 18,
        },
        "time_range": {"start": "2021-01-01", "end": "2024-12-31"},
    }


def test_historical_reference_review_summary_scores_curated_case_alignment_and_evidence_tiers() -> None:
    cases = load_validation_case_library(
        Path(__file__).resolve().parents[2] / "vmodel" / "verification" / "validation_reference_cases.yaml"
    )

    summary = build_historical_reference_review_summary(cases)

    assert summary == {
        "case_count": 49,
        "countries_covered": ["AFG", "AZE", "BWA", "CAN", "CHE", "CHN", "CRI", "DEU", "EGY", "EST", "FIN", "GEO", "GHA", "IND", "IRN", "ISR", "JPN", "MMR", "NER", "NGA", "NLD", "NOR", "OMN", "PAK", "POL", "QAT", "RUS", "SAU", "SDN", "SYR", "TUR", "TWN", "UKR", "URY", "USA"],
        "review_verdict_counts": {
            "historical_alignment_confirmed": 34,
            "historical_alignment_mismatch": 10,
            "historical_alignment_with_gaps": 5,
        },
        "evidence_tier_counts": {
            "corroborated_multi_source": 19,
            "curated_public_source": 21,
            "provisional": 1,
            "verified_multi_source": 8,
        },
        "average_evidence_score": 0.74,
    }


def test_validation_reference_library_includes_extended_focus_challenge_cases_for_usa_deu_egy() -> None:
    cases = load_validation_case_library(
        Path(__file__).resolve().parents[2] / "vmodel" / "verification" / "validation_reference_cases.yaml"
    )

    challenge_ids = sorted(case.case_id for case in cases if "CHALLENGE" in case.case_id)

    assert challenge_ids == [
        "VAL-CAN-2024-CHALLENGE-001",
        "VAL-CHE-2024-CHALLENGE-001",
        "VAL-CHN-2024-CHALLENGE-001",
        "VAL-DEU-2024-CHALLENGE-001",
        "VAL-EGY-2024-CHALLENGE-001",
        "VAL-GEO-2023-CHALLENGE-001",
        "VAL-IRN-2023-CHALLENGE-001",
        "VAL-NLD-2024-CHALLENGE-001",
        "VAL-PAK-2024-CHALLENGE-001",
        "VAL-RUS-2024-CHALLENGE-001",
        "VAL-UKR-2023-CHALLENGE-001",
        "VAL-USA-2024-CHALLENGE-001",
    ]


def test_historical_replay_summary_marks_status_only_mismatch_without_domain_gap_distinctly() -> None:
    summary = build_historical_replay_summary(
        [
            {
                "case_id": "VAL-TST-MISMATCH-001",
                "country_id": "UKR",
                "review_verdict": "replay_mismatch",
                "status_match": False,
                "missing_expected_domains": [],
                "unexpected_observed_domains": [],
                "replay_evidence_tier": "verified_replay_evidence",
                "replay_source_coverage_ratio": 1.0,
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 0.7,
                "domain_match_ratio": 1.0,
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDELT-DOC"],
                "replay_input_record_count": 2,
                "archival_data_files": ["archival_replay_inputs/VAL-TST-MISMATCH-001.json"],
            }
        ]
    )

    assert summary["attention_cases"] == [
        {
            "case_id": "VAL-TST-MISMATCH-001",
            "country_id": "UKR",
            "review_verdict": "replay_mismatch",
            "attention_level": "high",
            "attention_reason": "status_mismatch",
            "owner_hint": "validation governance",
            "replay_evidence_tier": "verified_replay_evidence",
            "replay_source_coverage_ratio": 1.0,
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "suggested_next_action": "Review reference-case expectation alignment before using this case as a strong validation signal.",
        }
    ]


def test_historical_replay_summary_marks_status_overcall_without_domain_gap_distinctly() -> None:
    summary = build_historical_replay_summary(
        [
            {
                "case_id": "VAL-TST-OVERCALL-001",
                "country_id": "CHE",
                "review_verdict": "replay_mismatch",
                "status_match": False,
                "expected_status": "S1",
                "replayed_status": "S3",
                "missing_expected_domains": [],
                "unexpected_observed_domains": [],
                "replay_evidence_tier": "partial_replay_evidence",
                "replay_source_coverage_ratio": 1.0,
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 0.6,
                "domain_match_ratio": 1.0,
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "SRC-GDACS", "WB-INDICATORS"],
                "replay_input_record_count": 8,
                "archival_data_files": ["archival_replay_inputs/VAL-TST-OVERCALL-001.json"],
            }
        ]
    )

    assert summary["attention_cases"] == [
        {
            "case_id": "VAL-TST-OVERCALL-001",
            "country_id": "CHE",
            "review_verdict": "replay_mismatch",
            "attention_level": "high",
            "attention_reason": "status_overcall",
            "owner_hint": "validation governance",
            "replay_evidence_tier": "partial_replay_evidence",
            "replay_source_coverage_ratio": 1.0,
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "suggested_next_action": "Review why replay evidence escalates above the bounded reference expectation before treating this case as a credible high-severity signal.",
        }
    ]


def test_historical_replay_summary_preserves_unexpected_observed_domain_attention_details() -> None:
    summary = build_historical_replay_summary(
        [
            {
                "case_id": "VAL-TST-UNEXPECTED-001",
                "country_id": "UKR",
                "review_verdict": "replay_match_with_gaps",
                "status_match": True,
                "missing_expected_domains": [],
                "unexpected_observed_domains": ["E"],
                "replay_evidence_tier": "strong_replay_evidence",
                "replay_source_coverage_ratio": 1.0,
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 0.8,
                "domain_match_ratio": 0.75,
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDELT-DOC"],
                "replay_input_record_count": 3,
                "archival_data_files": ["archival_replay_inputs/VAL-TST-UNEXPECTED-001.json"],
            }
        ]
    )

    assert summary["attention_cases"] == [
        {
            "case_id": "VAL-TST-UNEXPECTED-001",
            "country_id": "UKR",
            "review_verdict": "replay_match_with_gaps",
            "attention_level": "medium",
            "attention_reason": "domain_coverage_gap",
            "owner_hint": "runtime/source coverage",
            "replay_evidence_tier": "strong_replay_evidence",
            "replay_source_coverage_ratio": 1.0,
            "missing_expected_domains": [],
            "unexpected_observed_domains": ["E"],
            "suggested_next_action": "Review unexpected replayed domains and reference-case scoping before treating this replay as fully representative.",
        }
    ]


def test_historical_replay_summary_prioritizes_zero_source_coverage_before_partial_coverage() -> None:
    summary = build_historical_replay_summary(
        [
            {
                "case_id": "VAL-TST-ZERO-COVERAGE-001",
                "country_id": "UKR",
                "review_verdict": "replay_match_with_gaps",
                "status_match": True,
                "missing_expected_domains": ["D"],
                "unexpected_observed_domains": [],
                "replay_evidence_tier": "strong_replay_evidence",
                "replay_source_coverage_ratio": 0.0,
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 0.6,
                "domain_match_ratio": 0.66,
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": [],
                "replay_input_record_count": 0,
                "archival_data_files": [],
            },
            {
                "case_id": "VAL-TST-PARTIAL-COVERAGE-001",
                "country_id": "POL",
                "review_verdict": "replay_match_with_gaps",
                "status_match": True,
                "missing_expected_domains": ["D"],
                "unexpected_observed_domains": [],
                "replay_evidence_tier": "strong_replay_evidence",
                "replay_source_coverage_ratio": 0.5,
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 0.7,
                "domain_match_ratio": 0.66,
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDELT-DOC"],
                "replay_input_record_count": 2,
                "archival_data_files": ["archival_replay_inputs/VAL-TST-PARTIAL-COVERAGE-001.json"],
            },
        ]
    )

    assert [item["case_id"] for item in summary["attention_cases"]] == [
        "VAL-TST-ZERO-COVERAGE-001",
        "VAL-TST-PARTIAL-COVERAGE-001",
    ]


def test_historical_replay_summary_tolerates_legacy_null_domain_lists_and_non_numeric_coverage() -> None:
    summary = build_historical_replay_summary(
        [
            {
                "case_id": "VAL-TST-LEGACY-001",
                "country_id": "UKR",
                "review_verdict": "replay_match_with_gaps",
                "status_match": True,
                "missing_expected_domains": None,
                "unexpected_observed_domains": None,
                "replay_evidence_tier": "strong_replay_evidence",
                "replay_source_coverage_ratio": "n/a",
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 0.8,
                "domain_match_ratio": 0.75,
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDELT-DOC"],
                "replay_input_record_count": 3,
                "archival_data_files": ["archival_replay_inputs/VAL-TST-LEGACY-001.json"],
            }
        ]
    )

    assert summary["attention_case_count"] == 1
    assert summary["attention_level_counts"] == {"medium": 1}
    assert summary["attention_reason_counts"] == {"domain_coverage_gap": 1}
    assert summary["attention_owner_counts"] == {"runtime/source coverage": 1}
    assert summary["attention_country_summary"] == [
        {
            "country_id": "UKR",
            "attention_case_count": 1,
            "highest_attention_level": "medium",
            "case_ids": ["VAL-TST-LEGACY-001"],
        }
    ]
    assert summary["attention_cases"] == [
        {
            "case_id": "VAL-TST-LEGACY-001",
            "country_id": "UKR",
            "review_verdict": "replay_match_with_gaps",
            "attention_level": "medium",
            "attention_reason": "domain_coverage_gap",
            "owner_hint": "runtime/source coverage",
            "replay_evidence_tier": "strong_replay_evidence",
            "replay_source_coverage_ratio": "n/a",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "suggested_next_action": "Review missing expected domains and source coverage before treating this replay as fully representative.",
        }
    ]


def test_historical_replay_summary_aggregates_attention_by_country_and_owner() -> None:
    summary = build_historical_replay_summary(
        [
            {
                "case_id": "VAL-TST-UKR-MISMATCH-001",
                "country_id": "UKR",
                "review_verdict": "replay_mismatch",
                "status_match": False,
                "missing_expected_domains": ["B"],
                "unexpected_observed_domains": [],
                "replay_evidence_tier": "verified_replay_evidence",
                "replay_source_coverage_ratio": 0.5,
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDELT-DOC"],
            },
            {
                "case_id": "VAL-TST-UKR-GAP-002",
                "country_id": "UKR",
                "review_verdict": "replay_match_with_gaps",
                "status_match": True,
                "missing_expected_domains": ["D"],
                "unexpected_observed_domains": [],
                "replay_evidence_tier": "strong_replay_evidence",
                "replay_source_coverage_ratio": 0.75,
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDELT-EVENTS"],
            },
            {
                "case_id": "VAL-TST-POL-WEAK-003",
                "country_id": "POL",
                "review_verdict": "replay_match",
                "status_match": True,
                "missing_expected_domains": [],
                "unexpected_observed_domains": [],
                "replay_evidence_tier": "weak_replay_evidence",
                "replay_source_coverage_ratio": 1.0,
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDACS"],
            },
        ]
    )

    assert summary["attention_level_counts"] == {"high": 1, "medium": 2}
    assert summary["attention_reason_counts"] == {
        "domain_coverage_gap": 1,
        "status_mismatch_and_domain_gap": 1,
        "weak_replay_evidence": 1,
    }
    assert summary["attention_owner_counts"] == {
        "archival replay provenance": 1,
        "runtime/source coverage": 1,
        "validation governance": 1,
    }
    assert summary["attention_country_summary"] == [
        {
            "country_id": "UKR",
            "attention_case_count": 2,
            "highest_attention_level": "high",
            "case_ids": ["VAL-TST-UKR-MISMATCH-001", "VAL-TST-UKR-GAP-002"],
        },
        {
            "country_id": "POL",
            "attention_case_count": 1,
            "highest_attention_level": "medium",
            "case_ids": ["VAL-TST-POL-WEAK-003"],
        },
    ]


def test_historical_replay_summary_scores_fixture_backed_true_replay_cases() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    cases = load_validation_case_library(repo_root / "vmodel" / "verification" / "validation_reference_cases.yaml")
    replay_inputs = load_governed_historical_replay_inputs(repo_root)

    reviews = build_historical_replay_reviews(cases, replay_inputs)
    summary = build_historical_replay_summary(reviews)

    assert [review["case_id"] for review in reviews] == [
        "VAL-UKR-2022-001",
        "VAL-RUS-2024-001",
        "VAL-CHN-2024-001",
        "VAL-IND-2024-001",
        "VAL-IRN-2024-001",
        "VAL-TUR-2024-001",
        "VAL-USA-2024-001",
        "VAL-DEU-2024-001",
        "VAL-EST-2024-001",
        "VAL-FIN-2024-001",
        "VAL-SAU-2024-001",
        "VAL-QAT-2024-001",
        "VAL-EGY-2024-001",
        "VAL-NGA-2024-001",
        "VAL-SDN-2024-001",
        "VAL-MMR-2024-001",
        "VAL-POL-2023-001",
        "VAL-POL-2024-002",
        "VAL-ISR-2023-001",
        "VAL-ISR-2024-002",
        "VAL-PAK-2024-001",
        "VAL-GEO-2024-001",
        "VAL-TWN-2024-001",
        "VAL-UKR-2023-CHALLENGE-001",
        "VAL-IRN-2023-CHALLENGE-001",
        "VAL-GEO-2023-CHALLENGE-001",
        "VAL-RUS-2024-CHALLENGE-001",
        "VAL-CHN-2024-CHALLENGE-001",
        "VAL-PAK-2024-CHALLENGE-001",
        "VAL-USA-2024-CHALLENGE-001",
        "VAL-DEU-2024-CHALLENGE-001",
        "VAL-EGY-2024-CHALLENGE-001",
        "VAL-CHE-2024-CHALLENGE-001",
        "VAL-NLD-2024-CHALLENGE-001",
        "VAL-CAN-2024-CHALLENGE-001",
    ]
    assert summary == {
        "case_count": 35,
        "countries_covered": ["CAN", "CHE", "CHN", "DEU", "EGY", "EST", "FIN", "GEO", "IND", "IRN", "ISR", "MMR", "NGA", "NLD", "PAK", "POL", "QAT", "RUS", "SAU", "SDN", "TUR", "TWN", "UKR", "USA"],
        "review_verdict_counts": {
            "replay_match": 21,
            "replay_match_with_gaps": 4,
            "replay_mismatch": 10,
        },
        "status_match_count": 25,
        "average_domain_match_ratio": 0.83,
        "average_replay_evidence_score": 0.8,
        "average_replay_source_coverage_ratio": 0.82,
        "average_replay_provenance_completeness_ratio": 1.0,
        "replay_input_record_total": 219,
        "archival_data_file_count": 35,
        "replay_evidence_tier_counts": {
            "partial_replay_evidence": 3,
            "strong_replay_evidence": 4,
            "verified_replay_evidence": 21,
            "weak_replay_evidence": 7,
        },
        "replay_input_source_coverage_counts": {
            "SRC-GDACS": 28,
            "SRC-GDELT-DOC": 35,
            "SRC-GDELT-EVENTS": 28,
            "WB-INDICATORS": 23,
        },
        "review_basis_counts": {
            "provider_backed_archival_replay": 35,
        },
        "attention_case_count": 14,
        "attention_level_counts": {
            "high": 10,
            "medium": 4,
        },
        "attention_reason_counts": {
            "domain_coverage_gap": 4,
            "status_mismatch_and_domain_gap": 7,
            "status_overcall": 3,
        },
        "attention_owner_counts": {
            "runtime/source coverage": 4,
            "validation governance": 10,
        },
        "attention_country_summary": [
            {"country_id": "CAN", "attention_case_count": 1, "highest_attention_level": "high", "case_ids": ["VAL-CAN-2024-CHALLENGE-001"]},
            {"country_id": "CHE", "attention_case_count": 1, "highest_attention_level": "high", "case_ids": ["VAL-CHE-2024-CHALLENGE-001"]},
            {"country_id": "EGY", "attention_case_count": 1, "highest_attention_level": "high", "case_ids": ["VAL-EGY-2024-CHALLENGE-001"]},
            {"country_id": "GEO", "attention_case_count": 1, "highest_attention_level": "high", "case_ids": ["VAL-GEO-2023-CHALLENGE-001"]},
            {"country_id": "ISR", "attention_case_count": 1, "highest_attention_level": "high", "case_ids": ["VAL-ISR-2024-002"]},
            {"country_id": "NLD", "attention_case_count": 1, "highest_attention_level": "high", "case_ids": ["VAL-NLD-2024-CHALLENGE-001"]},
            {"country_id": "PAK", "attention_case_count": 1, "highest_attention_level": "high", "case_ids": ["VAL-PAK-2024-CHALLENGE-001"]},
            {"country_id": "RUS", "attention_case_count": 1, "highest_attention_level": "high", "case_ids": ["VAL-RUS-2024-CHALLENGE-001"]},
            {"country_id": "UKR", "attention_case_count": 1, "highest_attention_level": "high", "case_ids": ["VAL-UKR-2023-CHALLENGE-001"]},
            {"country_id": "USA", "attention_case_count": 1, "highest_attention_level": "high", "case_ids": ["VAL-USA-2024-CHALLENGE-001"]},
            {"country_id": "CHN", "attention_case_count": 1, "highest_attention_level": "medium", "case_ids": ["VAL-CHN-2024-CHALLENGE-001"]},
            {"country_id": "DEU", "attention_case_count": 1, "highest_attention_level": "medium", "case_ids": ["VAL-DEU-2024-CHALLENGE-001"]},
            {"country_id": "IRN", "attention_case_count": 1, "highest_attention_level": "medium", "case_ids": ["VAL-IRN-2023-CHALLENGE-001"]},
            {"country_id": "POL", "attention_case_count": 1, "highest_attention_level": "medium", "case_ids": ["VAL-POL-2024-002"]},
        ],
        "attention_cases": [
            {
                "case_id": "VAL-EGY-2024-CHALLENGE-001",
                "country_id": "EGY",
                "review_verdict": "replay_mismatch",
                "attention_level": "high",
                "attention_reason": "status_mismatch_and_domain_gap",
                "owner_hint": "validation governance",
                "replay_evidence_tier": "weak_replay_evidence",
                "replay_source_coverage_ratio": 0.25,
                "missing_expected_domains": ["B", "D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review reference-case expectation alignment and archival replay provenance before using this case as a strong validation signal.",
            },
            {
                "case_id": "VAL-GEO-2023-CHALLENGE-001",
                "country_id": "GEO",
                "review_verdict": "replay_mismatch",
                "attention_level": "high",
                "attention_reason": "status_mismatch_and_domain_gap",
                "owner_hint": "validation governance",
                "replay_evidence_tier": "weak_replay_evidence",
                "replay_source_coverage_ratio": 0.25,
                "missing_expected_domains": ["B", "D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review reference-case expectation alignment and archival replay provenance before using this case as a strong validation signal.",
            },
            {
                "case_id": "VAL-ISR-2024-002",
                "country_id": "ISR",
                "review_verdict": "replay_mismatch",
                "attention_level": "high",
                "attention_reason": "status_mismatch_and_domain_gap",
                "owner_hint": "validation governance",
                "replay_evidence_tier": "weak_replay_evidence",
                "replay_source_coverage_ratio": 0.25,
                "missing_expected_domains": ["B", "D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review reference-case expectation alignment and archival replay provenance before using this case as a strong validation signal.",
            },
            {
                "case_id": "VAL-PAK-2024-CHALLENGE-001",
                "country_id": "PAK",
                "review_verdict": "replay_mismatch",
                "attention_level": "high",
                "attention_reason": "status_mismatch_and_domain_gap",
                "owner_hint": "validation governance",
                "replay_evidence_tier": "weak_replay_evidence",
                "replay_source_coverage_ratio": 0.25,
                "missing_expected_domains": ["B", "D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review reference-case expectation alignment and archival replay provenance before using this case as a strong validation signal.",
            },
            {
                "case_id": "VAL-RUS-2024-CHALLENGE-001",
                "country_id": "RUS",
                "review_verdict": "replay_mismatch",
                "attention_level": "high",
                "attention_reason": "status_mismatch_and_domain_gap",
                "owner_hint": "validation governance",
                "replay_evidence_tier": "weak_replay_evidence",
                "replay_source_coverage_ratio": 0.25,
                "missing_expected_domains": ["B", "D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review reference-case expectation alignment and archival replay provenance before using this case as a strong validation signal.",
            },
            {
                "case_id": "VAL-UKR-2023-CHALLENGE-001",
                "country_id": "UKR",
                "review_verdict": "replay_mismatch",
                "attention_level": "high",
                "attention_reason": "status_mismatch_and_domain_gap",
                "owner_hint": "validation governance",
                "replay_evidence_tier": "weak_replay_evidence",
                "replay_source_coverage_ratio": 0.25,
                "missing_expected_domains": ["B", "D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review reference-case expectation alignment and archival replay provenance before using this case as a strong validation signal.",
            },
            {
                "case_id": "VAL-USA-2024-CHALLENGE-001",
                "country_id": "USA",
                "review_verdict": "replay_mismatch",
                "attention_level": "high",
                "attention_reason": "status_mismatch_and_domain_gap",
                "owner_hint": "validation governance",
                "replay_evidence_tier": "weak_replay_evidence",
                "replay_source_coverage_ratio": 0.25,
                "missing_expected_domains": ["B", "D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review reference-case expectation alignment and archival replay provenance before using this case as a strong validation signal.",
            },
            {
                "case_id": "VAL-CAN-2024-CHALLENGE-001",
                "country_id": "CAN",
                "review_verdict": "replay_mismatch",
                "attention_level": "high",
                "attention_reason": "status_overcall",
                "owner_hint": "validation governance",
                "replay_evidence_tier": "partial_replay_evidence",
                "replay_source_coverage_ratio": 1.0,
                "missing_expected_domains": [],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review why replay evidence escalates above the bounded reference expectation before treating this case as a credible high-severity signal.",
            },
            {
                "case_id": "VAL-CHE-2024-CHALLENGE-001",
                "country_id": "CHE",
                "review_verdict": "replay_mismatch",
                "attention_level": "high",
                "attention_reason": "status_overcall",
                "owner_hint": "validation governance",
                "replay_evidence_tier": "partial_replay_evidence",
                "replay_source_coverage_ratio": 1.0,
                "missing_expected_domains": [],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review why replay evidence escalates above the bounded reference expectation before treating this case as a credible high-severity signal.",
            },
            {
                "case_id": "VAL-NLD-2024-CHALLENGE-001",
                "country_id": "NLD",
                "review_verdict": "replay_mismatch",
                "attention_level": "high",
                "attention_reason": "status_overcall",
                "owner_hint": "validation governance",
                "replay_evidence_tier": "partial_replay_evidence",
                "replay_source_coverage_ratio": 1.0,
                "missing_expected_domains": [],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review why replay evidence escalates above the bounded reference expectation before treating this case as a credible high-severity signal.",
            },
            {
                "case_id": "VAL-CHN-2024-CHALLENGE-001",
                "country_id": "CHN",
                "review_verdict": "replay_match_with_gaps",
                "attention_level": "medium",
                "attention_reason": "domain_coverage_gap",
                "owner_hint": "runtime/source coverage",
                "replay_evidence_tier": "strong_replay_evidence",
                "replay_source_coverage_ratio": 0.75,
                "missing_expected_domains": ["D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review missing expected domains and source coverage before treating this replay as fully representative.",
            },
            {
                "case_id": "VAL-DEU-2024-CHALLENGE-001",
                "country_id": "DEU",
                "review_verdict": "replay_match_with_gaps",
                "attention_level": "medium",
                "attention_reason": "domain_coverage_gap",
                "owner_hint": "runtime/source coverage",
                "replay_evidence_tier": "strong_replay_evidence",
                "replay_source_coverage_ratio": 0.75,
                "missing_expected_domains": ["D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review missing expected domains and source coverage before treating this replay as fully representative.",
            },
            {
                "case_id": "VAL-IRN-2023-CHALLENGE-001",
                "country_id": "IRN",
                "review_verdict": "replay_match_with_gaps",
                "attention_level": "medium",
                "attention_reason": "domain_coverage_gap",
                "owner_hint": "runtime/source coverage",
                "replay_evidence_tier": "strong_replay_evidence",
                "replay_source_coverage_ratio": 0.75,
                "missing_expected_domains": ["D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review missing expected domains and source coverage before treating this replay as fully representative.",
            },
            {
                "case_id": "VAL-POL-2024-002",
                "country_id": "POL",
                "review_verdict": "replay_match_with_gaps",
                "attention_level": "medium",
                "attention_reason": "domain_coverage_gap",
                "owner_hint": "runtime/source coverage",
                "replay_evidence_tier": "strong_replay_evidence",
                "replay_source_coverage_ratio": 0.75,
                "missing_expected_domains": ["D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review missing expected domains and source coverage before treating this replay as fully representative.",
            },
        ],
    }
