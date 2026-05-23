from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from siasa.readmodels.readiness import build_readiness_view_model
from siasa.readmodels.release_gate import build_release_gate_view_model
from siasa.readmodels.stakeholder_functional_closure import build_stakeholder_functional_closure_report
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
    stakeholder_functional_closure = build_stakeholder_functional_closure_report(repo_root=repo_root)
    release_gate = build_release_gate_view_model(
        readiness_view_model=readiness_view_model,
        traceability_integrity_report=traceability_integrity,
    )
    release_readiness_index = build_release_readiness_index(
        repo_root=repo_root,
        release_gate_view_model=release_gate,
        stakeholder_functional_closure_report=stakeholder_functional_closure,
    )
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "release_gate": release_gate,
        "release_readiness_index": release_readiness_index,
        "readiness": readiness_view_model,
        "traceability_integrity": traceability_integrity,
        "stakeholder_functional_closure": stakeholder_functional_closure,
    }


def build_release_readiness_index(
    *,
    repo_root: Path,
    release_gate_view_model: dict[str, Any],
    stakeholder_functional_closure_report: dict[str, Any],
) -> dict[str, Any]:
    workflow_path = repo_root / ".github" / "workflows" / "vmodel-ci.yml"
    runbook_path = repo_root / "docs" / "verification" / "release-go-no-go-runbook.md"
    evidence_script = repo_root / "scripts" / "build_release_evidence_pack.py"
    gate_script = repo_root / "scripts" / "ci_release_gate_check.py"

    workflow_text = workflow_path.read_text(encoding="utf-8") if workflow_path.exists() else ""
    ci_gate_enforced = (
        "scripts/ci_release_gate_check.py" in workflow_text
        and "scripts/build_release_evidence_pack.py" in workflow_text
    )

    gates = [
        {
            "gate_id": "release_gate_go",
            "passed": release_gate_view_model.get("gate_verdict") == "go",
            "detail": str(release_gate_view_model.get("gate_verdict", "unknown")),
        },
        {
            "gate_id": "traceability_integrity_clean",
            "passed": "traceability_integrity_clean" not in [
                str(item) for item in release_gate_view_model.get("blockers", [])
            ],
            "detail": "derived_from_release_gate_blockers",
        },
        {
            "gate_id": "stakeholder_functional_focus_cluster_closed",
            "passed": (
                int((stakeholder_functional_closure_report.get("focus_gap_cluster") or {}).get("covered_count", 0)) == 19
                and int((stakeholder_functional_closure_report.get("focus_gap_cluster") or {}).get("not_implemented_count", 1))
                == 0
            ),
            "detail": "focus_gap_cluster.covered_count==19 and not_implemented_count==0",
        },
        {
            "gate_id": "ci_gate_enforced",
            "passed": ci_gate_enforced,
            "detail": str(workflow_path.relative_to(repo_root)),
        },
        {
            "gate_id": "evidence_pack_tooling_present",
            "passed": evidence_script.exists() and gate_script.exists(),
            "detail": "scripts/build_release_evidence_pack.py + scripts/ci_release_gate_check.py",
        },
        {
            "gate_id": "go_no_go_runbook_present",
            "passed": runbook_path.exists(),
            "detail": str(runbook_path.relative_to(repo_root)),
        },
    ]

    passed_count = sum(1 for gate in gates if bool(gate["passed"]))
    total_count = len(gates)
    percent = round((passed_count / total_count) * 100.0, 1) if total_count else 0.0

    return {
        "passed_gates": passed_count,
        "total_gates": total_count,
        "percent": percent,
        "gates": gates,
    }


def render_release_evidence_markdown(assessment: dict[str, Any]) -> str:
    gate = assessment.get("release_gate", {})
    readiness_index = assessment.get("release_readiness_index", {})
    summary = ((assessment.get("traceability_integrity") or {}).get("summary") or {})
    blockers = [str(item) for item in gate.get("blockers", [])]
    blocker_lines = "\n".join(f"- {item}" for item in blockers) or "- none"
    index_lines = "\n".join(
        f"- {item.get('gate_id', 'unknown')}: {'pass' if item.get('passed') else 'fail'}"
        for item in readiness_index.get("gates", [])
    ) or "- none"
    return (
        "# SIASA Release Evidence Pack\n\n"
        f"- generated_at_utc: {assessment.get('generated_at_utc', 'n/a')}\n"
        f"- gate_verdict: {gate.get('gate_verdict', 'n/a')}\n"
        f"- blocker_count: {gate.get('blocker_count', 'n/a')}\n"
        f"- release_readiness_gates: {readiness_index.get('passed_gates', 'n/a')}/{readiness_index.get('total_gates', 'n/a')}\n"
        f"- release_readiness_percent: {readiness_index.get('percent', 'n/a')}\n"
        f"- release_verdict: {(assessment.get('readiness') or {}).get('release_verdict', 'n/a')}\n"
        f"- demo_verdict: {(assessment.get('readiness') or {}).get('demo_verdict', 'n/a')}\n"
        f"- traceability_unhealthy_slice_count: {summary.get('unhealthy_slice_count', 'n/a')}\n"
        f"- traceability_closure_at_risk: {summary.get('closure_at_risk', 'n/a')}\n\n"
        "## Release Readiness Gates\n"
        f"{index_lines}\n\n"
        "## Blockers\n"
        f"{blocker_lines}\n"
    )
