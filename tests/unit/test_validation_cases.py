from pathlib import Path

from siasa.validation.cases import ValidationCase, compare_expected_vs_observed, load_validation_case_library


def test_validation_case_persists_identity_time_range_domains_pattern_sources_and_metrics() -> None:
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

    assert case.case_id == "VAL-UKR-2022-001"
    assert case.expected_domains == ["A", "B", "D"]
    assert case.validation_metrics == ["Domain Match", "Status Match"]


def test_backtest_comparison_service_compares_expected_and_observed_domain_patterns() -> None:
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
        known_limitations=[],
        validation_metrics=["Domain Match", "Status Match"],
    )

    comparison = compare_expected_vs_observed(
        validation_case=case,
        observed_domains=["A", "B"],
        observed_status="S3",
        expected_status="S3",
    )

    assert comparison["case_id"] == "VAL-UKR-2022-001"
    assert comparison["domain_match_ratio"] == 2 / 3
    assert comparison["status_match"] is True


def test_load_validation_case_library_reads_curated_reference_cases_from_repo_yaml() -> None:
    cases = load_validation_case_library(
        Path(__file__).resolve().parents[2] / "vmodel" / "verification" / "validation_reference_cases.yaml"
    )

    assert len(cases) >= 4
    assert cases[0].case_id == "VAL-UKR-2022-001"
    assert cases[0].country_id == "UKR"
    assert cases[0].expected_status == "S3"
    assert cases[0].evidence_tier == "verified_multi_source"
    assert cases[0].historical_observed_status == "S3"
    assert cases[0].historical_observed_domains == ["A", "B", "D"]
    assert "Domain Match" in cases[0].validation_metrics
    assert any(case.country_id == "POL" for case in cases)
    assert any(case.country_id == "IND" for case in cases)
    assert any(case.country_id == "IRN" for case in cases)
    assert any(case.country_id == "TUR" for case in cases)
