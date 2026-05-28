from pathlib import Path

from siasa.readmodels.release_evidence import build_repo_release_gate_assessment, render_release_evidence_markdown


def test_build_repo_release_gate_assessment_is_go_for_current_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assessment = build_repo_release_gate_assessment(
        repo_root=repo_root,
        stakeholder_e2e_ui_smoke_override={
            "flow_count": 6,
            "flow_gap_count": 0,
            "stop_criteria": {"all_flows_covered": True, "all_roles_covered": True},
        },
        stakeholder_browser_e2e_acceptance_override={
            "summary": {"bundle_count": 3, "broken_link_count": 0},
            "stop_criteria": {"role_bundle_count_met": True, "no_broken_internal_links": True},
        },
    )
    assert assessment["release_gate"]["gate_verdict"] == "go"
    assert assessment["release_gate"]["blockers"] == []
    readiness_index = assessment["release_readiness_index"]
    assert readiness_index["total_gates"] == 12
    assert readiness_index["passed_gates"] == 12
    assert readiness_index["percent"] == 100.0
    assert assessment["capability_fulfillment_percent"] == 100.0
    assert assessment["release_readiness_index_percent"] == 100.0
    assert assessment["capability_vs_readiness"]["metrics_diverged"] is False
    assert assessment["capability_vs_readiness"]["metric_gap_percent"] == 0.0
    operator_summary = assessment["operator_release_summary"]
    assert operator_summary["release_gate_verdict"] == "go"
    assert operator_summary["failed_gate_count"] == 0
    assert operator_summary["operator_next_action"] == "No action required; release gates are green."
    blocker_causality = assessment["operator_blocker_causality"]
    assert blocker_causality["primary_root_cause_gate_id"] is None
    assert blocker_causality["root_cause_gate_ids"] == []
    assert blocker_causality["derived_gate_ids"] == []
    assert blocker_causality["operator_next_action"] == "No blocker-chain action required; release gates are green."
    operability_cluster = assessment["operator_operability_cluster"]
    assert operability_cluster["cluster_status"] == "healthy"
    assert operability_cluster["covered_gate_count"] == 5
    assert operability_cluster["failed_gate_count"] == 0
    assert operability_cluster["operator_next_action"] == "No operability-cluster action required; stakeholder flows and browser gates are green."
    gate_ids = [item["gate_id"] for item in readiness_index["gates"]]
    assert "stakeholder_functional_focus_cluster_closed" in gate_ids
    assert "stakeholder_e2e_flows_covered" in gate_ids
    assert "stakeholder_e2e_ui_smoke_covered" in gate_ids
    assert "stakeholder_browser_e2e_acceptance_covered" in gate_ids
    assert "stakeholder_browser_interaction_depth_covered" in gate_ids
    assert "stakeholder_browser_failure_resilience_covered" in gate_ids
    assert "stale_remediation_actionable" in gate_ids
    assert assessment["stakeholder_e2e_flow_coverage"]["summary"]["covered_flow_count"] == 6
    assert assessment["stakeholder_e2e_flow_coverage"]["summary"]["flow_gap_count"] == 0


def test_render_release_evidence_markdown_contains_gate_summary() -> None:
    markdown = render_release_evidence_markdown(
        {
            "generated_at_utc": "2026-05-23T10:00:00+00:00",
            "release_gate": {"gate_verdict": "no_go", "blocker_count": 1, "blockers": ["known_gaps_clear"]},
            "release_readiness_index": {
                "passed_gates": 3,
                "total_gates": 12,
                "percent": 42.9,
                "gates": [
                    {"gate_id": "release_gate_go", "passed": False},
                    {"gate_id": "stakeholder_functional_focus_cluster_closed", "passed": False},
                    {"gate_id": "stakeholder_e2e_flows_covered", "passed": False},
                    {"gate_id": "stakeholder_e2e_ui_smoke_covered", "passed": False},
                    {"gate_id": "stakeholder_browser_e2e_acceptance_covered", "passed": False},
                    {"gate_id": "stakeholder_browser_interaction_depth_covered", "passed": False},
                    {"gate_id": "stakeholder_browser_failure_resilience_covered", "passed": False},
                    {"gate_id": "stale_remediation_actionable", "passed": False},
                    {"gate_id": "go_no_go_runbook_present", "passed": True},
                ],
            },
            "capability_fulfillment_percent": 100.0,
            "release_readiness_index_percent": 42.9,
            "capability_vs_readiness": {
                "metrics_diverged": True,
                "metric_gap_percent": 57.1,
                "operator_warning": "capability_fulfillment_percent exceeds release_readiness_index_percent; do not interpret capability closure as release-go",
            },
            "operator_release_summary": {
                "failed_gate_count": 2,
                "operator_next_action": "Regenerate local GUI bundle and fix missing role-flow smoke paths.",
                "failed_gates": [
                    {
                        "gate_id": "stakeholder_e2e_ui_smoke_covered",
                        "remediation_hint": "Regenerate local GUI bundle and fix missing role-flow smoke paths.",
                    },
                    {
                        "gate_id": "stakeholder_browser_e2e_acceptance_covered",
                        "remediation_hint": "Fix broken internal links or role-bundle navigation regressions in generated GUI pages.",
                    },
                ],
            },
            "operator_blocker_causality": {
                "primary_root_cause_gate_id": "known_gaps_clear",
                "root_cause_gate_ids": ["known_gaps_clear", "stakeholder_e2e_ui_smoke_covered"],
                "derived_gate_ids": ["release_gate_go"],
                "operator_next_action": "Resolve readiness known gaps or explicitly scope/mitigate them before release decision.",
                "causal_chain_rows": [
                    {"gate_id": "known_gaps_clear", "gate_role": "root_cause", "causal_detail": "direct blocker in readiness evidence"},
                    {"gate_id": "release_gate_go", "gate_role": "derived_effect", "causal_detail": "overall go/no-go remains blocked until root causes clear"},
                ],
            },
            "operator_operability_cluster": {
                "cluster_status": "degraded",
                "covered_gate_count": 5,
                "failed_gate_count": 2,
                "failed_gate_ids": ["stakeholder_e2e_ui_smoke_covered", "stakeholder_browser_e2e_acceptance_covered"],
                "operator_next_action": "Regenerate local GUI bundle and fix missing role-flow smoke paths.",
                "cluster_rows": [
                    {"gate_id": "stakeholder_e2e_flows_covered", "gate_group": "flow_definition", "passed": True, "cluster_role": "upstream_flow_spec"},
                    {"gate_id": "stakeholder_e2e_ui_smoke_covered", "gate_group": "flow_rendering", "passed": False, "cluster_role": "rendered_flow_presence"},
                    {"gate_id": "stakeholder_browser_e2e_acceptance_covered", "gate_group": "browser_acceptance", "passed": False, "cluster_role": "bundle_navigation_acceptance"},
                ],
            },
            "readiness": {"release_verdict": "blocked_by_known_gaps", "demo_verdict": "ready"},
            "traceability_integrity": {"summary": {"unhealthy_slice_count": 0, "closure_at_risk": 0}},
            "stakeholder_e2e_flow_coverage": {"summary": {"flow_count": 6, "covered_flow_count": 5, "flow_gap_count": 1}},
        }
    )
    assert "SIASA Release Evidence Pack" in markdown
    assert "gate_verdict: no_go" in markdown
    assert "release_readiness_gates: 3/12" in markdown
    assert "capability_fulfillment_percent: 100.0" in markdown
    assert "release_readiness_index_percent: 42.9" in markdown
    assert "capability_vs_readiness_diverged: True" in markdown
    assert "capability_vs_readiness_gap_percent: 57.1" in markdown
    assert "## Operator Release Summary" in markdown
    assert "failed_gate_count: 2" in markdown
    assert "operator_next_action: Regenerate local GUI bundle and fix missing role-flow smoke paths." in markdown
    assert "## Blocker Causality" in markdown
    assert "primary_root_cause_gate_id: known_gaps_clear" in markdown
    assert "root_causes: known_gaps_clear, stakeholder_e2e_ui_smoke_covered" in markdown
    assert "derived_effects: release_gate_go" in markdown
    assert "known_gaps_clear [root_cause]: direct blocker in readiness evidence" in markdown
    assert "release_gate_go [derived_effect]: overall go/no-go remains blocked until root causes clear" in markdown
    assert "## Operability Cluster" in markdown
    assert "cluster_status: degraded" in markdown
    assert "failed_gate_count: 2" in markdown
    assert "failed_gate_ids: stakeholder_e2e_ui_smoke_covered, stakeholder_browser_e2e_acceptance_covered" in markdown
    assert "stakeholder_e2e_ui_smoke_covered [flow_rendering/rendered_flow_presence]: fail" in markdown
    assert "stakeholder_browser_e2e_acceptance_covered [browser_acceptance/bundle_navigation_acceptance]: fail" in markdown
    assert "release_gate_go: fail" in markdown
    assert "stakeholder_functional_focus_cluster_closed: fail" in markdown
    assert "stakeholder_e2e_flows_covered: fail" in markdown
    assert "stakeholder_e2e_ui_smoke_covered: fail" in markdown
    assert "stakeholder_browser_e2e_acceptance_covered: fail" in markdown
    assert "stakeholder_browser_interaction_depth_covered: fail" in markdown
    assert "stakeholder_browser_failure_resilience_covered: fail" in markdown
    assert "stale_remediation_actionable: fail" in markdown
    assert "stakeholder_e2e_flow_coverage: 5/6" in markdown
    assert "stakeholder_e2e_flow_gap_count: 1" in markdown
    assert "known_gaps_clear" in markdown
