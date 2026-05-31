from __future__ import annotations

from pathlib import Path

from siasa.data.storage import (
    load_recent_runs,
    load_source_results_for_run,
    persist_operational_latest_run,
)


def test_persist_operational_latest_run_writes_run_and_sources(tmp_path: Path) -> None:
    db_path = tmp_path / "run_history.sqlite"

    persist_operational_latest_run(
        db_path,
        run_id="RUN-LATEST-001",
        run_status="success",
        pilot_set="extended-focus-complete",
        artifacts_dir=tmp_path / "artifacts/latest",
        gui_index=tmp_path / "gui/latest/index.html",
        failed_sources=[],
        source_results=[
            {"source_id": "WB-INDICATORS", "status": "success", "diagnostics": ""},
            {"source_id": "SRC-GDELT-DOC", "status": "failed", "diagnostics": "timeout"},
        ],
    )

    runs = load_recent_runs(db_path, limit=5)
    assert len(runs) == 1
    assert runs[0].run_id == "RUN-LATEST-001"
    assert runs[0].run_status == "success"
    assert runs[0].pilot_set == "extended-focus-complete"
    assert runs[0].failed_sources == []

    source_results = load_source_results_for_run(db_path, run_id="RUN-LATEST-001")
    assert [entry.source_id for entry in source_results] == ["SRC-GDELT-DOC", "WB-INDICATORS"]
    assert source_results[0].status == "failed"
    assert source_results[0].diagnostics == "timeout"


def test_persist_operational_latest_run_upserts_existing_run(tmp_path: Path) -> None:
    db_path = tmp_path / "run_history.sqlite"

    persist_operational_latest_run(
        db_path,
        run_id="RUN-LATEST-001",
        run_status="partial_success",
        pilot_set="representative",
        artifacts_dir=tmp_path / "artifacts/latest",
        gui_index=tmp_path / "gui/latest/index.html",
        failed_sources=["SRC-GDELT-DOC"],
        source_results=[
            {"source_id": "SRC-GDELT-DOC", "status": "failed", "diagnostics": "timeout"},
        ],
    )

    persist_operational_latest_run(
        db_path,
        run_id="RUN-LATEST-001",
        run_status="success",
        pilot_set="extended-focus-complete",
        artifacts_dir=tmp_path / "artifacts/latest_v2",
        gui_index=tmp_path / "gui/latest_v2/index.html",
        failed_sources=[],
        source_results=[
            {"source_id": "WB-INDICATORS", "status": "success", "diagnostics": ""},
        ],
    )

    runs = load_recent_runs(db_path, limit=5)
    assert len(runs) == 1
    assert runs[0].run_status == "success"
    assert runs[0].pilot_set == "extended-focus-complete"
    assert runs[0].artifacts_dir.endswith("artifacts/latest_v2")
    assert runs[0].failed_sources == []

    source_results = load_source_results_for_run(db_path, run_id="RUN-LATEST-001")
    assert len(source_results) == 1
    assert source_results[0].source_id == "WB-INDICATORS"
    assert source_results[0].status == "success"
