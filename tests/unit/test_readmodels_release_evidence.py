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
            "readiness": {"release_verdict": "blocked_by_known_gaps", "demo_verdict": "ready"},
            "traceability_integrity": {"summary": {"unhealthy_slice_count": 0, "closure_at_risk": 0}},
            "stakeholder_e2e_flow_coverage": {"summary": {"flow_count": 6, "covered_flow_count": 5, "flow_gap_count": 1}},
        }
    )
    assert "SIASA Release Evidence Pack" in markdown
    assert "gate_verdict: no_go" in markdown
    assert "release_readiness_gates: 3/12" in markdown
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
