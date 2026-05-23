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

    stakeholder_scenario = report["scenarios"]["stakeholder_focus_cluster_open_injected"]
    stakeholder_gate = {
        item["gate_id"]: item["passed"]
        for item in stakeholder_scenario["release_readiness_index"]["gates"]
    }
    assert stakeholder_gate["stakeholder_functional_focus_cluster_closed"] is False
