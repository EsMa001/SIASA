from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


def _build_bundle_evidence_links(*, bundle_dir: Path) -> dict[str, str]:
    bundle_dir = bundle_dir.resolve()
    return {
        "bundle_index_href": str(bundle_dir / "index.html"),
        "coverage_page_href": str(bundle_dir / "coverage.html"),
        "coverage_json_href": str(bundle_dir / "source_coverage.json"),
        "system_status_json_href": str(bundle_dir / "system_status.json"),
        "readiness_page_href": str(bundle_dir / "readiness.html"),
        "readiness_json_href": str(bundle_dir / "readiness.json"),
        "release_package_page_href": str(bundle_dir / "release_package.html"),
        "release_package_json_href": str(bundle_dir / "release_demo_package.json"),
        "release_gate_json_href": str(bundle_dir / "release_gate.json"),
    }


def _build_bundle_share_refs(*, bundle_root: Path) -> dict[str, str]:
    bundle_root = bundle_root.resolve()
    return {
        "bundle_ref": f"bundle:{bundle_root}",
        "coverage_json_ref": f"coverage_json:{bundle_root / 'source_coverage.json'}",
        "system_status_json_ref": f"system_status_json:{bundle_root / 'system_status.json'}",
        "readiness_json_ref": f"readiness_json:{bundle_root / 'readiness.json'}",
        "release_package_json_ref": f"release_package_json:{bundle_root / 'release_demo_package.json'}",
        "release_gate_json_ref": f"release_gate_json:{bundle_root / 'release_gate.json'}",
    }


def _build_bundle_handoff_summary(*, run_id: str, bundle_root: Path, share_refs: dict[str, str]) -> str:
    bundle_root = bundle_root.resolve()
    return (
        f"Run {run_id}: bundle at {bundle_root}; "
        f"review {share_refs.get('readiness_json_ref', 'readiness_json:n/a')}, "
        f"{share_refs.get('coverage_json_ref', 'coverage_json:n/a')}, and "
        f"{share_refs.get('release_gate_json_ref', 'release_gate_json:n/a')}."
    )


def _derive_run_triage(*, run_status: str, governance_verdict: str, policy_gate_verdict: str, release_verdict: str, readiness_interpretation: str, known_gap_count: int, failed_source_count: int) -> dict[str, str]:
    normalized_run_status = str(run_status or "unknown").lower()
    normalized_governance = str(governance_verdict or "unknown").lower()
    normalized_policy_gate = str(policy_gate_verdict or "unknown").lower()
    normalized_release = str(release_verdict or "unknown").lower()
    normalized_readiness = str(readiness_interpretation or "unknown").lower()

    if normalized_readiness == "runtime_degraded_and_release_blocked" or (
        normalized_release == "blocked_by_known_gaps" and normalized_run_status == "partial_success"
    ):
        return {
            "triage_tag": "degraded_release_blocked",
            "triage_summary": "Runtime degraded and release blocked; review failed sources and known gaps first.",
        }
    if normalized_readiness == "degraded_but_release_ready" or (
        normalized_release == "ready" and normalized_run_status == "partial_success"
    ):
        return {
            "triage_tag": "degraded_but_release_ready",
            "triage_summary": "Runtime degraded but release remains ready; review degraded sources before reuse.",
        }
    if (
        normalized_release == "ready"
        and normalized_run_status == "success"
        and normalized_governance == "green"
        and normalized_policy_gate == "pass"
        and known_gap_count == 0
        and failed_source_count == 0
    ):
        return {
            "triage_tag": "ready_green",
            "triage_summary": "Run is green and release-ready; suitable as the default handoff baseline.",
        }
    return {
        "triage_tag": "review_required",
        "triage_summary": (
            "Run requires manual review before reuse; "
            f"readiness={normalized_readiness}, governance={normalized_governance}, policy_gate={normalized_policy_gate}."
        ),
    }

from siasa.data.storage import (
    load_recent_runs,
    persist_operational_latest_run,
    source_results_from_run_state,
)
from siasa.gui.local_app import build_local_mvp_site, load_site_payload_from_artifacts
from siasa.readmodels.live_probe_evidence_digest import build_live_probe_evidence_digest
from siasa.readmodels.live_probe_policy_gate import evaluate_live_probe_digest_policy, load_live_probe_policy_profile
from siasa.runs.latest_bundle_verification import verify_latest_bundle
from siasa.runs.live_runtime import run_governed_live_pipeline


def _derive_readiness_interpretation(*, run_status: str, release_verdict: str, known_gaps: list[str], policy_gate_verdict: str) -> str:
    normalized_run_status = str(run_status or "unknown").lower()
    normalized_release_verdict = str(release_verdict or "unknown").lower()
    normalized_policy_gate = str(policy_gate_verdict or "unknown").lower()
    if normalized_release_verdict == "ready":
        if normalized_run_status == "partial_success":
            return "degraded_but_release_ready"
        return "release_ready"
    if normalized_release_verdict == "blocked_by_known_gaps":
        if normalized_run_status == "partial_success" and normalized_policy_gate == "pass":
            return "runtime_degraded_and_release_blocked"
        return "release_blocked_by_known_gaps"
    if normalized_release_verdict == "blocked":
        return "release_blocked"
    if known_gaps:
        return "release_truth_requires_review"
    return "release_truth_unknown"

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
    readiness = json.loads((readmodels_dir / "readiness.json").read_text(encoding="utf-8"))
    release_verdict = str(readiness.get("release_verdict") or "unknown")
    known_gaps = [str(item) for item in (readiness.get("known_gaps") or [])]
    suppressed_known_gaps = [str(item) for item in (readiness.get("suppressed_known_gaps") or [])]
    readiness_interpretation = _derive_readiness_interpretation(
        run_status=run_state.status,
        release_verdict=release_verdict,
        known_gaps=known_gaps,
        policy_gate_verdict=str(gate_evaluation.get("gate_verdict") or "unknown"),
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
        country_set_id=str(verification_summary.get("country_set_id") or "unknown"),
        combined_ce_ratio=digest.get("ce_utilization", {}).get("combined_ce_ratio"),
        governance_verdict=str(digest.get("governance_summary", {}).get("verdict") or "unknown"),
        policy_gate_verdict=str(gate_evaluation.get("gate_verdict") or "unknown"),
        release_verdict=release_verdict,
        readiness_interpretation=readiness_interpretation,
        known_gap_count=len(known_gaps),
    )
    evidence_links = _build_bundle_evidence_links(bundle_dir=gui_index.parent)
    bundle_root = str(gui_index.parent.resolve())
    share_refs = _build_bundle_share_refs(bundle_root=gui_index.parent)
    handoff_summary = _build_bundle_handoff_summary(
        run_id=run_state.run_id,
        bundle_root=gui_index.parent,
        share_refs=share_refs,
    )
    latest_triage = _derive_run_triage(
        run_status=run_state.status,
        governance_verdict=str(digest.get("governance_summary", {}).get("verdict") or "unknown"),
        policy_gate_verdict=str(gate_evaluation.get("gate_verdict") or "unknown"),
        release_verdict=release_verdict,
        readiness_interpretation=readiness_interpretation,
        known_gap_count=len(known_gaps),
        failed_source_count=len(list(run_state.failed_sources)),
    )
    recent_runs = [
        {
            "run_id": entry.run_id,
            "recorded_at": entry.recorded_at,
            "run_status": entry.run_status,
            "pilot_set": entry.pilot_set,
            "artifacts_dir": entry.artifacts_dir,
            "gui_index": entry.gui_index,
            "bundle_root": str(Path(entry.gui_index).resolve().parent),
            "country_set_id": entry.country_set_id,
            "combined_ce_ratio": entry.combined_ce_ratio,
            "governance_verdict": entry.governance_verdict,
            "policy_gate_verdict": entry.policy_gate_verdict,
            "release_verdict": entry.release_verdict,
            "readiness_interpretation": entry.readiness_interpretation,
            "known_gap_count": entry.known_gap_count,
            "failed_source_count": len(entry.failed_sources),
            "failed_sources": entry.failed_sources,
            "evidence_links": _build_bundle_evidence_links(bundle_dir=Path(entry.gui_index).parent),
            "share_refs": _build_bundle_share_refs(bundle_root=Path(entry.gui_index).parent),
            "handoff_summary": _build_bundle_handoff_summary(
                run_id=entry.run_id,
                bundle_root=Path(entry.gui_index).parent,
                share_refs=_build_bundle_share_refs(bundle_root=Path(entry.gui_index).parent),
            ),
            **_derive_run_triage(
                run_status=entry.run_status,
                governance_verdict=entry.governance_verdict,
                policy_gate_verdict=entry.policy_gate_verdict,
                release_verdict=entry.release_verdict,
                readiness_interpretation=entry.readiness_interpretation,
                known_gap_count=entry.known_gap_count,
                failed_source_count=len(entry.failed_sources),
            ),
        }
        for entry in load_recent_runs(resolved_history_db, limit=10)
    ]
    if not recent_runs:
        recent_runs = [
            {
                "run_id": run_state.run_id,
                "recorded_at": "pending_persisted_history",
                "run_status": run_state.status,
                "pilot_set": pilot_set,
                "artifacts_dir": str(result.artifact_bundle.output_dir),
                "gui_index": str(gui_index),
                "bundle_root": bundle_root,
                "country_set_id": str(verification_summary.get("country_set_id") or "unknown"),
                "combined_ce_ratio": digest.get("ce_utilization", {}).get("combined_ce_ratio"),
                "countries_missing_both_ce_count": verification_summary.get("countries_missing_both_ce_count", 0),
                "countries_missing_both_ce": verification_summary.get("countries_missing_both_ce", []),
                "governance_verdict": str(digest.get("governance_summary", {}).get("verdict") or "unknown"),
                "policy_gate_verdict": str(gate_evaluation.get("gate_verdict") or "unknown"),
                "release_verdict": release_verdict,
                "readiness_interpretation": readiness_interpretation,
                "known_gap_count": len(known_gaps),
                "failed_source_count": len(list(run_state.failed_sources)),
                "failed_sources": list(run_state.failed_sources),
                "evidence_links": evidence_links,
                "share_refs": share_refs,
                "handoff_summary": handoff_summary,
                **latest_triage,
            }
        ]
    evidence_lane = {
        "latest_summary": {
            "run_id": run_state.run_id,
            "run_status": run_state.status,
            "pilot_set": pilot_set,
            "artifacts_dir": str(result.artifact_bundle.output_dir),
            "gui_index": str(gui_index),
            "bundle_root": bundle_root,
            "country_set_id": str(verification_summary.get("country_set_id") or "unknown"),
            "combined_ce_ratio": digest.get("ce_utilization", {}).get("combined_ce_ratio"),
            "countries_missing_both_ce_count": verification_summary.get("countries_missing_both_ce_count", 0),
            "countries_missing_both_ce": verification_summary.get("countries_missing_both_ce", []),
            "governance_verdict": str(digest.get("governance_summary", {}).get("verdict") or "unknown"),
            "policy_gate_verdict": str(gate_evaluation.get("gate_verdict") or "unknown"),
            "release_verdict": release_verdict,
            "known_gaps": known_gaps,
            "known_gap_count": len(known_gaps),
            "suppressed_known_gaps": suppressed_known_gaps,
            "known_gap_suppression_reason": readiness.get("known_gap_suppression_reason"),
            "readiness_interpretation": readiness_interpretation,
            "failed_source_count": len(list(run_state.failed_sources)),
            "failed_sources": list(run_state.failed_sources),
            "operator_next_action": str(digest.get("governance_summary", {}).get("operator_next_action") or "n/a"),
            "evidence_links": evidence_links,
            "share_refs": share_refs,
            "handoff_summary": handoff_summary,
            **latest_triage,
        },
        "recent_runs": recent_runs,
    }
    evidence_lane_path = readmodels_dir / "operational_evidence_lane.json"
    evidence_lane_path.write_text(json.dumps(evidence_lane, indent=2, sort_keys=True), encoding="utf-8")
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
        "operational_evidence_lane_path": evidence_lane_path,
    }
