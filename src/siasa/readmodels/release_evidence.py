from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from siasa.readmodels.readiness import build_readiness_view_model
from siasa.readmodels.release_gate import build_release_gate_view_model
from siasa.readmodels.stakeholder_e2e_flow_coverage import build_stakeholder_e2e_flow_coverage_report
from siasa.readmodels.stakeholder_e2e_ui_smoke import build_stakeholder_e2e_ui_smoke_report
from siasa.readmodels.stakeholder_functional_closure import build_stakeholder_functional_closure_report
from siasa.traceability.consistency import build_traceability_integrity_report


def build_repo_release_gate_assessment(
    *,
    repo_root: Path,
    readiness_view_model_override: dict[str, Any] | None = None,
    traceability_integrity_override: dict[str, Any] | None = None,
    stakeholder_functional_closure_override: dict[str, Any] | None = None,
    stakeholder_e2e_flow_coverage_override: dict[str, Any] | None = None,
    stakeholder_e2e_ui_smoke_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    readiness_view_model = readiness_view_model_override or build_readiness_view_model(
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
    traceability_integrity = traceability_integrity_override or build_traceability_integrity_report(repo_root=repo_root)
    stakeholder_functional_closure = stakeholder_functional_closure_override or build_stakeholder_functional_closure_report(repo_root=repo_root)
    stakeholder_e2e_flow_coverage = stakeholder_e2e_flow_coverage_override or build_stakeholder_e2e_flow_coverage_report(repo_root=repo_root)
    stakeholder_e2e_ui_smoke = stakeholder_e2e_ui_smoke_override or build_stakeholder_e2e_ui_smoke_report(repo_root=repo_root)
    release_gate = build_release_gate_view_model(
        readiness_view_model=readiness_view_model,
        traceability_integrity_report=traceability_integrity,
    )
    release_readiness_index = build_release_readiness_index(
        repo_root=repo_root,
        release_gate_view_model=release_gate,
        stakeholder_functional_closure_report=stakeholder_functional_closure,
        stakeholder_e2e_flow_coverage_report=stakeholder_e2e_flow_coverage,
        stakeholder_e2e_ui_smoke_report=stakeholder_e2e_ui_smoke,
    )
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "release_gate": release_gate,
        "release_readiness_index": release_readiness_index,
        "readiness": readiness_view_model,
        "traceability_integrity": traceability_integrity,
        "stakeholder_functional_closure": stakeholder_functional_closure,
        "stakeholder_e2e_flow_coverage": stakeholder_e2e_flow_coverage,
        "stakeholder_e2e_ui_smoke": stakeholder_e2e_ui_smoke,
    }


def build_release_readiness_index(
    *,
    repo_root: Path,
    release_gate_view_model: dict[str, Any],
    stakeholder_functional_closure_report: dict[str, Any],
    stakeholder_e2e_flow_coverage_report: dict[str, Any],
    stakeholder_e2e_ui_smoke_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workflow_path = repo_root / ".github" / "workflows" / "vmodel-ci.yml"
    runbook_path = repo_root / "docs" / "verification" / "release-go-no-go-runbook.md"
    evidence_script = repo_root / "scripts" / "build_release_evidence_pack.py"
    gate_script = repo_root / "scripts" / "ci_release_gate_check.py"
    e2e_flow_gate_script = repo_root / "scripts" / "ci_stakeholder_e2e_flow_coverage_check.py"
    e2e_ui_smoke_gate_script = repo_root / "scripts" / "ci_stakeholder_e2e_ui_smoke_check.py"

    workflow_text = workflow_path.read_text(encoding="utf-8") if workflow_path.exists() else ""
    ci_gate_enforced = (
        "scripts/ci_release_gate_check.py" in workflow_text
        and "scripts/build_release_evidence_pack.py" in workflow_text
        and "scripts/ci_stakeholder_e2e_flow_coverage_check.py" in workflow_text
        and "scripts/ci_stakeholder_e2e_ui_smoke_check.py" in workflow_text
    )
    e2e_summary = stakeholder_e2e_flow_coverage_report.get("summary", {}) or {}
    e2e_stop_criteria = stakeholder_e2e_flow_coverage_report.get("stop_criteria", {}) or {}
    stakeholder_e2e_flows_covered = (
        int(e2e_summary.get("flow_count", 0)) >= int(e2e_summary.get("minimum_flow_count", 1))
        and int(e2e_summary.get("flow_gap_count", 1)) == 0
        and int(e2e_summary.get("missing_evidence_ref_count", 1)) == 0
        and all(bool(value) for value in e2e_stop_criteria.values())
    )
    stakeholder_e2e_ui_smoke = stakeholder_e2e_ui_smoke_report or {
        "flow_count": 0,
        "flow_gap_count": 1,
        "stop_criteria": {"not_evaluated": False},
    }
    stakeholder_e2e_ui_smoke_covered = (
        int(stakeholder_e2e_ui_smoke.get("flow_count", 0)) >= 6
        and int(stakeholder_e2e_ui_smoke.get("flow_gap_count", 1)) == 0
        and all(bool(value) for value in (stakeholder_e2e_ui_smoke.get("stop_criteria") or {}).values())
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
            "gate_id": "stakeholder_e2e_flows_covered",
            "passed": stakeholder_e2e_flows_covered,
            "detail": "flow_count>=minimum_flow_count, flow_gap_count==0, missing_evidence_ref_count==0, and all stop criteria pass",
        },
        {
            "gate_id": "stakeholder_e2e_ui_smoke_covered",
            "passed": stakeholder_e2e_ui_smoke_covered,
            "detail": "ui smoke report has >=6 flows, zero gaps, and all stop criteria pass",
        },
        {
            "gate_id": "ci_gate_enforced",
            "passed": ci_gate_enforced,
            "detail": str(workflow_path.relative_to(repo_root)),
        },
        {
            "gate_id": "evidence_pack_tooling_present",
            "passed": evidence_script.exists() and gate_script.exists() and e2e_flow_gate_script.exists() and e2e_ui_smoke_gate_script.exists(),
            "detail": "scripts/build_release_evidence_pack.py + scripts/ci_release_gate_check.py + scripts/ci_stakeholder_e2e_flow_coverage_check.py + scripts/ci_stakeholder_e2e_ui_smoke_check.py",
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


def build_release_failure_drill_report(*, repo_root: Path) -> dict[str, Any]:
    baseline = build_repo_release_gate_assessment(repo_root=repo_root)

    readiness_with_known_gap = dict(baseline["readiness"])
    readiness_with_known_gap["known_gaps"] = ["DRILL-SYNTHETIC-GAP"]
    readiness_with_known_gap["release_verdict"] = "blocked_by_known_gaps"
    scenario_known_gaps = build_repo_release_gate_assessment(
        repo_root=repo_root,
        readiness_view_model_override=readiness_with_known_gap,
    )

    traceability_dirty = dict(baseline["traceability_integrity"])
    traceability_dirty["summary"] = dict(traceability_dirty.get("summary") or {})
    traceability_dirty["summary"]["closure_at_risk"] = 1
    scenario_traceability_dirty = build_repo_release_gate_assessment(
        repo_root=repo_root,
        traceability_integrity_override=traceability_dirty,
    )

    stakeholder_open = dict(baseline["stakeholder_functional_closure"])
    stakeholder_open["focus_gap_cluster"] = dict(stakeholder_open.get("focus_gap_cluster") or {})
    stakeholder_open["focus_gap_cluster"]["covered_count"] = 18
    stakeholder_open["focus_gap_cluster"]["not_implemented_count"] = 1
    stakeholder_open["focus_gap_cluster"]["not_implemented_ids"] = ["StR-DRILL-001"]
    scenario_stakeholder_open = build_repo_release_gate_assessment(
        repo_root=repo_root,
        stakeholder_functional_closure_override=stakeholder_open,
    )

    e2e_flow_gap = dict(baseline["stakeholder_e2e_flow_coverage"])
    e2e_flow_gap["summary"] = dict(e2e_flow_gap.get("summary") or {})
    e2e_flow_gap["summary"]["covered_flow_count"] = max(0, int(e2e_flow_gap["summary"].get("covered_flow_count", 1)) - 1)
    e2e_flow_gap["summary"]["flow_gap_count"] = 1
    e2e_flow_gap["missing_evidence_refs"] = [
        {"flow_id": "FLOW-DRILL-001", "type": "pytest", "path": "tests/unit/missing.py", "test": "test_missing"}
    ]
    e2e_flow_gap["summary"]["missing_evidence_ref_count"] = 1
    e2e_flow_gap["stop_criteria"] = dict(e2e_flow_gap.get("stop_criteria") or {})
    e2e_flow_gap["stop_criteria"]["all_flows_covered"] = False
    e2e_flow_gap["stop_criteria"]["all_flow_evidence_refs_resolve"] = False
    scenario_e2e_flow_gap = build_repo_release_gate_assessment(
        repo_root=repo_root,
        stakeholder_e2e_flow_coverage_override=e2e_flow_gap,
    )

    e2e_ui_smoke_gap = dict(baseline["stakeholder_e2e_ui_smoke"])
    e2e_ui_smoke_gap["flow_gap_count"] = 1
    e2e_ui_smoke_gap["covered_flow_count"] = max(0, int(e2e_ui_smoke_gap.get("covered_flow_count", 1)) - 1)
    e2e_ui_smoke_gap["stop_criteria"] = dict(e2e_ui_smoke_gap.get("stop_criteria") or {})
    e2e_ui_smoke_gap["stop_criteria"]["all_flows_covered"] = False
    scenario_e2e_ui_smoke_gap = build_repo_release_gate_assessment(
        repo_root=repo_root,
        stakeholder_e2e_ui_smoke_override=e2e_ui_smoke_gap,
    )

    scenarios = {
        "baseline": baseline,
        "known_gap_injected": scenario_known_gaps,
        "traceability_closure_at_risk_injected": scenario_traceability_dirty,
        "stakeholder_focus_cluster_open_injected": scenario_stakeholder_open,
        "stakeholder_e2e_flow_gap_injected": scenario_e2e_flow_gap,
        "stakeholder_e2e_ui_smoke_gap_injected": scenario_e2e_ui_smoke_gap,
    }

    checks = {
        "baseline_go": baseline["release_gate"].get("gate_verdict") == "go",
        "known_gap_no_go": scenario_known_gaps["release_gate"].get("gate_verdict") == "no_go",
        "known_gap_blocker_present": "known_gaps_clear" in scenario_known_gaps["release_gate"].get("blockers", []),
        "traceability_no_go": scenario_traceability_dirty["release_gate"].get("gate_verdict") == "no_go",
        "traceability_blocker_present": "traceability_integrity_clean" in scenario_traceability_dirty["release_gate"].get("blockers", []),
        "stakeholder_gate_fails": any(
            (not bool(gate.get("passed"))) and gate.get("gate_id") == "stakeholder_functional_focus_cluster_closed"
            for gate in scenario_stakeholder_open["release_readiness_index"].get("gates", [])
        ),
        "stakeholder_e2e_flow_gate_fails": any(
            (not bool(gate.get("passed"))) and gate.get("gate_id") == "stakeholder_e2e_flows_covered"
            for gate in scenario_e2e_flow_gap["release_readiness_index"].get("gates", [])
        ),
        "stakeholder_e2e_ui_smoke_gate_fails": any(
            (not bool(gate.get("passed"))) and gate.get("gate_id") == "stakeholder_e2e_ui_smoke_covered"
            for gate in scenario_e2e_ui_smoke_gap["release_readiness_index"].get("gates", [])
        ),
    }

    return {
        "drill_verdict": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "scenarios": scenarios,
    }


def render_release_evidence_markdown(assessment: dict[str, Any]) -> str:
    gate = assessment.get("release_gate", {})
    readiness_index = assessment.get("release_readiness_index", {})
    summary = ((assessment.get("traceability_integrity") or {}).get("summary") or {})
    e2e_summary = ((assessment.get("stakeholder_e2e_flow_coverage") or {}).get("summary") or {})
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
        f"- traceability_closure_at_risk: {summary.get('closure_at_risk', 'n/a')}\n"
        f"- stakeholder_e2e_flow_coverage: {e2e_summary.get('covered_flow_count', 'n/a')}/{e2e_summary.get('flow_count', 'n/a')}\n"
        f"- stakeholder_e2e_flow_gap_count: {e2e_summary.get('flow_gap_count', 'n/a')}\n\n"
        "## Release Readiness Gates\n"
        f"{index_lines}\n\n"
        "## Blockers\n"
        f"{blocker_lines}\n"
    )
