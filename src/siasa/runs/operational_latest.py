from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from siasa.data.storage import persist_operational_latest_run, source_results_from_run_state
from siasa.gui.local_app import build_local_mvp_site, load_site_payload_from_artifacts
from siasa.readmodels.live_probe_evidence_digest import build_live_probe_evidence_digest
from siasa.readmodels.live_probe_policy_gate import evaluate_live_probe_digest_policy, load_live_probe_policy_profile
from siasa.runs.latest_bundle_verification import verify_latest_bundle
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
    readmodels_dir = result.artifact_bundle.output_dir / "readmodels"
    readmodels_dir.mkdir(parents=True, exist_ok=True)

    digest = build_live_probe_evidence_digest(artifacts_dir=result.artifact_bundle.output_dir)
    digest_path = readmodels_dir / "live_probe_evidence_digest.json"
    digest_path.write_text(json.dumps(digest, indent=2, sort_keys=True), encoding="utf-8")

    policy = load_live_probe_policy_profile(
        policy_file=repo_root / "vmodel" / "project" / "live_probe_policy_profiles.yaml",
        profile="standard",
    )
    gate_evaluation = evaluate_live_probe_digest_policy(digest, policy=policy)
    gate_path = readmodels_dir / "live_probe_policy_gate.json"
    gate_path.write_text(json.dumps(gate_evaluation, indent=2, sort_keys=True), encoding="utf-8")

    verification_summary = verify_latest_bundle(
        result.artifact_bundle.output_dir,
        allow_partial_success=allow_partial_success,
        allow_failed_sources=allow_failed_sources,
    )

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
        "digest_path": digest_path,
        "policy_gate_path": gate_path,
        "policy_gate_verdict": gate_evaluation.get("gate_verdict"),
        "verification_summary": verification_summary,
    }
