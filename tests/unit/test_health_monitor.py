from __future__ import annotations

import json
import time
from pathlib import Path

from siasa.runs.health_monitor import (
    HealthCheck,
    HealthStatus,
    check_artifacts_exist,
    check_artifacts_staleness,
    check_liveness,
    check_run_history_health,
    run_health_checks,
    write_health_status,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _build_minimal_artifacts(tmp_path: Path) -> Path:
    artifacts = tmp_path / "latest"
    _write_json(artifacts / "snapshot.json", {"snapshot_id": "SNAP-001"})
    _write_json(artifacts / "readmodels/system_status.json", {"run_id": "RUN-001"})
    _write_json(artifacts / "readmodels/world_map.json", {"countries": []})
    return artifacts


def test_check_liveness() -> None:
    result = check_liveness()
    assert result.status == "ok"
    assert result.name == "liveness"


def test_check_artifacts_exist_ok(tmp_path: Path) -> None:
    artifacts = _build_minimal_artifacts(tmp_path)
    result = check_artifacts_exist(artifacts)
    assert result.status == "ok"


def test_check_artifacts_exist_missing_dir(tmp_path: Path) -> None:
    result = check_artifacts_exist(tmp_path / "nonexistent")
    assert result.status == "critical"


def test_check_artifacts_exist_missing_file(tmp_path: Path) -> None:
    artifacts = _build_minimal_artifacts(tmp_path)
    (artifacts / "readmodels/world_map.json").unlink()
    result = check_artifacts_exist(artifacts)
    assert result.status == "warning"
    assert "world_map.json" in result.message


def test_check_artifacts_staleness_fresh(tmp_path: Path) -> None:
    artifacts = _build_minimal_artifacts(tmp_path)
    result = check_artifacts_staleness(artifacts, max_staleness_hours=48.0)
    assert result.status == "ok"


def test_check_artifacts_staleness_stale(tmp_path: Path) -> None:
    artifacts = _build_minimal_artifacts(tmp_path)
    # Make snapshot old by setting mtime 72 hours ago
    import os
    old_time = time.time() - 72 * 3600
    os.utime(artifacts / "snapshot.json", (old_time, old_time))
    result = check_artifacts_staleness(artifacts, max_staleness_hours=48.0)
    assert result.status == "warning"
    assert "72" in result.message or "71" in result.message


def test_check_artifacts_staleness_no_snapshot(tmp_path: Path) -> None:
    result = check_artifacts_staleness(tmp_path / "nonexistent", max_staleness_hours=48.0)
    assert result.status == "critical"


def test_check_run_history_health_no_db(tmp_path: Path) -> None:
    result = check_run_history_health(tmp_path / "nonexistent.sqlite")
    assert result.status == "warning"
    assert "does not exist" in result.message


def test_check_run_history_health_with_success_run(tmp_path: Path) -> None:
    from siasa.data.storage import persist_operational_latest_run
    db_path = tmp_path / "history.sqlite"
    persist_operational_latest_run(
        db_path,
        run_id="RUN-001",
        run_status="success",
        pilot_set="representative",
        artifacts_dir=tmp_path / "artifacts",
        gui_index=tmp_path / "gui/index.html",
        failed_sources=[],
    )
    result = check_run_history_health(db_path)
    assert result.status == "ok"
    assert "RUN-001" in result.message


def test_check_run_history_health_with_failed_run(tmp_path: Path) -> None:
    from siasa.data.storage import persist_operational_latest_run
    db_path = tmp_path / "history.sqlite"
    persist_operational_latest_run(
        db_path,
        run_id="RUN-002",
        run_status="partial_success",
        pilot_set="representative",
        artifacts_dir=tmp_path / "artifacts",
        gui_index=tmp_path / "gui/index.html",
        failed_sources=["SRC-GDELT-DOC"],
    )
    result = check_run_history_health(db_path)
    assert result.status == "warning"
    assert "partial_success" in result.message


def test_run_health_checks_healthy(tmp_path: Path) -> None:
    from siasa.data.storage import persist_operational_latest_run
    artifacts = _build_minimal_artifacts(tmp_path)
    db_path = tmp_path / "history.sqlite"
    persist_operational_latest_run(
        db_path,
        run_id="RUN-001",
        run_status="success",
        pilot_set="representative",
        artifacts_dir=artifacts,
        gui_index=tmp_path / "gui/index.html",
        failed_sources=[],
    )
    health = run_health_checks(
        artifacts_dir=artifacts,
        history_db_path=db_path,
        skip_source_probe=True,
    )
    assert health.overall == "healthy"
    assert len(health.checks) == 4


def test_run_health_checks_degraded(tmp_path: Path) -> None:
    artifacts = _build_minimal_artifacts(tmp_path)
    # No run history -> warning
    health = run_health_checks(
        artifacts_dir=artifacts,
        history_db_path=tmp_path / "nonexistent.sqlite",
        skip_source_probe=True,
    )
    assert health.overall == "degraded"


def test_write_health_status(tmp_path: Path) -> None:
    health = HealthStatus(
        overall="healthy",
        checked_at="2026-01-01T00:00:00+00:00",
        checks=[HealthCheck(name="test", status="ok", message="ok", checked_at="2026-01-01T00:00:00+00:00")],
    )
    output = tmp_path / "health.json"
    write_health_status(health, output)
    assert output.exists()
    data = json.loads(output.read_text())
    assert data["overall"] == "healthy"
    assert len(data["checks"]) == 1
