from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from siasa.data.storage import persist_operational_latest_run, source_results_from_run_state
from siasa.gui.local_app import build_local_mvp_site, load_site_payload_from_artifacts
from siasa.runs.live_runtime import run_governed_live_pipeline

DEFAULT_OPERATIONAL_LATEST_PILOT_SET = "extended-focus-complete"


def _default_gui_builder(*, artifacts_dir: Path, output_dir: Path) -> Path:
    payload = load_site_payload_from_artifacts(artifacts_dir)
    result = build_local_mvp_site(output_dir=output_dir, **payload)
    return result.output_dir / "index.html"


def build_operational_latest_bundle(
    *,
    repo_root: Path,
    run_id: str,
    artifacts_dir: Path,
    gui_output_dir: Path,
    pilot_set: str = DEFAULT_OPERATIONAL_LATEST_PILOT_SET,
    history_db_path: Path | None = None,
    allow_partial_success: bool = False,
    allow_failed_sources: bool = False,
    pipeline_runner: Callable[..., Any] = run_governed_live_pipeline,
    gui_builder: Callable[..., Path] = _default_gui_builder,
    run_history_writer: Callable[..., None] = persist_operational_latest_run,
) -> dict[str, Any]:
    result = pipeline_runner(
        repo_root=repo_root,
        run_id=run_id,
        pilot_set=pilot_set,
        output_dir=artifacts_dir,
    )
    run_state = result.run_state
    allowed_statuses = {"success", "partial_success"} if allow_partial_success else {"success"}
    if run_state.status not in allowed_statuses:
        raise ValueError(
            "Operational latest build failed closed: "
            f"run_status={run_state.status}, allowed_statuses={sorted(allowed_statuses)}"
        )
    if list(run_state.failed_sources) and not allow_failed_sources:
        raise ValueError(
            "Operational latest build failed closed: "
            f"failed_sources={run_state.failed_sources}"
        )

    gui_index = gui_builder(artifacts_dir=result.artifact_bundle.output_dir, output_dir=gui_output_dir)
    resolved_history_db = history_db_path or repo_root / "build/run_history/latest_runs.sqlite"
    run_history_writer(
        resolved_history_db,
        run_id=run_state.run_id,
        run_status=run_state.status,
        pilot_set=pilot_set,
        artifacts_dir=result.artifact_bundle.output_dir,
        gui_index=gui_index,
        failed_sources=list(run_state.failed_sources),
        source_results=source_results_from_run_state(run_state),
    )
    return {
        "pilot_set": pilot_set,
        "run_id": run_state.run_id,
        "run_status": run_state.status,
        "artifacts_dir": result.artifact_bundle.output_dir,
        "gui_index": gui_index,
        "history_db": resolved_history_db,
    }
