from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from siasa.runs.scheduler import (
    SchedulerRunResult,
    execute_scheduled_run,
    run_scheduler_loop,
    send_alert,
)


# ---------------------------------------------------------------------------
# Fake bundle builder for testing (no real pipeline / network)
# ---------------------------------------------------------------------------

class RecordingBundleBuilder:
    def __init__(self, *, fail_on: set[int] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._fail_on = fail_on or set()
        self._call_count = 0

    def __call__(self, **kwargs) -> dict[str, Any]:
        self._call_count += 1
        self.calls.append(kwargs)
        if self._call_count in self._fail_on:
            raise RuntimeError(f"Simulated failure on call {self._call_count}")
        return {
            "pilot_set": kwargs.get("pilot_set", "test"),
            "run_id": kwargs.get("run_id", "RUN-TEST"),
            "run_status": "success",
            "artifacts_dir": kwargs.get("artifacts_dir", Path(".")),
            "gui_index": Path("index.html"),
            "history_db": kwargs.get("history_db_path", Path("test.sqlite")),
        }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_execute_scheduled_run_success(tmp_path: Path) -> None:
    builder = RecordingBundleBuilder()
    result = execute_scheduled_run(
        repo_root=tmp_path,
        pilot_set="representative",
        artifacts_dir=tmp_path / "artifacts",
        gui_output_dir=tmp_path / "gui",
        history_db_path=tmp_path / "history.sqlite",
        bundle_builder=builder,
    )
    assert result.status == "success"
    assert result.error_message == ""
    assert result.pilot_set == "representative"
    assert len(builder.calls) == 1


def test_execute_scheduled_run_failure(tmp_path: Path) -> None:
    builder = RecordingBundleBuilder(fail_on={1})
    result = execute_scheduled_run(
        repo_root=tmp_path,
        pilot_set="representative",
        artifacts_dir=tmp_path / "artifacts",
        gui_output_dir=tmp_path / "gui",
        history_db_path=tmp_path / "history.sqlite",
        bundle_builder=builder,
    )
    assert result.status == "failed"
    assert "Simulated failure" in result.error_message


def test_scheduler_loop_runs_n_iterations(tmp_path: Path) -> None:
    builder = RecordingBundleBuilder()
    results = run_scheduler_loop(
        repo_root=tmp_path,
        interval_seconds=0.01,
        pilot_set="representative",
        artifacts_dir=tmp_path / "artifacts",
        gui_output_dir=tmp_path / "gui",
        history_db_path=tmp_path / "history.sqlite",
        log_file=tmp_path / "scheduler.log",
        max_iterations=3,
        bundle_builder=builder,
    )
    assert len(results) == 3
    assert all(r.status == "success" for r in results)
    assert len(builder.calls) == 3
    assert (tmp_path / "scheduler.log").exists()


def test_scheduler_loop_alerts_on_failure(tmp_path: Path) -> None:
    builder = RecordingBundleBuilder(fail_on={2})
    alert_log = tmp_path / "alerts.log"

    results = run_scheduler_loop(
        repo_root=tmp_path,
        interval_seconds=0.01,
        pilot_set="representative",
        artifacts_dir=tmp_path / "artifacts",
        gui_output_dir=tmp_path / "gui",
        history_db_path=tmp_path / "history.sqlite",
        log_file=tmp_path / "scheduler.log",
        alert_log_file=alert_log,
        max_iterations=3,
        bundle_builder=builder,
    )
    assert len(results) == 3
    assert results[0].status == "success"
    assert results[1].status == "failed"
    assert results[2].status == "success"

    # Alert log should have exactly one entry (the failed run)
    import json
    alert_lines = alert_log.read_text(encoding="utf-8").strip().split("\n")
    assert len(alert_lines) == 1
    alert = json.loads(alert_lines[0])
    assert alert["alert_type"] == "scheduler_run_failed"
    assert "Simulated failure" in alert["error_message"]


def test_send_alert_to_log_file(tmp_path: Path) -> None:
    alert_log = tmp_path / "alerts.log"
    run_result = SchedulerRunResult(
        run_id="RUN-TEST-001",
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:01:00+00:00",
        status="failed",
        error_message="test error",
        pilot_set="representative",
        artifacts_dir="/tmp/artifacts",
        history_db="/tmp/history.sqlite",
    )
    send_alert(run_result=run_result, alert_log_file=alert_log)

    import json
    content = alert_log.read_text(encoding="utf-8").strip()
    alert = json.loads(content)
    assert alert["run_id"] == "RUN-TEST-001"
    assert alert["alert_type"] == "scheduler_run_failed"


def test_run_id_contains_timestamp() -> None:
    from siasa.runs.scheduler import _generate_run_id
    run_id = _generate_run_id()
    assert run_id.startswith("RUN-SCHED-")
    assert len(run_id) > len("RUN-SCHED-")
