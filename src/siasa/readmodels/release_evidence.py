from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from siasa.readmodels.functional_fulfillment import (
    estimate_functional_fulfillment_from_statuses,
    extract_capability_statuses_from_matrix_markdown,
)
from siasa.readmodels.readiness import build_readiness_view_model
from siasa.readmodels.release_gate import build_release_gate_view_model
from siasa.readmodels.stakeholder_browser_e2e_acceptance import build_stakeholder_browser_e2e_acceptance_report
from siasa.readmodels.stakeholder_browser_failure_resilience import build_stakeholder_browser_failure_resilience_report
from siasa.readmodels.stakeholder_browser_interaction_depth import build_stakeholder_browser_interaction_depth_report
from siasa.readmodels.stakeholder_e2e_flow_coverage import build_stakeholder_e2e_flow_coverage_report
from siasa.readmodels.stakeholder_e2e_ui_smoke import build_stakeholder_e2e_ui_smoke_report
from siasa.readmodels.stakeholder_functional_closure import build_stakeholder_functional_closure_report
from siasa.traceability.consistency import build_traceability_integrity_report


_REMEDIATION_HINTS_BY_GATE_ID: dict[str, str] = {
    "known_gaps_clear": "Resolve known gaps in readiness inputs or mark explicitly deferred with governance evidence.",
    "traceability_integrity_clean": "Run traceability consistency checks and close unhealthy slices before release.",
    "stakeholder_functional_focus_cluster_closed": "Close remaining stakeholder focus-cluster implementation gaps.",
    "stakeholder_e2e_flows_covered": "Add or repair missing stakeholder E2E flow evidence until flow-gap count is zero.",
    "stakeholder_e2e_ui_smoke_covered": "Regenerate local GUI bundle and fix missing role-flow smoke paths.",
    "stakeholder_browser_e2e_acceptance_covered": "Fix broken internal links or role-bundle navigation regressions in generated GUI pages.",
    "stakeholder_browser_interaction_depth_covered": "Repair broken click-path transitions and re-run interaction-depth checks.",
    "stakeholder_browser_failure_resilience_covered": "Add missing required targets and eliminate broken internal links in generated pages.",
    "stale_remediation_actionable": "Populate stale-country remediation actions with explicit action text and positive priority score.",
    "ci_gate_enforced": "Wire all release gate scripts into CI workflow execution path.",
    "evidence_pack_tooling_present": "Restore missing release gate/evidence scripts used by CI and release runbook.",
    "go_no_go_runbook_present": "Restore or create release go/no-go runbook documentation.",
}


def _build_operator_blocker_causality(*, release_gate: dict[str, Any], release_readiness_index: dict[str, Any]) -> dict[str, Any]:
    remediation_hints = _REMEDIATION_HINTS_BY_GATE_ID
    blocker_ids = [str(item) for item in (release_gate.get("blockers") or [])]
    readiness_gates = [item for item in (release_readiness_index.get("gates") or []) if isinstance(item, dict)]
    failed_gate_ids = [str(item.get("gate_id", "unknown")) for item in readiness_gates if not bool(item.get("passed", False))]
    gate_details = {str(item.get("gate_id", "unknown")): str(item.get("detail", "")) for item in readiness_gates}

    derived_gate_ids: list[str] = []
    for gate_id in blocker_ids + failed_gate_ids:
        if gate_id in {"release_gate_go", "release_verdict_ready"} and gate_id not in derived_gate_ids:
            derived_gate_ids.append(gate_id)

    root_cause_gate_ids: list[str] = []
    for gate_id in blocker_ids + failed_gate_ids:
        if gate_id in derived_gate_ids:
            continue
        if gate_id not in root_cause_gate_ids:
            root_cause_gate_ids.append(gate_id)

    causal_chain_rows: list[dict[str, str]] = []
    for gate_id in root_cause_gate_ids:
        causal_chain_rows.append(
            {
                "gate_id": gate_id,
                "gate_role": "root_cause",
                "causal_detail": gate_details.get(gate_id) or "direct blocker in readiness evidence",
                "remediation_hint": remediation_hints.get(gate_id, "Inspect release evidence and close failing gate condition."),
            }
        )
    for gate_id in derived_gate_ids:
        causal_chain_rows.append(
            {
                "gate_id": gate_id,
                "gate_role": "derived_effect",
                "causal_detail": "overall go/no-go remains blocked until root causes clear",
                "remediation_hint": remediation_hints.get(gate_id, "Inspect release evidence and close failing gate condition."),
            }
        )

    primary_root_cause_gate_id = root_cause_gate_ids[0] if root_cause_gate_ids else None
    return {
        "primary_root_cause_gate_id": primary_root_cause_gate_id,
        "root_cause_gate_ids": root_cause_gate_ids,
        "derived_gate_ids": derived_gate_ids,
        "operator_next_action": (
            remediation_hints.get(primary_root_cause_gate_id, "Inspect release evidence and close failing gate condition.")
            if primary_root_cause_gate_id
            else "No blocker-chain action required; release gates are green."
        ),
        "causal_chain_rows": causal_chain_rows,
    }


def _build_operator_operability_cluster(*, release_readiness_index: dict[str, Any]) -> dict[str, Any]:
    operability_gate_ids = [
        "stakeholder_e2e_flows_covered",
        "stakeholder_e2e_ui_smoke_covered",
        "stakeholder_browser_e2e_acceptance_covered",
        "stakeholder_browser_interaction_depth_covered",
        "stakeholder_browser_failure_resilience_covered",
    ]
    gate_group_by_id = {
        "stakeholder_e2e_flows_covered": "flow_definition",
        "stakeholder_e2e_ui_smoke_covered": "flow_rendering",
        "stakeholder_browser_e2e_acceptance_covered": "browser_acceptance",
        "stakeholder_browser_interaction_depth_covered": "interaction_depth",
        "stakeholder_browser_failure_resilience_covered": "failure_resilience",
    }
    cluster_role_by_id = {
        "stakeholder_e2e_flows_covered": "upstream_flow_spec",
        "stakeholder_e2e_ui_smoke_covered": "rendered_flow_presence",
        "stakeholder_browser_e2e_acceptance_covered": "bundle_navigation_acceptance",
        "stakeholder_browser_interaction_depth_covered": "deterministic_click_path",
        "stakeholder_browser_failure_resilience_covered": "negative_path_resilience",
    }

    readiness_gates = {
        str(item.get("gate_id", "unknown")): item
        for item in (release_readiness_index.get("gates") or [])
        if isinstance(item, dict)
    }
    cluster_rows: list[dict[str, Any]] = []
    failed_gate_ids: list[str] = []
    for gate_id in operability_gate_ids:
        gate = readiness_gates.get(gate_id, {})
        passed = bool(gate.get("passed", False))
        if not passed:
            failed_gate_ids.append(gate_id)
        cluster_rows.append(
            {
                "gate_id": gate_id,
                "gate_group": gate_group_by_id[gate_id],
                "cluster_role": cluster_role_by_id[gate_id],
                "passed": passed,
                "detail": str(gate.get("detail", "not_evaluated")),
                "remediation_hint": _REMEDIATION_HINTS_BY_GATE_ID.get(gate_id, "Inspect operability gate and repair failing condition."),
            }
        )

    return {
        "cluster_status": "healthy" if not failed_gate_ids else "degraded",
        "covered_gate_count": len(cluster_rows),
        "failed_gate_count": len(failed_gate_ids),
        "failed_gate_ids": failed_gate_ids,
        "operator_next_action": (
            _REMEDIATION_HINTS_BY_GATE_ID.get(failed_gate_ids[0], "Inspect operability gate and repair failing condition.")
            if failed_gate_ids
            else "No operability-cluster action required; stakeholder flows and browser gates are green."
        ),
        "cluster_rows": cluster_rows,
    }


def _build_operator_release_summary(*, release_gate: dict[str, Any], release_readiness_index: dict[str, Any]) -> dict[str, Any]:
    blocker_ids = [str(item) for item in (release_gate.get("blockers") or [])]
    readiness_gates = release_readiness_index.get("gates") or []
    gate_details = {
        str(item.get("gate_id")): str(item.get("detail", ""))
        for item in readiness_gates
        if isinstance(item, dict)
    }

    failed_readiness_gate_ids = [
        str(item.get("gate_id"))
        for item in readiness_gates
        if isinstance(item, dict) and not bool(item.get("passed", False))
    ]

    ordered_unique_failed_ids: list[str] = []
    for gate_id in blocker_ids + failed_readiness_gate_ids:
        if gate_id not in ordered_unique_failed_ids:
            ordered_unique_failed_ids.append(gate_id)

    failed_items = [
        {
            "gate_id": gate_id,
            "detail": gate_details.get(gate_id, "derived_from_release_gate_blockers"),
            "remediation_hint": _REMEDIATION_HINTS_BY_GATE_ID.get(gate_id, "Inspect release evidence and close failing gate condition."),
        }
        for gate_id in ordered_unique_failed_ids
    ]

    return {
        "release_gate_verdict": str(release_gate.get("gate_verdict", "unknown")),
        "failed_gate_count": len(failed_items),
        "failed_gates": failed_items,
        "operator_next_action": failed_items[0]["remediation_hint"] if failed_items else "No action required; release gates are green.",
    }


def _build_failure_drill_operator_digest(*, gate_diagnostics_export: dict[str, dict[str, Any]]) -> dict[str, Any]:
    clusters: list[dict[str, Any]] = []
    for gate_id, gate_slice in gate_diagnostics_export.items():
        failed_in_scenarios = gate_slice.get("failed_in_scenarios") or []
        scenario_ids = sorted({str(item.get("scenario_id", "")) for item in failed_in_scenarios if str(item.get("scenario_id", ""))})
        if not scenario_ids:
            continue
        clusters.append(
            {
                "gate_id": gate_id,
                "gate_label": str(gate_slice.get("gate_label", gate_id)),
                "scenario_count": len(scenario_ids),
                "scenario_ids": scenario_ids,
                "remediation_hint": str(gate_slice.get("remediation_hint", "Inspect scenario evidence and repair failing gate conditions.")),
            }
        )

    clusters.sort(key=lambda item: (-int(item.get("scenario_count", 0)), str(item.get("gate_id", ""))))
    return {
        "cluster_count": len(clusters),
        "clusters": clusters,
        "top_cluster_gate_id": (clusters[0]["gate_id"] if clusters else None),
        "operator_next_action": (
            clusters[0]["remediation_hint"] if clusters else "No failure-drill action required; no failing scenarios localized."
        ),
    }


def _build_failure_drill_trend_baseline(*, operator_failure_drill_digest: dict[str, Any]) -> dict[str, Any]:
    clusters = operator_failure_drill_digest.get("clusters") or []
    trend_rows: list[dict[str, Any]] = []
    for cluster in clusters:
        gate_id = str(cluster.get("gate_id", "unknown"))
        scenario_count = int(cluster.get("scenario_count", 0))
        trend_rows.append(
            {
                "gate_id": gate_id,
                "gate_label": str(cluster.get("gate_label", gate_id)),
                "scenario_count": scenario_count,
                "baseline_scenario_count": scenario_count,
                "trend_status": "baseline_established",
                "trajectory": "steady",
                "recurrence_ratio": 1.0,
                "scenario_ids": list(cluster.get("scenario_ids") or []),
                "remediation_hint": str(cluster.get("remediation_hint", "Inspect scenario evidence and repair failing gate conditions.")),
            }
        )

    trend_rows.sort(key=lambda item: (-int(item.get("scenario_count", 0)), str(item.get("gate_id", ""))))
    top_recurring_gate_id = trend_rows[0]["gate_id"] if trend_rows else None
    return {
        "snapshot_count": 1,
        "time_window": "single_snapshot_baseline",
        "trend_rows": trend_rows,
        "top_recurring_gate_id": top_recurring_gate_id,
        "operator_focus": (
            f"Establish follow-up snapshots and monitor drift for {top_recurring_gate_id}." if top_recurring_gate_id
            else "No recurring failed clusters in baseline snapshot."
        ),
    }


def _build_stale_remediation_closure_guardrails(*, coverage_visibility: dict[str, Any], actionability_sla_hours: float = 72.0) -> dict[str, Any]:
    stale_summary = coverage_visibility.get("stale_priority_summary") if isinstance(coverage_visibility.get("stale_priority_summary"), dict) else {}
    stale_country_count = int(stale_summary.get("stale_country_count", 0)) if stale_summary else 0
    remediation_watchlist = coverage_visibility.get("remediation_watchlist") if isinstance(coverage_visibility.get("remediation_watchlist"), list) else []

    breaches: list[dict[str, Any]] = []
    for item in remediation_watchlist:
        if not isinstance(item, dict):
            continue
        priority_score = item.get("priority_score")
        unresolved_age_hours = item.get("unresolved_age_hours")
        if not isinstance(priority_score, (int, float)) or float(priority_score) <= 0:
            breaches.append({"reason": "non_actionable_priority", "item": item})
            continue
        if isinstance(unresolved_age_hours, (int, float)) and float(unresolved_age_hours) > actionability_sla_hours:
            breaches.append({"reason": "sla_breach", "item": item})

    requires_closure = stale_country_count > 0
    closure_guarded = (not requires_closure) or (len(remediation_watchlist) > 0 and len(breaches) == 0)
    return {
        "requires_closure": requires_closure,
        "actionability_sla_hours": actionability_sla_hours,
        "closure_guarded": closure_guarded,
        "breach_count": len(breaches),
        "breaches": breaches,
    }


def _build_operator_stale_remediation_action_plan(*, stale_closure_guardrails: dict[str, Any]) -> dict[str, Any]:
    breaches = stale_closure_guardrails.get("breaches") if isinstance(stale_closure_guardrails.get("breaches"), list) else []
    sla_hours = float(stale_closure_guardrails.get("actionability_sla_hours", 72.0))
    action_templates = {
        "non_actionable_priority": {
            "action_category": "make_actionable",
            "recommended_action": "Raise stale-remediation priority above zero so the item becomes actionable.",
            "closure_check": "priority_score > 0",
        },
        "sla_breach": {
            "action_category": "close_overdue_action",
            "recommended_action": "Close or re-baseline the overdue stale-remediation action inside the SLA window.",
            "closure_check": f"unresolved_age_hours <= {sla_hours}",
        },
    }

    actions: list[dict[str, Any]] = []
    for index, breach in enumerate(breaches, start=1):
        if not isinstance(breach, dict):
            continue
        breach_reason = str(breach.get("reason", "unknown"))
        item = breach.get("item") if isinstance(breach.get("item"), dict) else {}
        template = action_templates.get(
            breach_reason,
            {
                "action_category": "triage",
                "recommended_action": "Inspect stale-remediation breach and restore a closure-safe action state.",
                "closure_check": "breach_resolved == true",
            },
        )
        actions.append(
            {
                "action_id": f"AP25-STALE-{index:02d}",
                "breach_reason": breach_reason,
                "action_category": template["action_category"],
                "recommended_action": template["recommended_action"],
                "execution_status": "next_up" if index == 1 else "queued",
                "closure_check": template["closure_check"],
                "priority_score": item.get("priority_score"),
                "unresolved_age_hours": item.get("unresolved_age_hours"),
            }
        )

    status_counts: dict[str, int] = {}
    for action in actions:
        status = str(action.get("execution_status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1

    next_action = actions[0] if actions else None
    return {
        "action_count": len(actions),
        "next_action_id": (next_action or {}).get("action_id"),
        "operator_next_action": (
            str((next_action or {}).get("recommended_action"))
            if next_action
            else "No stale-remediation action plan required."
        ),
        "status_counts": status_counts,
        "actions": actions,
    }


def _build_recurrence_aware_remediation_prioritization(
    *,
    trend_baseline: dict[str, Any],
    stale_closure_guardrails: dict[str, Any],
) -> dict[str, Any]:
    trend_rows = trend_baseline.get("trend_rows") if isinstance(trend_baseline.get("trend_rows"), list) else []
    breaches = stale_closure_guardrails.get("breaches") if isinstance(stale_closure_guardrails.get("breaches"), list) else []

    breach_by_reason: dict[str, int] = {}
    for breach in breaches:
        if not isinstance(breach, dict):
            continue
        reason = str(breach.get("reason", "unknown"))
        breach_by_reason[reason] = breach_by_reason.get(reason, 0) + 1

    priorities: list[dict[str, Any]] = []
    for idx, row in enumerate(trend_rows, start=1):
        if not isinstance(row, dict):
            continue
        gate_id = str(row.get("gate_id", "unknown"))
        scenario_count = int(row.get("scenario_count", 0))
        recurrence_ratio = float(row.get("recurrence_ratio", 0.0)) if isinstance(row.get("recurrence_ratio"), (int, float)) else 0.0

        urgency_boost = 0
        if gate_id == "stale_remediation_actionable":
            urgency_boost += breach_by_reason.get("sla_breach", 0) * 2
            urgency_boost += breach_by_reason.get("non_actionable_priority", 0)

        priority_score = scenario_count + recurrence_ratio + urgency_boost
        priorities.append(
            {
                "rank": idx,
                "gate_id": gate_id,
                "gate_label": str(row.get("gate_label", gate_id)),
                "scenario_count": scenario_count,
                "recurrence_ratio": recurrence_ratio,
                "trajectory": str(row.get("trajectory", "steady")),
                "urgency_boost": urgency_boost,
                "priority_score": round(priority_score, 2),
                "recommended_action": str(row.get("remediation_hint", "Inspect scenario evidence and close failing condition.")),
            }
        )

    priorities.sort(key=lambda item: (-float(item.get("priority_score", 0.0)), str(item.get("gate_id", ""))))
    for new_rank, item in enumerate(priorities, start=1):
        item["rank"] = new_rank

    top_priority = priorities[0] if priorities else None
    return {
        "model": "recurrence_x_urgency",
        "priority_count": len(priorities),
        "priorities": priorities,
        "top_priority_gate_id": (top_priority or {}).get("gate_id"),
        "top_priority_score": (top_priority or {}).get("priority_score"),
        "operator_next_action": (
            str((top_priority or {}).get("recommended_action"))
            if top_priority
            else "No prioritized remediation actions; no recurring failures detected."
        ),
    }


def _build_failure_drill_delta_ledger(
    *,
    current_trend_baseline: dict[str, Any],
    previous_report: dict[str, Any] | None,
) -> dict[str, Any]:
    current_rows_raw = current_trend_baseline.get("trend_rows") if isinstance(current_trend_baseline.get("trend_rows"), list) else []
    current_rows = [row for row in current_rows_raw if isinstance(row, dict)]

    previous_trend_baseline = {}
    if isinstance(previous_report, dict):
        maybe_previous_trend_baseline = previous_report.get("operator_failure_drill_trend_baseline")
        if isinstance(maybe_previous_trend_baseline, dict):
            previous_trend_baseline = maybe_previous_trend_baseline
    previous_rows_raw = previous_trend_baseline.get("trend_rows") if isinstance(previous_trend_baseline.get("trend_rows"), list) else []
    previous_rows = [row for row in previous_rows_raw if isinstance(row, dict)]

    current_by_gate = {str(row.get("gate_id", "unknown")): row for row in current_rows}
    previous_by_gate = {str(row.get("gate_id", "unknown")): row for row in previous_rows}

    has_prior_snapshot = len(previous_by_gate) > 0
    movement_summary = {
        "steady": 0,
        "regressed": 0,
        "improved": 0,
        "new_issue": 0,
        "resolved": 0,
    }
    delta_rows: list[dict[str, Any]] = []
    for gate_id in sorted(set(previous_by_gate) | set(current_by_gate)):
        current_row = current_by_gate.get(gate_id, {})
        previous_row = previous_by_gate.get(gate_id, {})

        current_scenario_count = int(current_row.get("scenario_count", 0)) if current_row else 0
        previous_scenario_count = int(previous_row.get("scenario_count", 0)) if previous_row else 0
        if not has_prior_snapshot:
            previous_scenario_count = current_scenario_count

        scenario_delta = current_scenario_count - previous_scenario_count
        if not has_prior_snapshot:
            movement_status = "steady"
        elif previous_scenario_count == 0 and current_scenario_count > 0:
            movement_status = "new_issue"
        elif previous_scenario_count > 0 and current_scenario_count == 0:
            movement_status = "resolved"
        elif scenario_delta > 0:
            movement_status = "regressed"
        elif scenario_delta < 0:
            movement_status = "improved"
        else:
            movement_status = "steady"

        movement_summary[movement_status] += 1
        gate_label = str(current_row.get("gate_label") or previous_row.get("gate_label") or gate_id)
        remediation_hint = str(
            current_row.get("remediation_hint")
            or previous_row.get("remediation_hint")
            or "Inspect scenario evidence and close failing gate condition."
        )
        current_recurrence_ratio = float(current_row.get("recurrence_ratio", 0.0)) if isinstance(current_row.get("recurrence_ratio"), (int, float)) else 0.0
        previous_recurrence_ratio = float(previous_row.get("recurrence_ratio", 0.0)) if isinstance(previous_row.get("recurrence_ratio"), (int, float)) else 0.0
        delta_rows.append(
            {
                "gate_id": gate_id,
                "gate_label": gate_label,
                "movement_status": movement_status,
                "current_scenario_count": current_scenario_count,
                "previous_scenario_count": previous_scenario_count,
                "scenario_delta": scenario_delta,
                "current_recurrence_ratio": round(current_recurrence_ratio, 3),
                "previous_recurrence_ratio": round(previous_recurrence_ratio, 3),
                "trajectory": str(current_row.get("trajectory") or previous_row.get("trajectory") or "steady"),
                "recommended_action": remediation_hint,
            }
        )

    movement_priority = {
        "new_issue": 0,
        "regressed": 1,
        "resolved": 2,
        "improved": 3,
        "steady": 4,
    }
    delta_rows.sort(
        key=lambda item: (
            movement_priority.get(str(item.get("movement_status", "steady")), 99),
            -abs(int(item.get("scenario_delta", 0))),
            str(item.get("gate_id", "")),
        )
    )

    regression_rows = [row for row in delta_rows if row.get("movement_status") in {"new_issue", "regressed"}]
    improvement_rows = [row for row in delta_rows if row.get("movement_status") in {"resolved", "improved"}]
    top_regression_gate_id = regression_rows[0]["gate_id"] if regression_rows else None
    top_improvement_gate_id = improvement_rows[0]["gate_id"] if improvement_rows else None

    if not has_prior_snapshot:
        operator_impact_narrative = "No prior AP-23 snapshot available; current release drill establishes the first delta baseline."
        comparison_mode = "no_prior_snapshot"
        snapshot_count = 1
    else:
        comparison_mode = "previous_report"
        prior_delta_ledger = previous_report.get("operator_failure_drill_delta_ledger") if isinstance(previous_report, dict) else {}
        prior_snapshot_count = 0
        if isinstance(prior_delta_ledger, dict):
            prior_snapshot_count = int(prior_delta_ledger.get("snapshot_count", 0))
        if prior_snapshot_count <= 0:
            prior_snapshot_count = max(1, int(previous_trend_baseline.get("snapshot_count", 1)))
        snapshot_count = prior_snapshot_count + 1
        if regression_rows:
            top_regression = regression_rows[0]
            operator_impact_narrative = (
                f"AP-23 snapshot delta shows strongest operator regression on {top_regression['gate_id']} "
                f"(Δscenarios={top_regression['scenario_delta']:+d}); prioritize {top_regression['recommended_action']}"
            )
            if top_improvement_gate_id:
                operator_impact_narrative += f" while preserving improvement on {top_improvement_gate_id}."
            else:
                operator_impact_narrative += "."
        elif improvement_rows:
            top_improvement = improvement_rows[0]
            operator_impact_narrative = (
                f"AP-23 snapshot delta shows net improvement on {top_improvement['gate_id']} "
                f"(Δscenarios={top_improvement['scenario_delta']:+d}); keep {top_improvement['recommended_action']} stable."
            )
        else:
            operator_impact_narrative = "AP-23 snapshot delta shows no gate movement; maintain current operator release controls."

    return {
        "comparison_mode": comparison_mode,
        "snapshot_count": snapshot_count,
        "movement_summary": movement_summary,
        "delta_rows": delta_rows,
        "top_regression_gate_id": top_regression_gate_id,
        "top_improvement_gate_id": top_improvement_gate_id,
        "operator_impact_narrative": operator_impact_narrative,
    }


def _build_operator_remediation_execution_loop(
    *,
    prioritization: dict[str, Any],
    delta_ledger: dict[str, Any],
    gate_diagnostics_export: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    priorities = prioritization.get("priorities") if isinstance(prioritization.get("priorities"), list) else []
    delta_rows = delta_ledger.get("delta_rows") if isinstance(delta_ledger.get("delta_rows"), list) else []
    delta_by_gate = {
        str(item.get("gate_id", "unknown")): item
        for item in delta_rows
        if isinstance(item, dict)
    }

    closure_target_by_movement = {
        "new_issue": "Reduce the new issue in the next AP-23 delta snapshot or resolve the gate entirely.",
        "regressed": "Reverse the regression in the next AP-23 delta snapshot by lowering scenario count.",
        "steady": "Clear the gate from the next AP-23 delta snapshot or reduce scenario count.",
        "improved": "Preserve the improvement and continue toward full gate clearance in the next AP-23 delta snapshot.",
        "resolved": "Keep the gate absent in the next AP-23 delta snapshot.",
    }

    actions: list[dict[str, Any]] = []
    for item in priorities:
        if not isinstance(item, dict):
            continue
        rank = int(item.get("rank", len(actions) + 1))
        gate_id = str(item.get("gate_id", "unknown"))
        delta_row = delta_by_gate.get(gate_id, {})
        movement_status = str(delta_row.get("movement_status", "steady"))
        action_token = "".join(char if char.isalnum() else "-" for char in gate_id.upper()).strip("-") or "UNKNOWN"
        failed_in_scenarios = []
        gate_slice = gate_diagnostics_export.get(gate_id)
        if isinstance(gate_slice, dict):
            maybe_failed_in_scenarios = gate_slice.get("failed_in_scenarios")
            if isinstance(maybe_failed_in_scenarios, list):
                failed_in_scenarios = [row for row in maybe_failed_in_scenarios if isinstance(row, dict)]
        actions.append(
            {
                "action_id": f"AP24-ACT-{rank:02d}-{action_token}",
                "priority_rank": rank,
                "gate_id": gate_id,
                "gate_label": str(item.get("gate_label", gate_id)),
                "priority_score": float(item.get("priority_score", 0.0)) if isinstance(item.get("priority_score"), (int, float)) else 0.0,
                "recommended_action": str(item.get("recommended_action", "Inspect scenario evidence and close failing condition.")),
                "current_movement_status": movement_status,
                "current_scenario_count": int(delta_row.get("current_scenario_count", item.get("scenario_count", 0))) if delta_row or item else 0,
                "execution_status": "next_up" if rank == 1 else "queued",
                "closure_target": closure_target_by_movement.get(movement_status, "Close the failing gate in the next AP-23 delta snapshot."),
                "closure_evidence_sources": [
                    "operator_failure_drill_delta_ledger",
                    "gate_diagnostics_export",
                ],
                "failed_scenario_count": len(failed_in_scenarios),
                "scenario_ids": sorted({str(row.get("scenario_id", "")) for row in failed_in_scenarios if str(row.get("scenario_id", ""))}),
            }
        )

    next_action = actions[0] if actions else None
    status_counts: dict[str, int] = {}
    for action in actions:
        status = str(action.get("execution_status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "model": "priority_to_action_trace_closure",
        "action_count": len(actions),
        "open_action_count": len(actions),
        "next_action_id": (next_action or {}).get("action_id"),
        "operator_next_action": (
            str((next_action or {}).get("recommended_action"))
            if next_action
            else "No AP-24 execution-loop actions required."
        ),
        "status_counts": status_counts,
        "actions": actions,
    }


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
    capability_fulfillment_percent_override: float | None = None,
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

    capability_fulfillment_percent = capability_fulfillment_percent_override
    capability_fulfillment_source = "override"
    if capability_fulfillment_percent is None:
        matrix_path = repo_root / "docs" / "plans" / "siasa-project-lead-capability-matrix.md"
        if matrix_path.exists():
            matrix_text = matrix_path.read_text(encoding="utf-8")
            statuses = extract_capability_statuses_from_matrix_markdown(matrix_text)
            if statuses:
                capability_fulfillment_percent = estimate_functional_fulfillment_from_statuses(statuses).weighted_percent
                capability_fulfillment_source = str(matrix_path.relative_to(repo_root))
    if capability_fulfillment_percent is None:
        capability_fulfillment_percent = 0.0
        capability_fulfillment_source = "unavailable"

    release_readiness_index_percent = float(release_readiness_index.get("percent", 0.0))
    metric_gap_percent = round(capability_fulfillment_percent - release_readiness_index_percent, 1)
    metrics_diverged = metric_gap_percent != 0.0
    operator_metric_warning = (
        "capability_fulfillment_percent exceeds release_readiness_index_percent; do not interpret capability closure as release-go"
        if metric_gap_percent > 0
        else (
            "release_readiness_index_percent exceeds capability_fulfillment_percent; verify capability matrix freshness"
            if metric_gap_percent < 0
            else ""
        )
    )
    operator_release_summary = _build_operator_release_summary(
        release_gate=release_gate,
        release_readiness_index=release_readiness_index,
    )
    operator_blocker_causality = _build_operator_blocker_causality(
        release_gate=release_gate,
        release_readiness_index=release_readiness_index,
    )
    operator_operability_cluster = _build_operator_operability_cluster(
        release_readiness_index=release_readiness_index,
    )

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "release_gate": release_gate,
        "release_readiness_index": release_readiness_index,
        "capability_fulfillment_percent": capability_fulfillment_percent,
        "release_readiness_index_percent": release_readiness_index_percent,
        "capability_vs_readiness": {
            "metrics_diverged": metrics_diverged,
            "metric_gap_percent": metric_gap_percent,
            "operator_warning": operator_metric_warning,
            "capability_fulfillment_source": capability_fulfillment_source,
        },
        "operator_release_summary": operator_release_summary,
        "operator_blocker_causality": operator_blocker_causality,
        "operator_operability_cluster": operator_operability_cluster,
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


def build_release_failure_drill_report(
    *,
    repo_root: Path,
    previous_report_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "remediation_watchlist": [
            {
                "severity": "high",
                "reason": "stale_source_window",
                "priority_score": 0,
                "remediation_action": "Escalate source refresh and rerun governed collection",
                "unresolved_age_hours": 24.0,
            },
            {
                "severity": "high",
                "reason": "stale_source_window",
                "priority_score": 10,
                "remediation_action": "Coordinate source-owner recovery window",
                "unresolved_age_hours": 120.0,
            }
        ],
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

    baseline_stale_guardrails = _build_stale_remediation_closure_guardrails(
        coverage_visibility=(baseline.get("readiness", {}).get("country_coverage_visibility", {}) if isinstance(baseline.get("readiness"), dict) else {}),
    )
    stale_remediation_closure_gap_guardrails = _build_stale_remediation_closure_guardrails(
        coverage_visibility=stale_remediation_visibility,
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
        "stale_remediation_closure_guardrails_triggered": (
            baseline_stale_guardrails.get("closure_guarded") is True
            and stale_remediation_closure_gap_guardrails.get("closure_guarded") is False
            and int(stale_remediation_closure_gap_guardrails.get("breach_count", 0)) > 0
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

    operator_failure_drill_digest = _build_failure_drill_operator_digest(
        gate_diagnostics_export=gate_diagnostics_export,
    )
    operator_failure_drill_trend_baseline = _build_failure_drill_trend_baseline(
        operator_failure_drill_digest=operator_failure_drill_digest,
    )
    operator_recurrence_aware_remediation_prioritization = _build_recurrence_aware_remediation_prioritization(
        trend_baseline=operator_failure_drill_trend_baseline,
        stale_closure_guardrails=stale_remediation_closure_gap_guardrails,
    )
    operator_failure_drill_delta_ledger = _build_failure_drill_delta_ledger(
        current_trend_baseline=operator_failure_drill_trend_baseline,
        previous_report=previous_report_override,
    )
    operator_remediation_execution_loop = _build_operator_remediation_execution_loop(
        prioritization=operator_recurrence_aware_remediation_prioritization,
        delta_ledger=operator_failure_drill_delta_ledger,
        gate_diagnostics_export=gate_diagnostics_export,
    )
    operator_stale_remediation_action_plan = _build_operator_stale_remediation_action_plan(
        stale_closure_guardrails=stale_remediation_closure_gap_guardrails,
    )
    checks["recurrence_aware_prioritization_nonempty"] = (
        int(operator_recurrence_aware_remediation_prioritization.get("priority_count", 0)) > 0
    )
    checks["delta_ledger_nonempty"] = int(operator_failure_drill_delta_ledger.get("snapshot_count", 0)) >= 1 and len(
        operator_failure_drill_delta_ledger.get("delta_rows", [])
    ) > 0
    checks["execution_loop_nonempty"] = int(operator_remediation_execution_loop.get("action_count", 0)) > 0
    checks["stale_action_plan_nonempty"] = int(operator_stale_remediation_action_plan.get("action_count", 0)) > 0

    return {
        "drill_verdict": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "scenarios": scenarios,
        "failure_localization": scenario_localization,
        "gate_diagnostics_export": gate_diagnostics_export,
        "operator_failure_drill_digest": operator_failure_drill_digest,
        "operator_failure_drill_trend_baseline": operator_failure_drill_trend_baseline,
        "operator_recurrence_aware_remediation_prioritization": operator_recurrence_aware_remediation_prioritization,
        "operator_failure_drill_delta_ledger": operator_failure_drill_delta_ledger,
        "operator_remediation_execution_loop": operator_remediation_execution_loop,
        "operator_stale_remediation_action_plan": operator_stale_remediation_action_plan,
        "operator_stale_remediation_closure_drill": {
            "baseline": baseline_stale_guardrails,
            "stale_remediation_gap_injected": stale_remediation_closure_gap_guardrails,
        },
    }


def render_release_evidence_markdown(assessment: dict[str, Any]) -> str:
    gate = assessment.get("release_gate", {})
    readiness_index = assessment.get("release_readiness_index", {})
    capability_vs_readiness = assessment.get("capability_vs_readiness", {}) or {}
    operator_release_summary = assessment.get("operator_release_summary", {}) or {}
    operator_blocker_causality = assessment.get("operator_blocker_causality", {}) or {}
    operator_operability_cluster = assessment.get("operator_operability_cluster", {}) or {}
    summary = ((assessment.get("traceability_integrity") or {}).get("summary") or {})
    e2e_summary = ((assessment.get("stakeholder_e2e_flow_coverage") or {}).get("summary") or {})
    blockers = [str(item) for item in gate.get("blockers", [])]
    blocker_lines = "\n".join(f"- {item}" for item in blockers) or "- none"
    index_lines = "\n".join(
        f"- {item.get('gate_id', 'unknown')}: {'pass' if item.get('passed') else 'fail'}"
        for item in readiness_index.get("gates", [])
    ) or "- none"
    operator_failed_lines = "\n".join(
        f"- {item.get('gate_id', 'unknown')}: {item.get('remediation_hint', 'n/a')}"
        for item in operator_release_summary.get("failed_gates", [])
    ) or "- none"
    blocker_causality_rows = "\n".join(
        f"- {item.get('gate_id', 'unknown')} [{item.get('gate_role', 'n/a')}]: {item.get('causal_detail', 'n/a')}"
        for item in operator_blocker_causality.get("causal_chain_rows", [])
    ) or "- none"
    operability_cluster_rows = "\n".join(
        f"- {item.get('gate_id', 'unknown')} [{item.get('gate_group', 'n/a')}/{item.get('cluster_role', 'n/a')}]: {'pass' if item.get('passed') else 'fail'}"
        for item in operator_operability_cluster.get("cluster_rows", [])
    ) or "- none"
    return (
        "# SIASA Release Evidence Pack\n\n"
        f"- generated_at_utc: {assessment.get('generated_at_utc', 'n/a')}\n"
        f"- gate_verdict: {gate.get('gate_verdict', 'n/a')}\n"
        f"- blocker_count: {gate.get('blocker_count', 'n/a')}\n"
        f"- release_readiness_gates: {readiness_index.get('passed_gates', 'n/a')}/{readiness_index.get('total_gates', 'n/a')}\n"
        f"- release_readiness_percent: {readiness_index.get('percent', 'n/a')}\n"
        f"- capability_fulfillment_percent: {assessment.get('capability_fulfillment_percent', 'n/a')}\n"
        f"- release_readiness_index_percent: {assessment.get('release_readiness_index_percent', 'n/a')}\n"
        f"- capability_vs_readiness_diverged: {capability_vs_readiness.get('metrics_diverged', 'n/a')}\n"
        f"- capability_vs_readiness_gap_percent: {capability_vs_readiness.get('metric_gap_percent', 'n/a')}\n"
        f"- capability_vs_readiness_warning: {capability_vs_readiness.get('operator_warning', '')}\n"
        f"- release_verdict: {(assessment.get('readiness') or {}).get('release_verdict', 'n/a')}\n"
        f"- demo_verdict: {(assessment.get('readiness') or {}).get('demo_verdict', 'n/a')}\n"
        f"- traceability_unhealthy_slice_count: {summary.get('unhealthy_slice_count', 'n/a')}\n"
        f"- traceability_closure_at_risk: {summary.get('closure_at_risk', 'n/a')}\n"
        f"- stakeholder_e2e_flow_coverage: {e2e_summary.get('covered_flow_count', 'n/a')}/{e2e_summary.get('flow_count', 'n/a')}\n"
        f"- stakeholder_e2e_flow_gap_count: {e2e_summary.get('flow_gap_count', 'n/a')}\n\n"
        "## Operator Release Summary\n"
        f"- failed_gate_count: {operator_release_summary.get('failed_gate_count', 'n/a')}\n"
        f"- operator_next_action: {operator_release_summary.get('operator_next_action', 'n/a')}\n"
        f"{operator_failed_lines}\n\n"
        "## Blocker Causality\n"
        f"- primary_root_cause_gate_id: {operator_blocker_causality.get('primary_root_cause_gate_id', 'n/a')}\n"
        f"- root_causes: {', '.join(operator_blocker_causality.get('root_cause_gate_ids', [])) or 'none'}\n"
        f"- derived_effects: {', '.join(operator_blocker_causality.get('derived_gate_ids', [])) or 'none'}\n"
        f"- operator_next_action: {operator_blocker_causality.get('operator_next_action', 'n/a')}\n"
        f"{blocker_causality_rows}\n\n"
        "## Operability Cluster\n"
        f"- cluster_status: {operator_operability_cluster.get('cluster_status', 'n/a')}\n"
        f"- covered_gate_count: {operator_operability_cluster.get('covered_gate_count', 'n/a')}\n"
        f"- failed_gate_count: {operator_operability_cluster.get('failed_gate_count', 'n/a')}\n"
        f"- failed_gate_ids: {', '.join(operator_operability_cluster.get('failed_gate_ids', [])) or 'none'}\n"
        f"- operator_next_action: {operator_operability_cluster.get('operator_next_action', 'n/a')}\n"
        f"{operability_cluster_rows}\n\n"
        "## Release Readiness Gates\n"
        f"{index_lines}\n\n"
        "## Blockers\n"
        f"{blocker_lines}\n"
    )
