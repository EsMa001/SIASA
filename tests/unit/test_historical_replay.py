from pathlib import Path

from siasa.validation.cases import load_validation_case_library
from siasa.validation.historical_replay import build_historical_replay_reviews, load_historical_replay_inputs



def test_load_historical_replay_inputs_reads_fixture_backed_cases_from_repo_yaml() -> None:
    replay_inputs = load_historical_replay_inputs(
        Path(__file__).resolve().parents[2] / "vmodel" / "verification" / "validation_replay_inputs.yaml"
    )

    assert sorted(replay_inputs) == ["VAL-POL-2023-001", "VAL-UKR-2022-001"]
    assert replay_inputs["VAL-UKR-2022-001"].review_basis == "fixture_backed_historical_replay"
    assert len(replay_inputs["VAL-UKR-2022-001"].normalized_records) == 8



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
    ]
