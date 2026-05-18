from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import yaml

from siasa.data.normalized_models import NormalizedRecord
from siasa.validation.cases import ValidationCase, load_validation_case_library
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
_REFERENCE_CASE_LIBRARY_PATH = Path("vmodel/verification/validation_reference_cases.yaml")



def load_archival_replay_manifest(path: Path) -> list[ArchivalReplayManifestEntry]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    case_records = data.get("archival_replay_cases", [])
    if not isinstance(case_records, list):
        raise ValueError("archival_replay_cases must be a list")

    entries: list[ArchivalReplayManifestEntry] = []
    seen_case_ids: set[str] = set()
    for record in case_records:
        if not isinstance(record, dict):
            continue
        case_id = str(record.get("case_id", "")).strip()
        if not case_id:
            raise ValueError("archival replay manifest case_id is required")
        if case_id in seen_case_ids:
            raise ValueError(f"duplicate archival replay manifest case_id={case_id}")
        seen_case_ids.add(case_id)

        review_basis = str(record.get("review_basis", "provider_backed_archival_replay")).strip()
        if review_basis != "provider_backed_archival_replay":
            raise ValueError(f"archival replay manifest review_basis must be provider_backed_archival_replay for case_id={case_id}")

        data_files = [str(item).strip() for item in record.get("data_files", []) if str(item).strip()]
        if not data_files:
            raise ValueError(f"archival replay manifest data_files are required for case_id={case_id}")
        if len(data_files) != len(set(data_files)):
            raise ValueError(f"duplicate archival replay manifest data_files for case_id={case_id}")

        archival_sources = sorted({str(item).strip() for item in record.get("archival_sources", []) if str(item).strip()})
        if not archival_sources:
            raise ValueError(f"archival replay manifest archival_sources are required for case_id={case_id}")

        provenance_notes = str(record.get("provenance_notes", "")).strip()
        if not provenance_notes:
            raise ValueError(f"archival replay manifest provenance_notes are required for case_id={case_id}")

        known_limitations = [str(item).strip() for item in record.get("known_limitations", []) if str(item).strip()]
        if not known_limitations:
            raise ValueError(f"archival replay manifest known_limitations are required for case_id={case_id}")

        entries.append(
            ArchivalReplayManifestEntry(
                case_id=case_id,
                review_basis=review_basis,
                storage_mode=str(record.get("storage_mode", "archival_normalized_records")),
                data_files=data_files,
                archival_sources=archival_sources,
                provenance_notes=provenance_notes,
                known_limitations=known_limitations,
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



def _reference_case_by_id(path: Path) -> dict[str, ValidationCase]:
    return {case.case_id: case for case in load_validation_case_library(path)}



def _validate_archival_replay_bundle(
    entry: ArchivalReplayManifestEntry,
    validation_case: ValidationCase,
    normalized_records: list[NormalizedRecord],
) -> tuple[list[str], list[str]]:
    reference_sources = sorted({str(source_id) for source_id in validation_case.reference_sources if str(source_id)})
    if reference_sources != entry.archival_sources:
        raise ValueError(
            f"archival replay bundle reference source mismatch for case_id={entry.case_id}: "
            f"reference_case={reference_sources} manifest={entry.archival_sources}"
        )

    if not normalized_records:
        raise ValueError(f"archival replay bundle must contain records for case_id={entry.case_id}")

    replay_input_country_ids = sorted({record.country_id for record in normalized_records if record.country_id})
    if replay_input_country_ids != [validation_case.country_id]:
        raise ValueError(
            f"archival replay bundle country mismatch for case_id={entry.case_id}: "
            f"expected={validation_case.country_id} observed={replay_input_country_ids}"
        )

    replay_input_source_ids = sorted({record.provenance_source_id for record in normalized_records if record.provenance_source_id})
    if replay_input_source_ids != entry.archival_sources:
        raise ValueError(
            f"archival replay bundle source mismatch for case_id={entry.case_id}: "
            f"manifest={entry.archival_sources} observed={replay_input_source_ids}"
        )

    return replay_input_country_ids, replay_input_source_ids



def load_governed_historical_replay_inputs(repo_root: Path) -> dict[str, HistoricalReplayInput]:
    fixture_inputs = load_historical_replay_inputs(repo_root / _FIXTURE_REPLAY_INPUTS_PATH)
    manifest_entries = load_archival_replay_manifest(repo_root / _MANIFEST_PATH)
    reference_cases_by_id = _reference_case_by_id(repo_root / _REFERENCE_CASE_LIBRARY_PATH)

    governed_inputs = dict(fixture_inputs)
    for entry in manifest_entries:
        if entry.storage_mode != "archival_normalized_records":
            raise ValueError(
                f"Unsupported archival replay storage_mode={entry.storage_mode} for case_id={entry.case_id}"
            )
        validation_case = reference_cases_by_id.get(entry.case_id)
        if validation_case is None:
            raise ValueError(f"archival replay manifest case_id={entry.case_id} not found in validation reference case library")
        normalized_records = _load_archival_normalized_records(repo_root / "vmodel/verification", entry.data_files)
        replay_input_country_ids, replay_input_source_ids = _validate_archival_replay_bundle(
            entry,
            validation_case,
            normalized_records,
        )
        governed_inputs[entry.case_id] = HistoricalReplayInput(
            case_id=entry.case_id,
            review_basis=entry.review_basis,
            normalized_records=normalized_records,
            replay_input_source_ids=replay_input_source_ids,
            replay_input_country_ids=replay_input_country_ids,
            archival_data_files=list(entry.data_files),
            provenance_notes=entry.provenance_notes,
            known_limitations=list(entry.known_limitations),
        )
    return governed_inputs
