from pathlib import Path

from siasa.validation.archival_replay import load_archival_replay_manifest, load_governed_historical_replay_inputs



def test_load_archival_replay_manifest_reads_provider_backed_case_entries() -> None:
    manifest = load_archival_replay_manifest(
        Path(__file__).resolve().parents[2] / "vmodel" / "verification" / "validation_archival_replay_manifest.yaml"
    )

    assert [entry.case_id for entry in manifest] == [
        "VAL-UKR-2022-001",
        "VAL-POL-2023-001",
    ]
    assert manifest[0].review_basis == "provider_backed_archival_replay"
    assert manifest[0].storage_mode == "archival_normalized_records"
    assert manifest[0].data_files == ["archival_replay_inputs/VAL-UKR-2022-001.json"]



def test_load_governed_historical_replay_inputs_prefers_archival_provider_backed_cases_and_falls_back_to_fixtures() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    replay_inputs = load_governed_historical_replay_inputs(repo_root)

    assert sorted(replay_inputs) == [
        "VAL-ISR-2023-001",
        "VAL-POL-2023-001",
        "VAL-TWN-2024-001",
        "VAL-UKR-2022-001",
    ]
    assert replay_inputs["VAL-UKR-2022-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-POL-2023-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-ISR-2023-001"].review_basis == "fixture_backed_historical_replay"
    assert replay_inputs["VAL-TWN-2024-001"].review_basis == "fixture_backed_historical_replay"
    assert len(replay_inputs["VAL-UKR-2022-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-POL-2023-001"].normalized_records) == 8
