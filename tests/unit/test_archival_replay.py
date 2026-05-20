from pathlib import Path

import pytest

from siasa.validation.archival_replay import load_archival_replay_manifest, load_governed_historical_replay_inputs



def test_load_archival_replay_manifest_reads_provider_backed_case_entries() -> None:
    manifest = load_archival_replay_manifest(
        Path(__file__).resolve().parents[2] / "vmodel" / "verification" / "validation_archival_replay_manifest.yaml"
    )

    assert [entry.case_id for entry in manifest] == [
        "VAL-UKR-2022-001",
        "VAL-RUS-2024-001",
        "VAL-CHN-2024-001",
        "VAL-IND-2024-001",
        "VAL-IRN-2024-001",
        "VAL-TUR-2024-001",
        "VAL-POL-2023-001",
        "VAL-POL-2024-002",
        "VAL-ISR-2023-001",
        "VAL-ISR-2024-002",
        "VAL-PAK-2024-001",
        "VAL-GEO-2024-001",
        "VAL-TWN-2024-001",
    ]
    assert manifest[0].review_basis == "provider_backed_archival_replay"
    assert manifest[0].storage_mode == "archival_normalized_records"
    assert manifest[0].data_files == ["archival_replay_inputs/VAL-UKR-2022-001.json"]
    assert manifest[0].archival_sources == ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"]
    assert manifest[0].provenance_notes
    assert manifest[0].known_limitations == [
        "provider_backed_archival_replay_uses_repo_stored_archival_inputs_not_live_backfill_at_runtime"
    ]



def test_load_archival_replay_manifest_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        """
archival_replay_cases:
  - case_id: VAL-UKR-2022-001
    review_basis: provider_backed_archival_replay
    storage_mode: archival_normalized_records
    data_files: [archival_replay_inputs/VAL-UKR-2022-001.json]
    archival_sources: [SRC-GDELT-DOC]
    provenance_notes: governed bundle
    known_limitations: [repo_stored_inputs]
  - case_id: VAL-UKR-2022-001
    review_basis: provider_backed_archival_replay
    storage_mode: archival_normalized_records
    data_files: [archival_replay_inputs/VAL-UKR-2022-001-copy.json]
    archival_sources: [SRC-GDELT-DOC]
    provenance_notes: governed bundle copy
    known_limitations: [repo_stored_inputs]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate archival replay manifest case_id=VAL-UKR-2022-001"):
        load_archival_replay_manifest(manifest_path)



def test_load_archival_replay_manifest_rejects_missing_provenance_fields(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        """
archival_replay_cases:
  - case_id: VAL-UKR-2022-001
    review_basis: provider_backed_archival_replay
    storage_mode: archival_normalized_records
    data_files: [archival_replay_inputs/VAL-UKR-2022-001.json]
    archival_sources: []
    provenance_notes: ""
    known_limitations: []
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="archival_sources are required for case_id=VAL-UKR-2022-001"):
        load_archival_replay_manifest(manifest_path)



def test_load_governed_historical_replay_inputs_prefers_archival_provider_backed_cases_for_all_curated_cases() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    replay_inputs = load_governed_historical_replay_inputs(repo_root)

    assert sorted(replay_inputs) == [
        "VAL-CHN-2024-001",
        "VAL-GEO-2024-001",
        "VAL-IND-2024-001",
        "VAL-IRN-2024-001",
        "VAL-ISR-2023-001",
        "VAL-ISR-2024-002",
        "VAL-PAK-2024-001",
        "VAL-POL-2023-001",
        "VAL-POL-2024-002",
        "VAL-RUS-2024-001",
        "VAL-TUR-2024-001",
        "VAL-TWN-2024-001",
        "VAL-UKR-2022-001",
    ]
    assert replay_inputs["VAL-UKR-2022-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-RUS-2024-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-CHN-2024-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-IND-2024-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-IRN-2024-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-TUR-2024-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-POL-2023-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-POL-2024-002"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-ISR-2023-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-ISR-2024-002"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-PAK-2024-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-GEO-2024-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-TWN-2024-001"].review_basis == "provider_backed_archival_replay"
    assert replay_inputs["VAL-UKR-2022-001"].replay_input_source_ids == [
        "SRC-GDACS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "WB-INDICATORS",
    ]
    assert replay_inputs["VAL-UKR-2022-001"].replay_input_country_ids == ["UKR"]
    assert replay_inputs["VAL-UKR-2022-001"].archival_data_files == [
        "archival_replay_inputs/VAL-UKR-2022-001.json"
    ]
    assert replay_inputs["VAL-UKR-2022-001"].provenance_notes
    assert len(replay_inputs["VAL-UKR-2022-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-RUS-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-CHN-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-IND-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-IRN-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-TUR-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-POL-2023-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-POL-2024-002"].normalized_records) == 5
    assert len(replay_inputs["VAL-ISR-2023-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-ISR-2024-002"].normalized_records) == 2
    assert len(replay_inputs["VAL-PAK-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-GEO-2024-001"].normalized_records) == 8
    assert len(replay_inputs["VAL-TWN-2024-001"].normalized_records) == 4
    assert replay_inputs["VAL-POL-2024-002"].replay_input_source_ids == [
        "SRC-GDACS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
    ]
    assert replay_inputs["VAL-RUS-2024-001"].replay_input_source_ids == [
        "SRC-GDACS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "WB-INDICATORS",
    ]
    assert replay_inputs["VAL-CHN-2024-001"].replay_input_source_ids == [
        "SRC-GDACS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "WB-INDICATORS",
    ]
    assert replay_inputs["VAL-IND-2024-001"].replay_input_source_ids == [
        "SRC-GDACS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "WB-INDICATORS",
    ]
    assert replay_inputs["VAL-IRN-2024-001"].replay_input_source_ids == [
        "SRC-GDACS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "WB-INDICATORS",
    ]
    assert replay_inputs["VAL-PAK-2024-001"].replay_input_source_ids == [
        "SRC-GDACS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "WB-INDICATORS",
    ]
    assert replay_inputs["VAL-GEO-2024-001"].replay_input_source_ids == [
        "SRC-GDACS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "WB-INDICATORS",
    ]
    assert replay_inputs["VAL-TUR-2024-001"].replay_input_source_ids == [
        "SRC-GDACS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "WB-INDICATORS",
    ]
    assert replay_inputs["VAL-ISR-2024-002"].replay_input_source_ids == ["SRC-GDELT-DOC"]



def test_load_governed_historical_replay_inputs_rejects_archival_bundle_country_mismatch(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "vmodel" / "verification" / "archival_replay_inputs").mkdir(parents=True)
    (repo_root / "vmodel" / "verification" / "validation_replay_inputs.yaml").write_text(
        "replay_cases: []\n",
        encoding="utf-8",
    )
    (repo_root / "vmodel" / "verification" / "validation_reference_cases.yaml").write_text(
        """
validation_cases:
  - case_id: VAL-UKR-2022-001
    country_id: UKR
    case_name: Escalation reference case
    case_type: military_escalation
    time_start: "2022-02-01"
    time_end: "2022-03-01"
    expected_domains: [A, B, D]
    expected_status: S3
    expected_signal_pattern: test
    reference_sources: [SRC-GDELT-DOC, SRC-GDELT-EVENTS, WB-INDICATORS]
    validation_goal: test
    known_limitations: [test]
    validation_metrics: [Domain Match]
""".strip(),
        encoding="utf-8",
    )
    (repo_root / "vmodel" / "verification" / "validation_archival_replay_manifest.yaml").write_text(
        """
archival_replay_cases:
  - case_id: VAL-UKR-2022-001
    review_basis: provider_backed_archival_replay
    storage_mode: archival_normalized_records
    data_files: [archival_replay_inputs/VAL-UKR-2022-001.json]
    archival_sources: [SRC-GDELT-DOC]
    provenance_notes: governed bundle
    known_limitations: [repo_stored_inputs]
""".strip(),
        encoding="utf-8",
    )
    (repo_root / "vmodel" / "verification" / "archival_replay_inputs" / "VAL-UKR-2022-001.json").write_text(
        """
{
  "normalized_records": [
    {
      "country_id": "POL",
      "timestamp": "2022-02-24T08:00:00Z",
      "domain": "A",
      "signal_key": "article_count",
      "value": 12,
      "provenance_source_id": "SRC-GDELT-DOC",
      "quality_context": {"freshness_hours": 6}
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="country mismatch for case_id=VAL-UKR-2022-001"):
        load_governed_historical_replay_inputs(repo_root)



def test_load_governed_historical_replay_inputs_rejects_archival_source_manifest_mismatch(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "vmodel" / "verification" / "archival_replay_inputs").mkdir(parents=True)
    (repo_root / "vmodel" / "verification" / "validation_replay_inputs.yaml").write_text(
        "replay_cases: []\n",
        encoding="utf-8",
    )
    (repo_root / "vmodel" / "verification" / "validation_reference_cases.yaml").write_text(
        """
validation_cases:
  - case_id: VAL-UKR-2022-001
    country_id: UKR
    case_name: Escalation reference case
    case_type: military_escalation
    time_start: "2022-02-01"
    time_end: "2022-03-01"
    expected_domains: [A, B, D]
    expected_status: S3
    expected_signal_pattern: test
    reference_sources: [SRC-GDELT-DOC, SRC-GDELT-EVENTS]
    validation_goal: test
    known_limitations: [test]
    validation_metrics: [Domain Match]
""".strip(),
        encoding="utf-8",
    )
    (repo_root / "vmodel" / "verification" / "validation_archival_replay_manifest.yaml").write_text(
        """
archival_replay_cases:
  - case_id: VAL-UKR-2022-001
    review_basis: provider_backed_archival_replay
    storage_mode: archival_normalized_records
    data_files: [archival_replay_inputs/VAL-UKR-2022-001.json]
    archival_sources: [SRC-GDELT-DOC, SRC-GDELT-EVENTS]
    provenance_notes: governed bundle
    known_limitations: [repo_stored_inputs]
""".strip(),
        encoding="utf-8",
    )
    (repo_root / "vmodel" / "verification" / "archival_replay_inputs" / "VAL-UKR-2022-001.json").write_text(
        """
{
  "normalized_records": [
    {
      "country_id": "UKR",
      "timestamp": "2022-02-24T08:00:00Z",
      "domain": "A",
      "signal_key": "article_count",
      "value": 12,
      "provenance_source_id": "SRC-GDELT-DOC",
      "quality_context": {"freshness_hours": 6}
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="source mismatch for case_id=VAL-UKR-2022-001"):
        load_governed_historical_replay_inputs(repo_root)



def test_load_governed_historical_replay_inputs_allows_archival_sources_to_be_a_reference_source_subset(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "vmodel" / "verification" / "archival_replay_inputs").mkdir(parents=True)
    (repo_root / "vmodel" / "verification" / "validation_replay_inputs.yaml").write_text(
        "replay_cases: []\n",
        encoding="utf-8",
    )
    (repo_root / "vmodel" / "verification" / "validation_reference_cases.yaml").write_text(
        """
validation_cases:
  - case_id: VAL-UKR-2022-001
    country_id: UKR
    case_name: Escalation reference case
    case_type: military_escalation
    time_start: "2022-02-01"
    time_end: "2022-03-01"
    expected_domains: [A, B, D]
    expected_status: S3
    expected_signal_pattern: test
    reference_sources: [SRC-GDELT-DOC, SRC-GDELT-EVENTS, WB-INDICATORS]
    validation_goal: test
    known_limitations: [test]
    validation_metrics: [Domain Match]
""".strip(),
        encoding="utf-8",
    )
    (repo_root / "vmodel" / "verification" / "validation_archival_replay_manifest.yaml").write_text(
        """
archival_replay_cases:
  - case_id: VAL-UKR-2022-001
    review_basis: provider_backed_archival_replay
    storage_mode: archival_normalized_records
    data_files: [archival_replay_inputs/VAL-UKR-2022-001.json]
    archival_sources: [SRC-GDELT-DOC, SRC-GDELT-EVENTS]
    provenance_notes: governed bundle
    known_limitations: [repo_stored_inputs]
""".strip(),
        encoding="utf-8",
    )
    (repo_root / "vmodel" / "verification" / "archival_replay_inputs" / "VAL-UKR-2022-001.json").write_text(
        """
{
  "normalized_records": [
    {
      "country_id": "UKR",
      "timestamp": "2022-02-24T08:00:00Z",
      "domain": "A",
      "signal_key": "article_count",
      "value": 12,
      "provenance_source_id": "SRC-GDELT-DOC",
      "quality_context": {"freshness_hours": 6}
    },
    {
      "country_id": "UKR",
      "timestamp": "2022-02-24T09:00:00Z",
      "domain": "B",
      "signal_key": "conflict_event_count",
      "value": 4,
      "provenance_source_id": "SRC-GDELT-EVENTS",
      "quality_context": {"freshness_hours": 5}
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    replay_inputs = load_governed_historical_replay_inputs(repo_root)

    assert replay_inputs["VAL-UKR-2022-001"].replay_input_source_ids == [
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
    ]
