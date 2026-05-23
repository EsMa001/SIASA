from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from siasa.readmodels.readiness import build_readiness_view_model
from siasa.readmodels.release_gate import build_release_gate_view_model
from siasa.traceability.consistency import build_traceability_integrity_report


def build_repo_release_gate_assessment(*, repo_root: Path) -> dict[str, Any]:
    readiness_view_model = build_readiness_view_model(
        country_profile_read_models={"UKR": {"country_id": "UKR"}},
        domain_detail_read_models={("UKR", "A"): {"country_id": "UKR", "domain": "A"}},
        report_catalog={"REP-1": {"id": "REP-1"}},
        system_status_read_model={
            "run_id": "RUN-CI-RELEASE-GATE",
            "snapshot_id": "SNAP-CI-RELEASE-GATE-v1",
            "failed_sources": [],
            "data_gaps": [],
            "country_coverage_visibility": {"country_gap_rows": []},
            "coverage": {"countries_total": 1, "countries_with_updates": 1},
            "artifact_status": {},
        },
        source_coverage_read_model={"missing_sources": []},
        validation_view_model={"ok": True},
        traceability_view_model={"ok": True},
        annotations_view_model={"ok": True},
        repo_closure_view_model={"ok": True},
        available_pages={"index.html", "coverage.html", "reports.html", "validation.html"},
    )
    traceability_integrity = build_traceability_integrity_report(repo_root=repo_root)
    release_gate = build_release_gate_view_model(
        readiness_view_model=readiness_view_model,
        traceability_integrity_report=traceability_integrity,
    )
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "release_gate": release_gate,
        "readiness": readiness_view_model,
        "traceability_integrity": traceability_integrity,
    }


def render_release_evidence_markdown(assessment: dict[str, Any]) -> str:
    gate = assessment.get("release_gate", {})
    summary = ((assessment.get("traceability_integrity") or {}).get("summary") or {})
    blockers = [str(item) for item in gate.get("blockers", [])]
    blocker_lines = "\n".join(f"- {item}" for item in blockers) or "- none"
    return (
        "# SIASA Release Evidence Pack\n\n"
        f"- generated_at_utc: {assessment.get('generated_at_utc', 'n/a')}\n"
        f"- gate_verdict: {gate.get('gate_verdict', 'n/a')}\n"
        f"- blocker_count: {gate.get('blocker_count', 'n/a')}\n"
        f"- release_verdict: {(assessment.get('readiness') or {}).get('release_verdict', 'n/a')}\n"
        f"- demo_verdict: {(assessment.get('readiness') or {}).get('demo_verdict', 'n/a')}\n"
        f"- traceability_unhealthy_slice_count: {summary.get('unhealthy_slice_count', 'n/a')}\n"
        f"- traceability_closure_at_risk: {summary.get('closure_at_risk', 'n/a')}\n\n"
        "## Blockers\n"
        f"{blocker_lines}\n"
    )
