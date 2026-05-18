from siasa.readmodels.validation_backtest import build_validation_backtest_read_model, build_validation_portfolio_summary
from siasa.runs.reprocessing import build_reprocessing_comparison
from siasa.validation.cases import ValidationCase, compare_expected_vs_observed


def test_validation_backtest_read_model_exposes_case_context_comparison_and_reprocessing_delta() -> None:
    case = ValidationCase(
        case_id="VAL-UKR-2022-001",
        country_id="UKR",
        case_name="Escalation reference case",
        case_type="military_escalation",
        time_start="2022-02-01",
        time_end="2022-03-01",
        expected_domains=["A", "B", "D"],
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
