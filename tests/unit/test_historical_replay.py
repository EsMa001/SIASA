from pathlib import Path

from siasa.validation.cases import ValidationCase, load_validation_case_library
from siasa.validation.historical_replay import HistoricalReplayInput, build_historical_replay_reviews, load_historical_replay_inputs



def test_load_historical_replay_inputs_reads_fixture_backed_cases_from_repo_yaml() -> None:
    replay_inputs = load_historical_replay_inputs(
        Path(__file__).resolve().parents[2] / "vmodel" / "verification" / "validation_replay_inputs.yaml"
    )

    assert sorted(replay_inputs) == [
        "VAL-CHN-2024-001",
        "VAL-GEO-2024-001",
        "VAL-ISR-2023-001",
        "VAL-ISR-2024-002",
        "VAL-PAK-2024-001",
        "VAL-POL-2023-001",
        "VAL-POL-2024-002",
        "VAL-RUS-2024-001",
        "VAL-TWN-2024-001",
        "VAL-UKR-2022-001",
    ]
    assert replay_inputs["VAL-UKR-2022-001"].review_basis == "fixture_backed_historical_replay"
    assert len(replay_inputs["VAL-UKR-2022-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-RUS-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-CHN-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-ISR-2023-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-PAK-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-GEO-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-TWN-2024-001"].normalized_records) == 4



def test_build_historical_replay_reviews_executes_replay_against_fixture_backed_inputs() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    cases = load_validation_case_library(repo_root / "vmodel" / "verification" / "validation_reference_cases.yaml")
    replay_inputs = load_historical_replay_inputs(repo_root / "vmodel" / "verification" / "validation_replay_inputs.yaml")

    reviews = build_historical_replay_reviews(cases, replay_inputs)

    assert reviews == [
        {
            "case_id": "VAL-UKR-2022-001",
            "country_id": "UKR",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["UKR"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 1.0,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 1.0,
            "replay_evidence_tier": "verified_replay_evidence",
            "replayed_status": "S3",
            "expected_status": "S3",
            "status_match": True,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A", "B", "D"],
            "domain_match_ratio": 1.0,
            "review_verdict": "replay_match",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 8,
        },
        {
            "case_id": "VAL-RUS-2024-001",
            "country_id": "RUS",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["RUS"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 1.0,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 1.0,
            "replay_evidence_tier": "verified_replay_evidence",
            "replayed_status": "S3",
            "expected_status": "S3",
            "status_match": True,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A", "B", "D"],
            "domain_match_ratio": 1.0,
            "review_verdict": "replay_match",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 8,
        },
        {
            "case_id": "VAL-CHN-2024-001",
            "country_id": "CHN",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["CHN"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 1.0,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 1.0,
            "replay_evidence_tier": "verified_replay_evidence",
            "replayed_status": "S3",
            "expected_status": "S3",
            "status_match": True,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A", "B", "D"],
            "domain_match_ratio": 1.0,
            "review_verdict": "replay_match",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 8,
        },
        {
            "case_id": "VAL-POL-2023-001",
            "country_id": "POL",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["POL"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 1.0,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 1.0,
            "replay_evidence_tier": "verified_replay_evidence",
            "replayed_status": "S3",
            "expected_status": "S3",
            "status_match": True,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A", "B", "D"],
            "domain_match_ratio": 1.0,
            "review_verdict": "replay_match",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 8,
        },
        {
            "case_id": "VAL-POL-2024-002",
            "country_id": "POL",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS"],
            "replay_input_country_ids": ["POL"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 0.75,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 0.85,
            "replay_evidence_tier": "strong_replay_evidence",
            "replayed_status": "S3",
            "expected_status": "S3",
            "status_match": True,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A", "B"],
            "domain_match_ratio": 2 / 3,
            "review_verdict": "replay_match_with_gaps",
            "missing_expected_domains": ["D"],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 5,
        },
        {
            "case_id": "VAL-ISR-2023-001",
            "country_id": "ISR",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["ISR"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 1.0,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 1.0,
            "replay_evidence_tier": "verified_replay_evidence",
            "replayed_status": "S3",
            "expected_status": "S3",
            "status_match": True,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A", "B", "D"],
            "domain_match_ratio": 1.0,
            "review_verdict": "replay_match",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 8,
        },
        {
            "case_id": "VAL-ISR-2024-002",
            "country_id": "ISR",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDELT-DOC"],
            "replay_input_country_ids": ["ISR"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 0.25,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 0.25,
            "replay_evidence_tier": "weak_replay_evidence",
            "replayed_status": "S1",
            "expected_status": "S3",
            "status_match": False,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A"],
            "domain_match_ratio": 1 / 3,
            "review_verdict": "replay_mismatch",
            "missing_expected_domains": ["B", "D"],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 2,
        },
        {
            "case_id": "VAL-PAK-2024-001",
            "country_id": "PAK",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["PAK"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 1.0,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 1.0,
            "replay_evidence_tier": "verified_replay_evidence",
            "replayed_status": "S3",
            "expected_status": "S3",
            "status_match": True,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A", "B", "D"],
            "domain_match_ratio": 1.0,
            "review_verdict": "replay_match",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 8,
        },
        {
            "case_id": "VAL-GEO-2024-001",
            "country_id": "GEO",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["GEO"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 1.0,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 1.0,
            "replay_evidence_tier": "verified_replay_evidence",
            "replayed_status": "S3",
            "expected_status": "S3",
            "status_match": True,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A", "B", "D"],
            "domain_match_ratio": 1.0,
            "review_verdict": "replay_match",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 8,
        },
        {
            "case_id": "VAL-TWN-2024-001",
            "country_id": "TWN",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS"],
            "replay_input_country_ids": ["TWN"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 1.0,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 1.0,
            "replay_evidence_tier": "verified_replay_evidence",
            "replayed_status": "S1",
            "expected_status": "S1",
            "status_match": True,
            "expected_domains": ["A", "B"],
            "replayed_domains": ["A", "B"],
            "domain_match_ratio": 1.0,
            "review_verdict": "replay_match",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 4,
        },
    ]



def test_build_historical_replay_reviews_assigns_lower_evidence_tier_when_replay_has_domain_and_source_gaps() -> None:
    case = ValidationCase(
        case_id="VAL-TST-001",
        country_id="TWN",
        case_name="Synthetic replay quality case",
        case_type="synthetic",
        time_start="2024-01-01",
        time_end="2024-01-31",
        expected_domains=["A", "B"],
        expected_status="S1",
        expected_signal_pattern="Synthetic pattern",
        reference_sources=["SRC-GDELT-DOC", "SRC-GDELT-EVENTS"],
        validation_goal="Exercise replay evidence scoring.",
        known_limitations=["synthetic_test_case"],
        validation_metrics=["Domain Match", "Status Match"],
    )
    base_input = load_historical_replay_inputs(
        Path(__file__).resolve().parents[2] / "vmodel" / "verification" / "validation_replay_inputs.yaml"
    )["VAL-TWN-2024-001"]
    replay_inputs = {
        "VAL-TST-001": HistoricalReplayInput(
            case_id="VAL-TST-001",
            review_basis="fixture_backed_historical_replay",
            normalized_records=base_input.normalized_records[:2],
            replay_input_source_ids=["SRC-GDELT-DOC"],
            replay_input_country_ids=["TWN"],
        )
    }

    reviews = build_historical_replay_reviews([case], replay_inputs)

    assert reviews[0]["review_verdict"] == "replay_match_with_gaps"
    assert reviews[0]["replay_source_coverage_ratio"] == 0.5
    assert reviews[0]["replay_provenance_completeness_ratio"] == 1.0
    assert reviews[0]["replay_evidence_score"] == 0.75
    assert reviews[0]["replay_evidence_tier"] == "strong_replay_evidence"
