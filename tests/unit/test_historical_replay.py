from pathlib import Path

from siasa.validation.cases import ValidationCase, load_validation_case_library
from siasa.data.normalized_models import NormalizedRecord
from siasa.validation.historical_replay import (
    HistoricalReplayInput,
    _records_as_of,
    _replay_window_dates,
    build_historical_replay_reviews,
    derive_country_replay_status_timeseries,
    load_historical_replay_inputs,
)



def test_load_historical_replay_inputs_reads_fixture_backed_cases_from_repo_yaml() -> None:
    replay_inputs = load_historical_replay_inputs(
        Path(__file__).resolve().parents[2] / "vmodel" / "verification" / "validation_replay_inputs.yaml"
    )

    assert sorted(replay_inputs) == [
        "VAL-CAN-2024-CHALLENGE-001",
        "VAL-CHE-2024-CHALLENGE-001",
        "VAL-CHN-2024-001",
        "VAL-CHN-2024-CHALLENGE-001",
        "VAL-DEU-2024-001",
        "VAL-DEU-2024-CHALLENGE-001",
        "VAL-EGY-2024-001",
        "VAL-EGY-2024-CHALLENGE-001",
        "VAL-EST-2024-001",
        "VAL-FIN-2024-001",
        "VAL-GEO-2023-CHALLENGE-001",
        "VAL-GEO-2024-001",
        "VAL-IND-2024-001",
        "VAL-IRN-2023-CHALLENGE-001",
        "VAL-IRN-2024-001",
        "VAL-ISR-2023-001",
        "VAL-ISR-2024-002",
        "VAL-MMR-2024-001",
        "VAL-NGA-2024-001",
        "VAL-NLD-2024-CHALLENGE-001",
        "VAL-PAK-2024-001",
        "VAL-PAK-2024-CHALLENGE-001",
        "VAL-POL-2023-001",
        "VAL-POL-2024-002",
        "VAL-QAT-2024-001",
        "VAL-RUS-2024-001",
        "VAL-RUS-2024-CHALLENGE-001",
        "VAL-SAU-2024-001",
        "VAL-SDN-2024-001",
        "VAL-TUR-2024-001",
        "VAL-TWN-2024-001",
        "VAL-UKR-2022-001",
        "VAL-UKR-2023-CHALLENGE-001",
        "VAL-USA-2024-001",
        "VAL-USA-2024-CHALLENGE-001",
    ]
    assert replay_inputs["VAL-UKR-2022-001"].review_basis == "fixture_backed_historical_replay"
    assert len(replay_inputs["VAL-UKR-2022-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-RUS-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-CHN-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-IND-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-IRN-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-USA-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-DEU-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-EST-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-FIN-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-SAU-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-QAT-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-EGY-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-NGA-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-SDN-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-MMR-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-ISR-2023-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-PAK-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-GEO-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-TUR-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-TWN-2024-001"].normalized_records) == 4



def test_build_historical_replay_reviews_executes_replay_against_fixture_backed_inputs() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    cases = load_validation_case_library(repo_root / "vmodel" / "verification" / "validation_reference_cases.yaml")
    replay_inputs = load_historical_replay_inputs(repo_root / "vmodel" / "verification" / "validation_replay_inputs.yaml")

    reviews = build_historical_replay_reviews(cases, replay_inputs)

    # AP-26 adds status_timeseries additively; this legacy assertion pins the
    # pre-existing review fields, so strip the new keys before comparing.
    reviews = [
        {key: value for key, value in review.items() if key not in {"status_timeseries", "status_timeseries_degradations"}}
        for review in reviews
    ]
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
            "case_id": "VAL-IND-2024-001",
            "country_id": "IND",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["IND"],
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
            "case_id": "VAL-IRN-2024-001",
            "country_id": "IRN",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["IRN"],
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
            "case_id": "VAL-TUR-2024-001",
            "country_id": "TUR",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["TUR"],
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
            "case_id": "VAL-USA-2024-001",
            "country_id": "USA",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["USA"],
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
            "case_id": "VAL-DEU-2024-001",
            "country_id": "DEU",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["DEU"],
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
            "case_id": "VAL-EST-2024-001",
            "country_id": "EST",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["EST"],
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
            "case_id": "VAL-FIN-2024-001",
            "country_id": "FIN",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["FIN"],
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
            "case_id": "VAL-SAU-2024-001",
            "country_id": "SAU",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["SAU"],
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
            "case_id": "VAL-QAT-2024-001",
            "country_id": "QAT",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["QAT"],
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
            "case_id": "VAL-EGY-2024-001",
            "country_id": "EGY",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["EGY"],
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
            "case_id": "VAL-NGA-2024-001",
            "country_id": "NGA",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["NGA"],
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
            "case_id": "VAL-SDN-2024-001",
            "country_id": "SDN",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["SDN"],
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
            "case_id": "VAL-MMR-2024-001",
            "country_id": "MMR",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["MMR"],
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
        # --- Challenge cases (3 new non-perfect replay scenarios) ---
        {
            "case_id": "VAL-UKR-2023-CHALLENGE-001",
            "country_id": "UKR",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDELT-DOC"],
            "replay_input_country_ids": ["UKR"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 0.25,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 0.25,
            "replay_evidence_tier": "weak_replay_evidence",
            "replayed_status": "S1",
            "expected_status": "S2",
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
            "case_id": "VAL-IRN-2023-CHALLENGE-001",
            "country_id": "IRN",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS"],
            "replay_input_country_ids": ["IRN"],
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
            "replay_input_record_count": 4,
        },
        {
            "case_id": "VAL-GEO-2023-CHALLENGE-001",
            "country_id": "GEO",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDELT-DOC"],
            "replay_input_country_ids": ["GEO"],
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
            "case_id": "VAL-RUS-2024-CHALLENGE-001",
            "country_id": "RUS",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDELT-DOC"],
            "replay_input_country_ids": ["RUS"],
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
            "case_id": "VAL-CHN-2024-CHALLENGE-001",
            "country_id": "CHN",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS"],
            "replay_input_country_ids": ["CHN"],
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
            "replay_input_record_count": 4,
        },
        {
            "case_id": "VAL-PAK-2024-CHALLENGE-001",
            "country_id": "PAK",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDELT-DOC"],
            "replay_input_country_ids": ["PAK"],
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
            "case_id": "VAL-USA-2024-CHALLENGE-001",
            "country_id": "USA",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDELT-DOC"],
            "replay_input_country_ids": ["USA"],
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
            "case_id": "VAL-DEU-2024-CHALLENGE-001",
            "country_id": "DEU",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS"],
            "replay_input_country_ids": ["DEU"],
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
            "replay_input_record_count": 4,
        },
        {
            "case_id": "VAL-EGY-2024-CHALLENGE-001",
            "country_id": "EGY",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDELT-DOC"],
            "replay_input_country_ids": ["EGY"],
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
            "case_id": "VAL-CHE-2024-CHALLENGE-001",
            "country_id": "CHE",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["CHE"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 1.0,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 0.6,
            "replay_evidence_tier": "partial_replay_evidence",
            "replayed_status": "S3",
            "expected_status": "S1",
            "status_match": False,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A", "B", "D"],
            "domain_match_ratio": 1.0,
            "review_verdict": "replay_mismatch",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 8,
        },
        {
            "case_id": "VAL-NLD-2024-CHALLENGE-001",
            "country_id": "NLD",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["NLD"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 1.0,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 0.6,
            "replay_evidence_tier": "partial_replay_evidence",
            "replayed_status": "S3",
            "expected_status": "S1",
            "status_match": False,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A", "B", "D"],
            "domain_match_ratio": 1.0,
            "review_verdict": "replay_mismatch",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 8,
        },
        {
            "case_id": "VAL-CAN-2024-CHALLENGE-001",
            "country_id": "CAN",
            "review_basis": "fixture_backed_historical_replay",
            "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
            "replay_input_country_ids": ["CAN"],
            "archival_data_files": [],
            "provenance_notes": "",
            "replay_known_limitations": [],
            "replay_source_coverage_ratio": 1.0,
            "replay_provenance_completeness_ratio": 1.0,
            "replay_evidence_score": 0.6,
            "replay_evidence_tier": "partial_replay_evidence",
            "replayed_status": "S3",
            "expected_status": "S1",
            "status_match": False,
            "expected_domains": ["A", "B", "D"],
            "replayed_domains": ["A", "B", "D"],
            "domain_match_ratio": 1.0,
            "review_verdict": "replay_mismatch",
            "missing_expected_domains": [],
            "unexpected_observed_domains": [],
            "replay_input_record_count": 8,
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


def test_challenge_cases_produce_correct_non_perfect_verdicts_and_attention_routing() -> None:
    """Challenge cases must produce mismatch/gap verdicts and route to attention-level handling."""
    from siasa.readmodels.validation_backtest import build_historical_replay_summary

    repo_root = Path(__file__).resolve().parents[2]
    cases = load_validation_case_library(
        repo_root / "vmodel" / "verification" / "validation_reference_cases.yaml"
    )
    replay_inputs = load_historical_replay_inputs(
        repo_root / "vmodel" / "verification" / "validation_replay_inputs.yaml"
    )
    reviews = build_historical_replay_reviews(cases, replay_inputs)

    # Index by case_id for easy lookup
    by_id = {r["case_id"]: r for r in reviews}

    # VAL-UKR-2023-CHALLENGE-001: replay_mismatch, weak evidence
    ukr = by_id["VAL-UKR-2023-CHALLENGE-001"]
    assert ukr["review_verdict"] == "replay_mismatch"
    assert ukr["status_match"] is False
    assert ukr["replay_evidence_tier"] == "weak_replay_evidence"
    assert "B" in ukr["missing_expected_domains"]
    assert "D" in ukr["missing_expected_domains"]
    assert ukr["replayed_domains"] == ["A"]

    # VAL-IRN-2023-CHALLENGE-001: replay_match_with_gaps (status match, D missing)
    irn = by_id["VAL-IRN-2023-CHALLENGE-001"]
    assert irn["review_verdict"] == "replay_match_with_gaps"
    assert irn["status_match"] is True
    assert "D" in irn["missing_expected_domains"]
    assert irn["replay_evidence_score"] >= 0.75  # strong despite domain gap

    # VAL-GEO-2023-CHALLENGE-001: replay_mismatch, weak evidence, only A domain
    geo = by_id["VAL-GEO-2023-CHALLENGE-001"]
    assert geo["review_verdict"] == "replay_mismatch"
    assert geo["status_match"] is False
    assert geo["replay_evidence_tier"] == "weak_replay_evidence"
    assert geo["replayed_domains"] == ["A"]

    # VAL-RUS-2024-CHALLENGE-001: replay_mismatch, weak evidence, only A domain
    rus = by_id["VAL-RUS-2024-CHALLENGE-001"]
    assert rus["review_verdict"] == "replay_mismatch"
    assert rus["status_match"] is False
    assert rus["replay_evidence_tier"] == "weak_replay_evidence"
    assert rus["replayed_domains"] == ["A"]
    assert "B" in rus["missing_expected_domains"]
    assert "D" in rus["missing_expected_domains"]

    # VAL-CHN-2024-CHALLENGE-001: replay_match_with_gaps (status match, D missing)
    chn = by_id["VAL-CHN-2024-CHALLENGE-001"]
    assert chn["review_verdict"] == "replay_match_with_gaps"
    assert chn["status_match"] is True
    assert "D" in chn["missing_expected_domains"]
    assert chn["replay_evidence_score"] >= 0.75

    # VAL-PAK-2024-CHALLENGE-001: replay_mismatch, weak evidence, only A domain
    pak = by_id["VAL-PAK-2024-CHALLENGE-001"]
    assert pak["review_verdict"] == "replay_mismatch"
    assert pak["status_match"] is False
    assert pak["replay_evidence_tier"] == "weak_replay_evidence"
    assert pak["replayed_domains"] == ["A"]
    assert "B" in pak["missing_expected_domains"]
    assert "D" in pak["missing_expected_domains"]

    # VAL-USA-2024-CHALLENGE-001: replay_mismatch, weak evidence, only A domain
    usa = by_id["VAL-USA-2024-CHALLENGE-001"]
    assert usa["review_verdict"] == "replay_mismatch"
    assert usa["status_match"] is False
    assert usa["replay_evidence_tier"] == "weak_replay_evidence"
    assert usa["replayed_domains"] == ["A"]
    assert "B" in usa["missing_expected_domains"]
    assert "D" in usa["missing_expected_domains"]

    # VAL-DEU-2024-CHALLENGE-001: replay_match_with_gaps (status match, D missing)
    deu = by_id["VAL-DEU-2024-CHALLENGE-001"]
    assert deu["review_verdict"] == "replay_match_with_gaps"
    assert deu["status_match"] is True
    assert "D" in deu["missing_expected_domains"]
    assert deu["replay_evidence_score"] >= 0.75

    # VAL-EGY-2024-CHALLENGE-001: replay_mismatch, weak evidence, only A domain
    egy = by_id["VAL-EGY-2024-CHALLENGE-001"]
    assert egy["review_verdict"] == "replay_mismatch"
    assert egy["status_match"] is False
    assert egy["replay_evidence_tier"] == "weak_replay_evidence"
    assert egy["replayed_domains"] == ["A"]
    assert "B" in egy["missing_expected_domains"]
    assert "D" in egy["missing_expected_domains"]

    # New overcall challenge archetype: full-domain replay escalates above bounded reference expectation
    che = by_id["VAL-CHE-2024-CHALLENGE-001"]
    assert che["review_verdict"] == "replay_mismatch"
    assert che["status_match"] is False
    assert che["replay_evidence_tier"] == "partial_replay_evidence"
    assert che["replayed_domains"] == ["A", "B", "D"]
    assert che["expected_status"] == "S1"
    assert che["replayed_status"] == "S3"
    assert che["missing_expected_domains"] == []

    nld = by_id["VAL-NLD-2024-CHALLENGE-001"]
    assert nld["review_verdict"] == "replay_mismatch"
    assert nld["status_match"] is False
    assert nld["replay_evidence_tier"] == "partial_replay_evidence"
    assert nld["replayed_domains"] == ["A", "B", "D"]

    can = by_id["VAL-CAN-2024-CHALLENGE-001"]
    assert can["review_verdict"] == "replay_mismatch"
    assert can["status_match"] is False
    assert can["replay_evidence_tier"] == "partial_replay_evidence"
    assert can["replayed_domains"] == ["A", "B", "D"]

    # Summary must reflect non-perfect verdict mix
    summary = build_historical_replay_summary(reviews)
    verdict_counts = summary["review_verdict_counts"]
    assert verdict_counts.get("replay_mismatch", 0) >= 5, "Expected expanded mismatch coverage including overcall cases"
    assert verdict_counts.get("replay_match_with_gaps", 0) >= 1, "At least 1 match_with_gaps expected"

    # Attention cases must include all 12 challenge cases / non-perfect challenge slices
    attention_cases = summary.get("attention_cases", [])
    attention_ids = {a["case_id"] for a in attention_cases}
    assert "VAL-UKR-2023-CHALLENGE-001" in attention_ids
    assert "VAL-IRN-2023-CHALLENGE-001" in attention_ids
    assert "VAL-GEO-2023-CHALLENGE-001" in attention_ids
    assert "VAL-RUS-2024-CHALLENGE-001" in attention_ids
    assert "VAL-CHN-2024-CHALLENGE-001" in attention_ids
    assert "VAL-PAK-2024-CHALLENGE-001" in attention_ids
    assert "VAL-USA-2024-CHALLENGE-001" in attention_ids
    assert "VAL-DEU-2024-CHALLENGE-001" in attention_ids
    assert "VAL-EGY-2024-CHALLENGE-001" in attention_ids
    assert "VAL-CHE-2024-CHALLENGE-001" in attention_ids
    assert "VAL-NLD-2024-CHALLENGE-001" in attention_ids
    assert "VAL-CAN-2024-CHALLENGE-001" in attention_ids

    # High-attention cases: mismatch cases including the new overcall subtype
    high_attention = [a for a in attention_cases if a["attention_level"] == "high"]
    high_ids = {a["case_id"] for a in high_attention}
    assert "VAL-UKR-2023-CHALLENGE-001" in high_ids
    assert "VAL-GEO-2023-CHALLENGE-001" in high_ids
    assert "VAL-RUS-2024-CHALLENGE-001" in high_ids
    assert "VAL-PAK-2024-CHALLENGE-001" in high_ids
    assert "VAL-USA-2024-CHALLENGE-001" in high_ids
    assert "VAL-EGY-2024-CHALLENGE-001" in high_ids
    assert "VAL-CHE-2024-CHALLENGE-001" in high_ids
    assert "VAL-NLD-2024-CHALLENGE-001" in high_ids
    assert "VAL-CAN-2024-CHALLENGE-001" in high_ids


def _b_record(signal_key: str, value: float, day: int, *, country: str = "AAA", source: str = "SRC-B") -> NormalizedRecord:
    return NormalizedRecord(
        normalized_id=f"{signal_key}-{day}",
        country_id=country,
        timestamp=f"2026-01-{day:02d}T00:00:00Z",
        domain="B",
        signal_key=signal_key,
        value=float(value),
        provenance_source_id=source,
        quality_context={"expected_source_count": 1},
    )


def test_replay_window_dates_enumerates_inclusive_daily_range() -> None:
    assert _replay_window_dates("2026-01-01", "2026-01-03") == ["2026-01-01", "2026-01-02", "2026-01-03"]
    assert _replay_window_dates("2026-01-05", "2026-01-05") == ["2026-01-05"]
    assert _replay_window_dates("2026-01-05", "2026-01-01") == []  # start after end
    assert _replay_window_dates("", "2026-01-01") == []  # invalid input


def test_records_as_of_cuts_point_in_time_without_look_ahead() -> None:
    records = [_b_record("conflict_event_count", 10, day) for day in (1, 2, 5)]
    as_of = _records_as_of(records, "2026-01-02")
    assert [r.normalized_id for r in as_of] == ["conflict_event_count-1", "conflict_event_count-2"]
    assert all(str(r.timestamp)[:10] <= "2026-01-02" for r in as_of)  # no look-ahead


def test_replay_status_timeseries_is_per_day_deterministic_and_varies_with_input() -> None:
    records = (
        [_b_record("conflict_event_count", 10, day) for day in range(1, 6)]
        + [_b_record("conflict_event_count", 80, 6)]
        + [_b_record("protest_event_count", 5, day) for day in range(1, 7)]
    )
    result = derive_country_replay_status_timeseries(records, "AAA", "2026-01-01", "2026-01-06")
    timeseries = result["timeseries"]
    assert [entry["date"] for entry in timeseries] == [f"2026-01-0{day}" for day in range(1, 7)]
    assert all(set(entry) == {"date", "status", "confidence"} for entry in timeseries)
    # acceptance 1: varying input -> the status changes traceably across the window
    assert len({entry["status"] for entry in timeseries}) >= 2
    assert result["degradations"] == []
    # acceptance 2: two identical runs produce bit-identical timeseries
    assert derive_country_replay_status_timeseries(records, "AAA", "2026-01-01", "2026-01-06") == result


def test_replay_status_timeseries_records_explicit_degradation_on_exception(monkeypatch) -> None:
    import siasa.validation.historical_replay as historical_replay

    def _boom(*args, **kwargs):
        raise ValueError("forced per-day failure")

    monkeypatch.setattr(historical_replay, "_replay_status_as_of", _boom)
    records = [_b_record("conflict_event_count", 10, day) for day in range(1, 4)]
    result = derive_country_replay_status_timeseries(records, "AAA", "2026-01-01", "2026-01-02")
    # acceptance 3: a forced per-day exception is an explicit degradation entry, not a silent drop
    assert len(result["degradations"]) == 2
    entry = result["degradations"][0]
    assert entry["status"] == "degraded"
    assert entry["exception_type"] == "ValueError"
    assert entry["reason"] == "forced per-day failure"
    assert [item["date"] for item in result["timeseries"]] == ["2026-01-01", "2026-01-02"]


def test_reviews_include_additive_status_timeseries() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    cases = load_validation_case_library(repo_root / "vmodel" / "verification" / "validation_reference_cases.yaml")
    replay_inputs = load_historical_replay_inputs(repo_root / "vmodel" / "verification" / "validation_replay_inputs.yaml")
    reviews = build_historical_replay_reviews(cases, replay_inputs)
    assert reviews, "expected at least one review"
    for review in reviews:
        assert "status_timeseries" in review
        assert "status_timeseries_degradations" in review
        for entry in review["status_timeseries"]:
            assert set(entry) == {"date", "status", "confidence"}


def test_status_timeseries_artifact_is_written_deterministically(tmp_path) -> None:
    import json

    from siasa.runs.artifacts import write_status_timeseries_artifacts

    reviews = [
        {
            "case_id": "VAL-AAA-TS",
            "country_id": "AAA",
            "status_timeseries": [{"date": "2026-01-01", "status": "S0", "confidence": 1.0}],
            "status_timeseries_degradations": [],
        }
    ]
    readmodels_dir = tmp_path / "readmodels"
    readmodels_dir.mkdir()

    paths = write_status_timeseries_artifacts(readmodels_dir, reviews)
    assert len(paths) == 1
    artifact = readmodels_dir / "status_timeseries" / "status_timeseries_VAL-AAA-TS.json"
    assert artifact.exists()

    first_bytes = artifact.read_bytes()
    # SwR-087 / acceptance 2: two identical runs produce a bit-identical file
    write_status_timeseries_artifacts(readmodels_dir, reviews)
    assert artifact.read_bytes() == first_bytes

    payload = json.loads(first_bytes)
    assert payload["case_id"] == "VAL-AAA-TS"
    assert payload["status_timeseries"][0]["status"] == "S0"
    # no replay reviews -> nothing written
    assert write_status_timeseries_artifacts(readmodels_dir, None) == []
