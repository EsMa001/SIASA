from __future__ import annotations

import json
import os
from pathlib import Path

from siasa.readmodels.live_probe_evidence_digest import build_live_probe_evidence_digest


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_live_probe_evidence_digest_summarizes_ce_utilization_and_run_context(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    _write(
        artifacts_dir / "readmodels" / "system_status.json",
        {
            "run_id": "RUN-CI-1",
            "run_status": "success",
            "failed_sources": [],
        },
    )
    _write(
        artifacts_dir / "readmodels" / "world_map.json",
        {
            "active_domains": ["A", "B", "C", "D", "E"],
            "countries": [
                {"country_id": "UKR", "status": "S1", "active_domains": ["A", "B", "C", "D", "E"]},
                {"country_id": "POL", "status": "S1", "active_domains": ["A", "B", "D"]},
            ],
        },
    )

    digest = build_live_probe_evidence_digest(artifacts_dir=artifacts_dir)

    assert digest["run_context"]["run_id"] == "RUN-CI-1"
    assert digest["run_context"]["run_status"] == "success"
    assert digest["ce_utilization"]["domain_c_active_country_count"] == 1
    assert digest["ce_utilization"]["domain_e_active_country_count"] == 1
    assert digest["ce_utilization"]["countries_total"] == 2
    assert digest["ce_utilization"]["combined_ce_ratio"] == 0.5
    assert digest["governance_summary"]["verdict"] == "green"


def test_live_probe_evidence_digest_captures_policy_profile_context(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    _write(
        artifacts_dir / "readmodels" / "system_status.json",
        {"run_id": "RUN-CI-3", "run_status": "success", "failed_sources": []},
    )
    _write(
        artifacts_dir / "readmodels" / "world_map.json",
        {"active_domains": ["A", "B", "C", "D", "E"], "countries": [{"country_id": "UKR", "status": "S1", "active_domains": ["A", "B", "C", "D", "E"]}]},
    )

    previous_file = os.environ.get("LIVE_PROBE_POLICY_FILE")
    previous_profile = os.environ.get("LIVE_PROBE_POLICY_PROFILE")
    os.environ["LIVE_PROBE_POLICY_FILE"] = "vmodel/project/live_probe_policy_profiles.yaml"
    os.environ["LIVE_PROBE_POLICY_PROFILE"] = "standard"
    try:
        digest = build_live_probe_evidence_digest(artifacts_dir=artifacts_dir)
    finally:
        if previous_file is None:
            os.environ.pop("LIVE_PROBE_POLICY_FILE", None)
        else:
            os.environ["LIVE_PROBE_POLICY_FILE"] = previous_file
        if previous_profile is None:
            os.environ.pop("LIVE_PROBE_POLICY_PROFILE", None)
        else:
            os.environ["LIVE_PROBE_POLICY_PROFILE"] = previous_profile

    assert digest["ci_context"]["live_probe_policy_file"] == "vmodel/project/live_probe_policy_profiles.yaml"
    assert digest["ci_context"]["live_probe_policy_profile"] == "standard"


def test_live_probe_evidence_digest_marks_failed_sources_as_amber(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    _write(
        artifacts_dir / "readmodels" / "system_status.json",
        {
            "run_id": "RUN-CI-2",
            "run_status": "partial_success",
            "failed_sources": ["SRC-EXAMPLE"],
        },
    )
    _write(
        artifacts_dir / "readmodels" / "world_map.json",
        {
            "active_domains": ["A", "B", "C", "D", "E"],
            "countries": [
                {"country_id": "UKR", "status": "S2", "active_domains": ["A", "B", "C", "D", "E"]},
            ],
        },
    )

    digest = build_live_probe_evidence_digest(artifacts_dir=artifacts_dir)

    assert digest["governance_summary"]["verdict"] == "amber"
    assert "failed_sources_present" in digest["governance_summary"]["reasons"]
