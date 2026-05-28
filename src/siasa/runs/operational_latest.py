from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

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
    pipeline_runner: Callable[..., Any] = run_governed_live_pipeline,
    gui_builder: Callable[..., Path] = _default_gui_builder,
) -> dict[str, Any]:
    result = pipeline_runner(
        repo_root=repo_root,
        run_id=run_id,
        pilot_set=pilot_set,
        output_dir=artifacts_dir,
    )
    run_state = result.run_state
    if run_state.status != "success" or list(run_state.failed_sources):
        raise ValueError(
            f"Operational latest build failed closed: run_status={run_state.status}, failed_sources={run_state.failed_sources}"
        )

    gui_index = gui_builder(artifacts_dir=result.artifact_bundle.output_dir, output_dir=gui_output_dir)
    return {
        "pilot_set": pilot_set,
        "run_id": run_state.run_id,
        "run_status": run_state.status,
        "artifacts_dir": result.artifact_bundle.output_dir,
        "gui_index": gui_index,
    }
