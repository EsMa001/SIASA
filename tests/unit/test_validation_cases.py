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
    assert any(case.country_id == "USA" for case in cases)
    assert any(case.country_id == "DEU" for case in cases)
    assert any(case.country_id == "EST" for case in cases)
    assert any(case.country_id == "FIN" for case in cases)
    assert any(case.country_id == "SAU" for case in cases)
    assert any(case.country_id == "QAT" for case in cases)
    assert any(case.country_id == "EGY" for case in cases)
    assert any(case.country_id == "NGA" for case in cases)
    assert any(case.country_id == "SDN" for case in cases)
    assert any(case.country_id == "MMR" for case in cases)


# --- AP-27 ground-truth redesign (SwR-088..090) ---

from siasa.validation.cases import validate_reference_case_library  # noqa: E402

_REFERENCE_CASES_PATH = ("vmodel", "verification", "validation_reference_cases.yaml")


def _gt_case(
    case_id: str,
    expected_status: str,
    *,
    polarity: str = "positive",
    split: str = "unassigned",
    onset: str | None = None,
    trajectory: list[str] | None = None,
    historical: str | None = None,
    time_start: str = "2024-01-01",
    time_end: str = "2024-03-31",
) -> ValidationCase:
    return ValidationCase(
        case_id=case_id,
        country_id="AAA",
        case_name="x",
        case_type="t",
        time_start=time_start,
        time_end=time_end,
        expected_domains=["A", "B"],
        expected_status=expected_status,
        expected_signal_pattern="",
        reference_sources=[],
        validation_goal="",
        known_limitations=[],
        validation_metrics=[],
        historical_observed_status=historical,
        onset_date=onset,
        expected_trajectory=trajectory,
        dataset_split=split,
        case_polarity=polarity,
    )


def test_new_ground_truth_fields_default_backward_compatibly() -> None:
    case = _gt_case("VAL-X", "S3")
    assert case.onset_date is None
    assert case.expected_trajectory is None
    assert case.dataset_split == "unassigned"
    assert case.case_polarity == "positive"


def test_reference_library_loads_exemplary_s0_negative_and_keeps_legacy_defaults() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    cases = load_validation_case_library(repo_root.joinpath(*_REFERENCE_CASES_PATH))
    by_id = {case.case_id: case for case in cases}
    che = by_id["VAL-CHE-2024-NEGATIVE-001"]
    assert che.expected_status == "S0"
    assert che.case_polarity == "negative"
    assert che.dataset_split == "holdout"
    assert che.expected_trajectory == ["S0", "S0", "S0"]
    # legacy cases still load with backward-compatible defaults
    assert by_id["VAL-UKR-2022-001"].case_polarity == "positive"
    assert by_id["VAL-UKR-2022-001"].dataset_split == "unassigned"


def test_validator_passes_structurally_and_counts_the_s0_negative() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    cases = load_validation_case_library(repo_root.joinpath(*_REFERENCE_CASES_PATH))
    report = validate_reference_case_library(cases)
    assert report["is_valid"] is True
    assert report["onset_out_of_window"] == []
    assert report["invalid_split"] == []
    assert report["invalid_polarity"] == []
    assert report["s0_negative_count"] >= 1
    assert "holdout" in report["dataset_splits_present"]


def test_validator_flags_onset_outside_window_and_ungoverned_split() -> None:
    bad = [
        _gt_case("VAL-ONSET", "S3", onset="2025-01-01"),  # onset after window end
        _gt_case("VAL-SPLIT", "S3", split="train"),  # ungoverned split value
    ]
    report = validate_reference_case_library(bad)
    assert report["onset_out_of_window"] == ["VAL-ONSET"]
    assert report["invalid_split"] == ["VAL-SPLIT"]
    assert report["is_valid"] is False


def test_validation_event_set_is_consistent_with_the_ap27_label_library() -> None:
    # AP-29 / StR-689..691: every event-set pair references AP-27 labels, escalation is a
    # positive case matched with an S0-negative control, and assigned_sources is a subset of
    # the referenced case's reference_sources.
    import yaml

    repo_root = Path(__file__).resolve().parents[2]
    event_set = yaml.safe_load(
        (repo_root / "vmodel" / "verification" / "validation_event_set.yaml").read_text(encoding="utf-8")
    )
    cases = {case.case_id: case for case in load_validation_case_library(repo_root.joinpath(*_REFERENCE_CASES_PATH))}

    pairs = event_set["event_pairs"]
    assert pairs, "event set must define at least one matched escalation/control pair"
    for pair in pairs:
        escalation, control = pair["escalation"], pair["control"]
        assert escalation["case_id"] in cases, escalation["case_id"]
        assert control["case_id"] in cases, control["case_id"]
        esc_case, ctrl_case = cases[escalation["case_id"]], cases[control["case_id"]]
        assert esc_case.case_polarity == "positive"
        assert ctrl_case.case_polarity == "negative"
        assert ctrl_case.expected_status == "S0"  # StR-691: controls are S0 negatives
        assert set(escalation["assigned_sources"]) <= set(esc_case.reference_sources)
        assert set(control["assigned_sources"]) <= set(ctrl_case.reference_sources)


def test_validator_anti_circularity_flags_positive_but_exempts_negative() -> None:
    cases = [
        _gt_case("VAL-CIRC", "S3", historical="S3"),  # positive, historical == expected -> circular
        _gt_case("VAL-NEG", "S0", polarity="negative", historical="S0"),  # negative -> exempt
        _gt_case("VAL-INDEP", "S3", historical="S1"),  # positive, independent -> not circular
    ]
    report = validate_reference_case_library(cases)
    assert report["circular_label_case_ids"] == ["VAL-CIRC"]
    # circular labels are a quality signal, not a structural failure
    assert report["is_valid"] is True
