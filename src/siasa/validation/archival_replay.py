from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import yaml

from siasa.data.normalized_models import NormalizedRecord
from siasa.validation.historical_replay import HistoricalReplayInput, load_historical_replay_inputs


@dataclass(frozen=True)
class ArchivalReplayManifestEntry:
    case_id: str
    review_basis: str
    storage_mode: str
    data_files: list[str]
    archival_sources: list[str]
    provenance_notes: str
    known_limitations: list[str]


_MANIFEST_PATH = Path("vmodel/verification/validation_archival_replay_manifest.yaml")
_FIXTURE_REPLAY_INPUTS_PATH = Path("vmodel/verification/validation_replay_inputs.yaml")



def load_archival_replay_manifest(path: Path) -> list[ArchivalReplayManifestEntry]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    case_records = data.get("archival_replay_cases", [])
    if not isinstance(case_records, list):
        raise ValueError("archival_replay_cases must be a list")

    entries: list[ArchivalReplayManifestEntry] = []
    for record in case_records:
        if not isinstance(record, dict):
            continue
        case_id = str(record.get("case_id", "")).strip()
        if not case_id:
            raise ValueError("archival replay manifest case_id is required")
        data_files = [str(item) for item in record.get("data_files", [])]
        if not data_files:
            raise ValueError(f"archival replay manifest data_files are required for case_id={case_id}")
        entries.append(
            ArchivalReplayManifestEntry(
                case_id=case_id,
                review_basis=str(record.get("review_basis", "provider_backed_archival_replay")),
                storage_mode=str(record.get("storage_mode", "archival_normalized_records")),
                data_files=data_files,
                archival_sources=[str(item) for item in record.get("archival_sources", [])],
                provenance_notes=str(record.get("provenance_notes", "")),
                known_limitations=[str(item) for item in record.get("known_limitations", [])],
            )
        )
    return entries



def _load_archival_normalized_records(base_dir: Path, data_files: list[str]) -> list[NormalizedRecord]:
    normalized_records: list[NormalizedRecord] = []
    for relative_file in data_files:
        payload = json.loads((base_dir / relative_file).read_text(encoding="utf-8"))
        records = payload.get("normalized_records", []) if isinstance(payload, dict) else []
        if not isinstance(records, list):
            raise ValueError(f"normalized_records must be a list in archival replay file {relative_file}")
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                continue
            normalized_records.append(
                NormalizedRecord(
                    normalized_id=str(record.get("normalized_id") or f"ARCHIVE-{base_dir.name}-{index}"),
                    country_id=str(record["country_id"]),
                    timestamp=str(record.get("timestamp") or ""),
                    domain=str(record["domain"]),
                    signal_key=str(record["signal_key"]),
                    value=float(record["value"]),
                    provenance_source_id=str(record["provenance_source_id"]),
                    quality_context=dict(record.get("quality_context", {})) if isinstance(record.get("quality_context", {}), dict) else {},
                )
            )
    return normalized_records



def load_governed_historical_replay_inputs(repo_root: Path) -> dict[str, HistoricalReplayInput]:
    fixture_inputs = load_historical_replay_inputs(repo_root / _FIXTURE_REPLAY_INPUTS_PATH)
    manifest_entries = load_archival_replay_manifest(repo_root / _MANIFEST_PATH)

    governed_inputs = dict(fixture_inputs)
    for entry in manifest_entries:
        if entry.storage_mode != "archival_normalized_records":
            raise ValueError(
                f"Unsupported archival replay storage_mode={entry.storage_mode} for case_id={entry.case_id}"
            )
        normalized_records = _load_archival_normalized_records(repo_root / "vmodel/verification", entry.data_files)
        governed_inputs[entry.case_id] = HistoricalReplayInput(
            case_id=entry.case_id,
            review_basis=entry.review_basis,
            normalized_records=normalized_records,
        )
    return governed_inputs
