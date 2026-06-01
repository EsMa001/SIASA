from __future__ import annotations

import json
from pathlib import Path

import pytest

from siasa.runs.latest_bundle_verification import verify_latest_bundle


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _build_minimal_latest_bundle(tmp_path: Path) -> Path:
    artifacts_dir = tmp_path / "latest"
    _write_json(artifacts_dir / "snapshot.json", {"snapshot_id": "SNAP-001"})
    _write_json(
        artifacts_dir / "readmodels/system_status.json",
        {
            "run_id": "RUN-LIVE-001",
            "run_status": "success",
            "failed_sources": [],
        },
    )
    _write_json(
        artifacts_dir / "readmodels/world_map.json",
        {
            "active_domains": ["A", "B", "C", "D", "E"],
            "countries": [{"country_id": "UKR"}],
        },
    )
    _write_json(
        artifacts_dir / "readmodels/country_profiles/UKR.json",
        {
            "country_id": "UKR",
            "domain_states": {"A": "D1", "B": "D1", "D": "D1", "E": "D0"},
        },
    )
    return artifacts_dir


def test_verify_latest_bundle_accepts_valid_bundle(tmp_path: Path) -> None:
    artifacts_dir = _build_minimal_latest_bundle(tmp_path)

    summary = verify_latest_bundle(artifacts_dir)

    assert summary["status"] == "ok"
    assert summary["run_id"] == "RUN-LIVE-001"
    assert summary["countries_with_domain_e"] == ["UKR"]


def test_verify_latest_bundle_rejects_missing_required_artifact(tmp_path: Path) -> None:
    artifacts_dir = _build_minimal_latest_bundle(tmp_path)
    (artifacts_dir / "readmodels/world_map.json").unlink()

    with pytest.raises(ValueError, match="missing required artifacts"):
        verify_latest_bundle(artifacts_dir)


def test_verify_latest_bundle_rejects_when_domain_e_absent_in_profiles(tmp_path: Path) -> None:
    artifacts_dir = _build_minimal_latest_bundle(tmp_path)
    _write_json(
        artifacts_dir / "readmodels/country_profiles/UKR.json",
        {
            "country_id": "UKR",
            "domain_states": {"A": "D1", "B": "D1", "D": "D1"},
        },
    )

    with pytest.raises(ValueError, match="no country profile with Domain E state"):
        verify_latest_bundle(artifacts_dir)


def test_verify_latest_bundle_rejects_partial_success_by_default(tmp_path: Path) -> None:
    artifacts_dir = _build_minimal_latest_bundle(tmp_path)
    _write_json(
        artifacts_dir / "readmodels/system_status.json",
        {
            "run_id": "RUN-LIVE-001",
            "run_status": "partial_success",
            "failed_sources": ["SRC-GDELT-DOC"],
        },
    )

    with pytest.raises(ValueError, match="not in allowed statuses"):
        verify_latest_bundle(artifacts_dir)


def test_verify_latest_bundle_accepts_partial_success_and_failed_sources_when_enabled(tmp_path: Path) -> None:
    artifacts_dir = _build_minimal_latest_bundle(tmp_path)
    _write_json(
        artifacts_dir / "readmodels/system_status.json",
        {
            "run_id": "RUN-LIVE-001",
            "run_status": "partial_success",
            "failed_sources": ["SRC-GDELT-DOC"],
        },
    )

    summary = verify_latest_bundle(
        artifacts_dir,
        allow_partial_success=True,
        allow_failed_sources=True,
    )

    assert summary["status"] == "ok"
    assert summary["run_status"] == "partial_success"
    assert summary["failed_sources"] == ["SRC-GDELT-DOC"]
