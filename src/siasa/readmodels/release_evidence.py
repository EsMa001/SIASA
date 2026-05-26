from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from siasa.readmodels.readiness import build_readiness_view_model
from siasa.readmodels.release_gate import build_release_gate_view_model
from siasa.readmodels.stakeholder_browser_e2e_acceptance import build_stakeholder_browser_e2e_acceptance_report
from siasa.readmodels.stakeholder_browser_failure_resilience import build_stakeholder_browser_failure_resilience_report
from siasa.readmodels.stakeholder_browser_interaction_depth import build_stakeholder_browser_interaction_depth_report
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
    stakeholder_browser_e2e_acceptance_override: dict[str, Any] | None = None,
    stakeholder_browser_interaction_depth_override: dict[str, Any] | None = None,
    stakeholder_browser_failure_resilience_override: dict[str, Any] | None = None,
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
    stakeholder_browser_e2e_acceptance = stakeholder_browser_e2e_acceptance_override or build_stakeholder_browser_e2e_acceptance_report(repo_root=repo_root)
    stakeholder_browser_interaction_depth = stakeholder_browser_interaction_depth_override or build_stakeholder_browser_interaction_depth_report(repo_root=repo_root)
    stakeholder_browser_failure_resilience = stakeholder_browser_failure_resilience_override or build_stakeholder_browser_failure_resilience_report(repo_root=repo_root)
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
        stakeholder_browser_e2e_acceptance_report=stakeholder_browser_e2e_acceptance,
        stakeholder_browser_interaction_depth_report=stakeholder_browser_interaction_depth,
        stakeholder_browser_failure_resilience_report=stakeholder_browser_failure_resilience,
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
        "stakeholder_browser_e2e_acceptance": stakeholder_browser_e2e_acceptance,
        "stakeholder_browser_interaction_depth": stakeholder_browser_interaction_depth,
        "stakeholder_browser_failure_resilience": stakeholder_browser_failure_resilience,
    }


def build_release_readiness_index(
    *,
    repo_root: Path,
    release_gate_view_model: dict[str, Any],
    stakeholder_functional_closure_report: dict[str, Any],
    stakeholder_e2e_flow_coverage_report: dict[str, Any],
    stakeholder_e2e_ui_smoke_report: dict[str, Any] | None = None,
    stakeholder_browser_e2e_acceptance_report: dict[str, Any] | None = None,
    stakeholder_browser_interaction_depth_report: dict[str, Any] | None = None,
    stakeholder_browser_failure_resilience_report: dict[str, Any] | None = None,
    coverage_visibility_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workflow_path = repo_root / ".github" / "workflows" / "vmodel-ci.yml"
    runbook_path = repo_root / "docs" / "verification" / "release-go-no-go-runbook.md"
    evidence_script = repo_root / "scripts" / "build_release_evidence_pack.py"
    gate_script = repo_root / "scripts" / "ci_release_gate_check.py"
    e2e_flow_gate_script = repo_root / "scripts" / "ci_stakeholder_e2e_flow_coverage_check.py"
    e2e_ui_smoke_gate_script = repo_root / "scripts" / "ci_stakeholder_e2e_ui_smoke_check.py"
    browser_e2e_gate_script = repo_root / "scripts" / "ci_stakeholder_browser_e2e_acceptance_check.py"
    browser_interaction_depth_gate_script = repo_root / "scripts" / "ci_stakeholder_browser_interaction_depth_check.py"
    browser_failure_resilience_gate_script = repo_root / "scripts" / "ci_stakeholder_browser_failure_resilience_check.py"
    stale_remediation_gate_script = repo_root / "scripts" / "ci_stale_remediation_actionability_check.py"

    workflow_text = workflow_path.read_text(encoding="utf-8") if workflow_path.exists() else ""
    ci_gate_enforced = (
        "scripts/ci_release_gate_check.py" in workflow_text
        and "scripts/build_release_evidence_pack.py" in workflow_text
        and "scripts/ci_stakeholder_e2e_flow_coverage_check.py" in workflow_text
        and "scripts/ci_stakeholder_e2e_ui_smoke_check.py" in workflow_text
        and "scripts/ci_stakeholder_browser_e2e_acceptance_check.py" in workflow_text
        and "scripts/ci_stakeholder_browser_interaction_depth_check.py" in workflow_text
        and "scripts/ci_stakeholder_browser_failure_resilience_check.py" in workflow_text
        and "scripts/ci_stale_remediation_actionability_check.py" in workflow_text
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
    stakeholder_browser_e2e_acceptance = stakeholder_browser_e2e_acceptance_report or {
        "summary": {"bundle_count": 0, "broken_link_count": 1},
        "stop_criteria": {"not_evaluated": False},
    }
    stakeholder_browser_e2e_acceptance_covered = (
        int((stakeholder_browser_e2e_acceptance.get("summary") or {}).get("bundle_count", 0)) >= 3
        and int((stakeholder_browser_e2e_acceptance.get("summary") or {}).get("broken_link_count", 1)) == 0
        and all(bool(value) for value in (stakeholder_browser_e2e_acceptance.get("stop_criteria") or {}).values())
    )
    stakeholder_browser_interaction_depth = stakeholder_browser_interaction_depth_report or {
        "summary": {"transition_count": 0, "passed_transition_count": 0},
        "stop_criteria": {"not_evaluated": False},
    }
    stakeholder_browser_interaction_depth_covered = (
        int((stakeholder_browser_interaction_depth.get("summary") or {}).get("transition_count", 0)) > 0
        and int((stakeholder_browser_interaction_depth.get("summary") or {}).get("passed_transition_count", 0))
        == int((stakeholder_browser_interaction_depth.get("summary") or {}).get("transition_count", 0))
        and all(bool(value) for value in (stakeholder_browser_interaction_depth.get("stop_criteria") or {}).values())
    )
    stakeholder_browser_failure_resilience = stakeholder_browser_failure_resilience_report or {
        "summary": {"broken_internal_link_count": 1, "missing_required_target_count": 1},
        "stop_criteria": {"not_evaluated": False},
    }
    stakeholder_browser_failure_resilience_covered = (
        int((stakeholder_browser_failure_resilience.get("summary") or {}).get("broken_internal_link_count", 1)) == 0
        and int((stakeholder_browser_failure_resilience.get("summary") or {}).get("missing_required_target_count", 1)) == 0
        and all(bool(value) for value in (stakeholder_browser_failure_resilience.get("stop_criteria") or {}).values())
    )
    coverage_visibility = coverage_visibility_override or {}
    if not coverage_visibility:
        readiness_vm = release_gate_view_model.get("readiness")
        if isinstance(readiness_vm, dict):
            maybe_visibility = readiness_vm.get("country_coverage_visibility")
            if isinstance(maybe_visibility, dict):
                coverage_visibility = maybe_visibility
    stale_summary = coverage_visibility.get("stale_priority_summary") if isinstance(coverage_visibility.get("stale_priority_summary"), dict) else {}
    stale_watchlist = coverage_visibility.get("stale_priority_watchlist") if isinstance(coverage_visibility.get("stale_priority_watchlist"), list) else []
    remediation_watchlist = coverage_visibility.get("remediation_watchlist") if isinstance(coverage_visibility.get("remediation_watchlist"), list) else []
    stale_country_count = int(stale_summary.get("stale_country_count", 0)) if stale_summary else 0
    stale_remediation_actionable = (
        stale_country_count == 0
        or (
            len(stale_watchlist) > 0
            and all(bool(str(item.get("country_id", "")).strip()) for item in stale_watchlist if isinstance(item, dict))
            and len(remediation_watchlist) > 0
            and all(
                isinstance(item, dict)
                and bool(str(item.get("remediation_action", "")).strip())
                and isinstance(item.get("priority_score"), (int, float))
                and float(item.get("priority_score", 0)) > 0
                for item in remediation_watchlist
            )
        )
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
            "gate_id": "stakeholder_browser_e2e_acceptance_covered",
            "passed": stakeholder_browser_e2e_acceptance_covered,
            "detail": "browser E2E acceptance report has 3 role bundles, zero broken links, and all stop criteria pass",
        },
        {
            "gate_id": "stakeholder_browser_interaction_depth_covered",
            "passed": stakeholder_browser_interaction_depth_covered,
            "detail": "browser interaction-depth report has all configured click-path transitions passing",
        },
        {
            "gate_id": "stakeholder_browser_failure_resilience_covered",
            "passed": stakeholder_browser_failure_resilience_covered,
            "detail": "browser failure-resilience report has zero required-target misses, zero broken internal links, and all stop criteria pass",
        },
        {
            "gate_id": "stale_remediation_actionable",
            "passed": stale_remediation_actionable,
            "detail": "if stale_country_count>0 then stale watchlist and remediation actions with positive priority scores must be present",
        },
        {
            "gate_id": "ci_gate_enforced",
            "passed": ci_gate_enforced,
            "detail": str(workflow_path.relative_to(repo_root)),
        },
        {
            "gate_id": "evidence_pack_tooling_present",
            "passed": (
                evidence_script.exists()
                and gate_script.exists()
                and e2e_flow_gate_script.exists()
                and e2e_ui_smoke_gate_script.exists()
                and browser_e2e_gate_script.exists()
                and browser_interaction_depth_gate_script.exists()
                and browser_failure_resilience_gate_script.exists()
                and stale_remediation_gate_script.exists()
            ),
            "detail": "scripts/build_release_evidence_pack.py + scripts/ci_release_gate_check.py + scripts/ci_stakeholder_e2e_flow_coverage_check.py + scripts/ci_stakeholder_e2e_ui_smoke_check.py + scripts/ci_stakeholder_browser_e2e_acceptance_check.py + scripts/ci_stakeholder_browser_interaction_depth_check.py + scripts/ci_stakeholder_browser_failure_resilience_check.py + scripts/ci_stale_remediation_actionability_check.py",
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

    browser_e2e_gap = dict(baseline["stakeholder_browser_e2e_acceptance"])
    browser_e2e_gap["summary"] = dict(browser_e2e_gap.get("summary") or {})
    browser_e2e_gap["summary"]["broken_link_count"] = 1
    browser_e2e_gap["stop_criteria"] = dict(browser_e2e_gap.get("stop_criteria") or {})
    browser_e2e_gap["stop_criteria"]["no_broken_internal_links"] = False
    scenario_browser_e2e_gap = build_repo_release_gate_assessment(
        repo_root=repo_root,
        stakeholder_browser_e2e_acceptance_override=browser_e2e_gap,
    )

    browser_interaction_depth_gap = dict(baseline["stakeholder_browser_interaction_depth"])
    browser_interaction_depth_gap["summary"] = dict(browser_interaction_depth_gap.get("summary") or {})
    browser_interaction_depth_gap["summary"]["passed_transition_count"] = max(
        0,
        int(browser_interaction_depth_gap["summary"].get("passed_transition_count", 1)) - 1,
    )
    browser_interaction_depth_gap["stop_criteria"] = dict(browser_interaction_depth_gap.get("stop_criteria") or {})
    browser_interaction_depth_gap["stop_criteria"]["interaction_depth_transitions_closed"] = False
    scenario_browser_interaction_depth_gap = build_repo_release_gate_assessment(
        repo_root=repo_root,
        stakeholder_browser_interaction_depth_override=browser_interaction_depth_gap,
    )

    browser_failure_resilience_gap = dict(baseline["stakeholder_browser_failure_resilience"])
    browser_failure_resilience_gap["summary"] = dict(browser_failure_resilience_gap.get("summary") or {})
    browser_failure_resilience_gap["summary"]["broken_internal_link_count"] = 1
    browser_failure_resilience_gap["summary"]["missing_required_target_count"] = 1
    browser_failure_resilience_gap["stop_criteria"] = dict(browser_failure_resilience_gap.get("stop_criteria") or {})
    browser_failure_resilience_gap["stop_criteria"]["no_broken_internal_links_on_core_paths"] = False
    scenario_browser_failure_resilience_gap = build_repo_release_gate_assessment(
        repo_root=repo_root,
        stakeholder_browser_failure_resilience_override=browser_failure_resilience_gap,
    )

    stale_remediation_visibility = {
        "stale_priority_summary": {
            "stale_country_count": 1,
            "p1_stale_count": 1,
            "p2_stale_count": 0,
            "p3_stale_count": 0,
        },
        "stale_priority_watchlist": [{"country_id": "UKR", "priority": "P1", "freshness_hours": 720.0}],
        "remediation_watchlist": [{"severity": "high", "reason": "stale_source_window", "priority_score": 0}],
    }
    scenario_stale_remediation_gap = dict(baseline)
    scenario_stale_remediation_gap["release_readiness_index"] = build_release_readiness_index(
        repo_root=repo_root,
        release_gate_view_model=baseline["release_gate"],
        stakeholder_functional_closure_report=baseline["stakeholder_functional_closure"],
        stakeholder_e2e_flow_coverage_report=baseline["stakeholder_e2e_flow_coverage"],
        stakeholder_e2e_ui_smoke_report=baseline["stakeholder_e2e_ui_smoke"],
        stakeholder_browser_e2e_acceptance_report=baseline["stakeholder_browser_e2e_acceptance"],
        stakeholder_browser_interaction_depth_report=baseline["stakeholder_browser_interaction_depth"],
        stakeholder_browser_failure_resilience_report=baseline["stakeholder_browser_failure_resilience"],
        coverage_visibility_override=stale_remediation_visibility,
    )

    scenarios = {
        "baseline": baseline,
        "known_gap_injected": scenario_known_gaps,
        "traceability_closure_at_risk_injected": scenario_traceability_dirty,
        "stakeholder_focus_cluster_open_injected": scenario_stakeholder_open,
        "stakeholder_e2e_flow_gap_injected": scenario_e2e_flow_gap,
        "stakeholder_e2e_ui_smoke_gap_injected": scenario_e2e_ui_smoke_gap,
        "stakeholder_browser_e2e_gap_injected": scenario_browser_e2e_gap,
        "stakeholder_browser_interaction_depth_gap_injected": scenario_browser_interaction_depth_gap,
        "stakeholder_browser_failure_resilience_gap_injected": scenario_browser_failure_resilience_gap,
        "stale_remediation_gap_injected": scenario_stale_remediation_gap,
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
        "stakeholder_browser_e2e_gate_fails": any(
            (not bool(gate.get("passed"))) and gate.get("gate_id") == "stakeholder_browser_e2e_acceptance_covered"
            for gate in scenario_browser_e2e_gap["release_readiness_index"].get("gates", [])
        ),
        "stakeholder_browser_interaction_depth_gate_fails": any(
            (not bool(gate.get("passed"))) and gate.get("gate_id") == "stakeholder_browser_interaction_depth_covered"
            for gate in scenario_browser_interaction_depth_gap["release_readiness_index"].get("gates", [])
        ),
        "stakeholder_browser_failure_resilience_gate_fails": any(
            (not bool(gate.get("passed"))) and gate.get("gate_id") == "stakeholder_browser_failure_resilience_covered"
            for gate in scenario_browser_failure_resilience_gap["release_readiness_index"].get("gates", [])
        ),
        "stale_remediation_gate_fails": any(
            (not bool(gate.get("passed"))) and gate.get("gate_id") == "stale_remediation_actionable"
            for gate in scenario_stale_remediation_gap["release_readiness_index"].get("gates", [])
        ),
    }

    gate_labels = {
        "stakeholder_functional_focus_cluster_closed": "Stakeholder functional focus cluster closure",
        "stakeholder_e2e_flows_covered": "Stakeholder E2E flow coverage",
        "stakeholder_e2e_ui_smoke_covered": "Stakeholder E2E UI smoke coverage",
        "stakeholder_browser_e2e_acceptance_covered": "Stakeholder browser E2E acceptance",
        "stakeholder_browser_interaction_depth_covered": "Stakeholder browser interaction depth",
        "stakeholder_browser_failure_resilience_covered": "Stakeholder browser failure resilience",
        "stale_remediation_actionable": "Stale-remediation actionability",
        "known_gaps_clear": "Known-gaps clearance",
        "traceability_integrity_clean": "Traceability integrity",
    }
    remediation_hints = {
        "stakeholder_functional_focus_cluster_closed": "Close missing focus-cluster stakeholder mappings and rerun stakeholder closure checks.",
        "stakeholder_e2e_flows_covered": "Update stakeholder E2E flow definitions/evidence refs and ensure all required flow tests resolve.",
        "stakeholder_e2e_ui_smoke_covered": "Regenerate local GUI bundle and fix missing role-flow smoke paths.",
        "stakeholder_browser_e2e_acceptance_covered": "Fix broken internal links or role-bundle navigation regressions in generated GUI pages.",
        "stakeholder_browser_interaction_depth_covered": "Repair deterministic click-path transitions between overview/readiness/coverage/country/domain/validation/reports.",
        "stakeholder_browser_failure_resilience_covered": "Fix role-misrouting, required navigation targets, and core internal-link integrity on browser paths.",
        "stale_remediation_actionable": "Populate stale-country watchlist with actionable remediation entries and positive priority scores.",
        "known_gaps_clear": "Resolve readiness known gaps or explicitly scope/mitigate them before release decision.",
        "traceability_integrity_clean": "Close traceability integrity risks (unhealthy slices/closure-at-risk) before release.",
    }

    scenario_localization: dict[str, list[dict[str, str]]] = {}
    for scenario_id, scenario_assessment in scenarios.items():
        if scenario_id == "baseline":
            scenario_localization[scenario_id] = []
            continue

        failures: list[dict[str, str]] = []
        if scenario_assessment.get("release_gate", {}).get("gate_verdict") == "no_go":
            for blocker in scenario_assessment.get("release_gate", {}).get("blockers", []):
                blocker_id = str(blocker)
                failures.append(
                    {
                        "gate_id": blocker_id,
                        "gate_label": gate_labels.get(blocker_id, blocker_id),
                        "remediation_hint": remediation_hints.get(blocker_id, "Inspect scenario evidence and close the blocker condition."),
                    }
                )
        for gate in scenario_assessment.get("release_readiness_index", {}).get("gates", []):
            if not bool(gate.get("passed")):
                gate_id = str(gate.get("gate_id", "unknown"))
                failures.append(
                    {
                        "gate_id": gate_id,
                        "gate_label": gate_labels.get(gate_id, gate_id),
                        "remediation_hint": remediation_hints.get(gate_id, "Inspect scenario evidence and repair failing gate conditions."),
                    }
                )
        dedup: dict[str, dict[str, str]] = {item["gate_id"]: item for item in failures}
        scenario_localization[scenario_id] = list(dedup.values())

    checks["failure_localization_nonempty_for_injected_scenarios"] = all(
        len(entries) > 0 for key, entries in scenario_localization.items() if key != "baseline"
    )

    gate_diagnostics_export: dict[str, dict[str, Any]] = {}
    for scenario_id, scenario_assessment in scenarios.items():
        release_readiness_gates = {
            str(gate.get("gate_id", "unknown")): gate
            for gate in (scenario_assessment.get("release_readiness_index", {}).get("gates", []) or [])
        }
        release_gate_blockers = [
            str(blocker)
            for blocker in (scenario_assessment.get("release_gate", {}).get("blockers", []) or [])
        ]

        for failure in scenario_localization.get(scenario_id, []):
            gate_id = str(failure.get("gate_id", "unknown"))
            gate_slice = gate_diagnostics_export.setdefault(
                gate_id,
                {
                    "gate_id": gate_id,
                    "gate_label": failure.get("gate_label", gate_id),
                    "remediation_hint": failure.get("remediation_hint", "Inspect scenario evidence and repair failing gate conditions."),
                    "failed_in_scenarios": [],
                },
            )
            if scenario_id in [item.get("scenario_id") for item in gate_slice["failed_in_scenarios"]]:
                continue

            gate_entry = release_readiness_gates.get(gate_id, {})
            gate_slice["failed_in_scenarios"].append(
                {
                    "scenario_id": scenario_id,
                    "source": "release_gate_blocker" if gate_id in release_gate_blockers else "release_readiness_gate",
                    "detail": str(gate_entry.get("detail", "derived_from_release_gate_blockers")),
                    "passed": bool(gate_entry.get("passed", False)) if gate_entry else False,
                    "release_gate_verdict": str(scenario_assessment.get("release_gate", {}).get("gate_verdict", "unknown")),
                }
            )

    for gate_slice in gate_diagnostics_export.values():
        gate_slice["failed_in_scenarios"] = sorted(
            gate_slice["failed_in_scenarios"],
            key=lambda item: str(item.get("scenario_id", "")),
        )

    checks["gate_diagnostics_export_nonempty_for_failed_gates"] = all(
        bool(gate_slice.get("failed_in_scenarios"))
        for gate_slice in gate_diagnostics_export.values()
    )

    return {
        "drill_verdict": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "scenarios": scenarios,
        "failure_localization": scenario_localization,
        "gate_diagnostics_export": gate_diagnostics_export,
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
