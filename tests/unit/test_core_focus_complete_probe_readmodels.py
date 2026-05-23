from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE_ROOT = REPO_ROOT / "build" / "run_artifacts" / "_core_focus_complete_probe_1" / "readmodels"


def test_core_focus_complete_probe_readiness_is_ready_without_known_gaps() -> None:
    readiness = json.loads((PROBE_ROOT / "readiness.json").read_text(encoding="utf-8"))

    assert readiness["run_id"] == "RUN-LIVE-CORE-COMPLETE-001"
    assert readiness["release_verdict"] == "ready"
    assert readiness["known_gaps"] == []


def test_core_focus_complete_probe_system_status_has_no_failed_sources() -> None:
    system_status = json.loads((PROBE_ROOT / "system_status.json").read_text(encoding="utf-8"))

    assert system_status["run_id"] == "RUN-LIVE-CORE-COMPLETE-001"
    assert system_status["run_status"] == "success"
    assert system_status["failed_sources"] == []


def test_core_focus_complete_probe_world_map_covers_core_focus_countries() -> None:
    world_map = json.loads((PROBE_ROOT / "world_map.json").read_text(encoding="utf-8"))

    country_ids = {entry["country_id"] for entry in world_map["countries"]}
    assert country_ids == {
        "UKR",
        "RUS",
        "CHN",
        "TWN",
        "IRN",
        "ISR",
        "TUR",
        "IND",
        "PAK",
        "GEO",
        "POL",
    }
