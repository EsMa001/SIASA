"""SIASA daily run scheduler.

Provides a lightweight scheduler that executes ``build_operational_latest_bundle``
on a configurable interval (default: every 24 h), rotates ``latest/`` artifacts,
detects failures, and writes structured log entries.

The scheduler is intentionally simple (``time.sleep`` loop, no Celery/APScheduler
dependency) to keep the MVP operational footprint minimal.  It is designed to run
as a foreground process supervised by systemd, s6, or a simple ``nohup`` wrapper.

Usage (Linux/macOS):
    PYTHONPATH=src python -m siasa.runs.scheduler \\
        --repo-root . \\
        --interval-hours 24 \\
        --pilot-set extended-focus-complete \\
        --artifacts-dir build/run_artifacts/latest \\
        --gui-output-dir build/local_gui/latest \\
        --history-db build/run_history/latest_runs.sqlite \\
        --log-file build/scheduler/scheduler.log

Usage (Windows/PyCharm):
    $env:PYTHONPATH="src"; .\\venv\\Scripts\\python.exe -m siasa.runs.scheduler `
        --repo-root . --interval-hours 24

Alerting:
    --alert-webhook URL     POST JSON alert on failure to this URL
    --alert-log-file PATH   append alert lines to this file (default: scheduler.log)
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from siasa.runs.operational_latest import DEFAULT_OPERATIONAL_LATEST_PILOT_SET, build_operational_latest_bundle

logger = logging.getLogger("siasa.scheduler")


@dataclass(frozen=True)
class SchedulerRunResult:
    run_id: str
    started_at: str
    finished_at: str
    status: str  # "success" | "failed"
    error_message: str
    pilot_set: str
    artifacts_dir: str
    history_db: str


def _generate_run_id() -> str:
    return f"RUN-SCHED-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute_scheduled_run(
    *,
    repo_root: Path,
    pilot_set: str,
    artifacts_dir: Path,
    gui_output_dir: Path,
    history_db_path: Path,
    bundle_builder: Callable[..., dict[str, Any]] = build_operational_latest_bundle,
) -> SchedulerRunResult:
    """Execute a single scheduled run and return structured result."""
    run_id = _generate_run_id()
    started_at = _now_iso()
    try:
        result = bundle_builder(
            repo_root=repo_root,
            run_id=run_id,
            pilot_set=pilot_set,
            artifacts_dir=artifacts_dir,
            gui_output_dir=gui_output_dir,
            history_db_path=history_db_path,
        )
        return SchedulerRunResult(
            run_id=run_id,
            started_at=started_at,
            finished_at=_now_iso(),
            status="success",
            error_message="",
            pilot_set=pilot_set,
            artifacts_dir=str(result.get("artifacts_dir", artifacts_dir)),
            history_db=str(result.get("history_db", history_db_path)),
        )
    except Exception as exc:
        return SchedulerRunResult(
            run_id=run_id,
            started_at=started_at,
            finished_at=_now_iso(),
            status="failed",
            error_message=str(exc)[:500],
            pilot_set=pilot_set,
            artifacts_dir=str(artifacts_dir),
            history_db=str(history_db_path),
        )


def send_alert(
    *,
    run_result: SchedulerRunResult,
    webhook_url: Optional[str] = None,
    alert_log_file: Optional[Path] = None,
) -> None:
    """Send failure alert via webhook and/or log file."""
    payload = asdict(run_result)
    payload["alert_type"] = "scheduler_run_failed"

    if alert_log_file:
        alert_log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(alert_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")

    if webhook_url:
        try:
            import urllib.request
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                logger.info("Alert webhook responded: %s", resp.status)
        except Exception as exc:
            logger.warning("Alert webhook failed: %s", exc)


def run_scheduler_loop(
    *,
    repo_root: Path,
    interval_seconds: float,
    pilot_set: str,
    artifacts_dir: Path,
    gui_output_dir: Path,
    history_db_path: Path,
    log_file: Optional[Path] = None,
    alert_webhook: Optional[str] = None,
    alert_log_file: Optional[Path] = None,
    max_iterations: Optional[int] = None,
    bundle_builder: Callable[..., dict[str, Any]] = build_operational_latest_bundle,
) -> list[SchedulerRunResult]:
    """Run the scheduler loop. Returns list of results (useful for testing)."""

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info(
        "Scheduler started: interval=%ds pilot_set=%s artifacts_dir=%s",
        int(interval_seconds), pilot_set, artifacts_dir,
    )

    results: list[SchedulerRunResult] = []
    iteration = 0

    while True:
        if max_iterations is not None and iteration >= max_iterations:
            break

        logger.info("Scheduler tick %d: starting run", iteration + 1)

        run_result = execute_scheduled_run(
            repo_root=repo_root,
            pilot_set=pilot_set,
            artifacts_dir=artifacts_dir,
            gui_output_dir=gui_output_dir,
            history_db_path=history_db_path,
            bundle_builder=bundle_builder,
        )
        results.append(run_result)

        if run_result.status == "success":
            logger.info(
                "Scheduler tick %d: SUCCESS run_id=%s duration=%s",
                iteration + 1, run_result.run_id,
                _duration_str(run_result.started_at, run_result.finished_at),
            )
        else:
            logger.error(
                "Scheduler tick %d: FAILED run_id=%s error=%s",
                iteration + 1, run_result.run_id, run_result.error_message[:200],
            )
            resolved_alert_log = alert_log_file or log_file
            send_alert(
                run_result=run_result,
                webhook_url=alert_webhook,
                alert_log_file=resolved_alert_log,
            )

        iteration += 1
        if max_iterations is not None and iteration >= max_iterations:
            break

        logger.info("Scheduler: sleeping %d seconds until next run", int(interval_seconds))
        time.sleep(interval_seconds)

    logger.info("Scheduler stopped after %d iterations", iteration)
    return results


def _duration_str(started_at: str, finished_at: str) -> str:
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(finished_at)
        delta = end - start
        return f"{delta.total_seconds():.1f}s"
    except Exception:
        return "?"


def main() -> int:
    parser = argparse.ArgumentParser(description="SIASA daily run scheduler")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--interval-hours", type=float, default=24.0, help="Hours between runs (default: 24)")
    parser.add_argument("--pilot-set", default=DEFAULT_OPERATIONAL_LATEST_PILOT_SET, help="Governed pilot set")
    parser.add_argument("--artifacts-dir", default="build/run_artifacts/latest", help="Artifact output directory")
    parser.add_argument("--gui-output-dir", default="build/local_gui/latest", help="GUI output directory")
    parser.add_argument("--history-db", default="build/run_history/latest_runs.sqlite", help="SQLite run-history DB")
    parser.add_argument("--log-file", default="build/scheduler/scheduler.log", help="Scheduler log file")
    parser.add_argument("--alert-webhook", default=None, help="Webhook URL for failure alerts (POST JSON)")
    parser.add_argument("--alert-log-file", default=None, help="File for alert log lines (default: scheduler log)")
    args = parser.parse_args()

    run_scheduler_loop(
        repo_root=Path(args.repo_root),
        interval_seconds=args.interval_hours * 3600,
        pilot_set=args.pilot_set,
        artifacts_dir=Path(args.artifacts_dir),
        gui_output_dir=Path(args.gui_output_dir),
        history_db_path=Path(args.history_db),
        log_file=Path(args.log_file),
        alert_webhook=args.alert_webhook,
        alert_log_file=Path(args.alert_log_file) if args.alert_log_file else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
