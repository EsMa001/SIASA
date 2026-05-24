from pathlib import Path

from siasa.readmodels.release_evidence import build_release_failure_drill_report


def test_release_failure_drill_report_detects_expected_failure_modes() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    report = build_release_failure_drill_report(repo_root=repo_root)

    assert report["drill_verdict"] == "pass"
    checks = report["checks"]
    assert checks["baseline_go"] is True
    assert checks["known_gap_no_go"] is True
    assert checks["known_gap_blocker_present"] is True
    assert checks["traceability_no_go"] is True
    assert checks["traceability_blocker_present"] is True
    assert checks["stakeholder_gate_fails"] is True
    assert checks["stakeholder_e2e_flow_gate_fails"] is True
    assert checks["stakeholder_e2e_ui_smoke_gate_fails"] is True
    assert checks["stakeholder_browser_e2e_gate_fails"] is True
    assert checks["stakeholder_browser_interaction_depth_gate_fails"] is True
    assert checks["stakeholder_browser_failure_resilience_gate_fails"] is True
    assert checks["stale_remediation_gate_fails"] is True
    assert checks["failure_localization_nonempty_for_injected_scenarios"] is True

    scenarios = report["scenarios"]
    assert set(scenarios.keys()) == {
        "baseline",
        "known_gap_injected",
        "traceability_closure_at_risk_injected",
        "stakeholder_focus_cluster_open_injected",
        "stakeholder_e2e_flow_gap_injected",
        "stakeholder_e2e_ui_smoke_gap_injected",
        "stakeholder_browser_e2e_gap_injected",
        "stakeholder_browser_interaction_depth_gap_injected",
        "stakeholder_browser_failure_resilience_gap_injected",
        "stale_remediation_gap_injected",
    }
    assert scenarios["baseline"]["release_gate"]["gate_verdict"] == "go"
    assert scenarios["known_gap_injected"]["release_gate"]["gate_verdict"] == "no_go"
    assert scenarios["traceability_closure_at_risk_injected"]["release_gate"]["gate_verdict"] == "no_go"

    stakeholder_scenario = scenarios["stakeholder_focus_cluster_open_injected"]
    stakeholder_gate = {
        item["gate_id"]: item["passed"]
        for item in stakeholder_scenario["release_readiness_index"]["gates"]
    }
    assert stakeholder_gate["stakeholder_functional_focus_cluster_closed"] is False

    e2e_scenario = scenarios["stakeholder_e2e_flow_gap_injected"]
    e2e_gate = {item["gate_id"]: item["passed"] for item in e2e_scenario["release_readiness_index"]["gates"]}
    assert e2e_gate["stakeholder_e2e_flows_covered"] is False

    e2e_ui_smoke_scenario = scenarios["stakeholder_e2e_ui_smoke_gap_injected"]
    e2e_ui_smoke_gate = {item["gate_id"]: item["passed"] for item in e2e_ui_smoke_scenario["release_readiness_index"]["gates"]}
    assert e2e_ui_smoke_gate["stakeholder_e2e_ui_smoke_covered"] is False

    browser_e2e_scenario = scenarios["stakeholder_browser_e2e_gap_injected"]
    browser_e2e_gate = {item["gate_id"]: item["passed"] for item in browser_e2e_scenario["release_readiness_index"]["gates"]}
    assert browser_e2e_gate["stakeholder_browser_e2e_acceptance_covered"] is False

    browser_interaction_depth_scenario = scenarios["stakeholder_browser_interaction_depth_gap_injected"]
    browser_interaction_depth_gate = {item["gate_id"]: item["passed"] for item in browser_interaction_depth_scenario["release_readiness_index"]["gates"]}
    assert browser_interaction_depth_gate["stakeholder_browser_interaction_depth_covered"] is False

    browser_failure_resilience_scenario = scenarios["stakeholder_browser_failure_resilience_gap_injected"]
    browser_failure_resilience_gate = {item["gate_id"]: item["passed"] for item in browser_failure_resilience_scenario["release_readiness_index"]["gates"]}
    assert browser_failure_resilience_gate["stakeholder_browser_failure_resilience_covered"] is False

    stale_scenario = scenarios["stale_remediation_gap_injected"]
    stale_gate = {item["gate_id"]: item["passed"] for item in stale_scenario["release_readiness_index"]["gates"]}
    assert stale_gate["stale_remediation_actionable"] is False

    failure_localization = report["failure_localization"]
    assert set(failure_localization.keys()) == set(scenarios.keys())
    assert failure_localization["baseline"] == []
    assert any(item["gate_id"] == "known_gaps_clear" for item in failure_localization["known_gap_injected"])
    assert any(item["gate_id"] == "traceability_integrity_clean" for item in failure_localization["traceability_closure_at_risk_injected"])
    assert any(
        item["gate_id"] == "stakeholder_browser_failure_resilience_covered" and "role-misrouting" in item["remediation_hint"]
        for item in failure_localization["stakeholder_browser_failure_resilience_gap_injected"]
    )
