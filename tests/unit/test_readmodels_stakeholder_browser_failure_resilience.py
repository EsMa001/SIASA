from pathlib import Path

from siasa.readmodels.stakeholder_browser_failure_resilience import build_stakeholder_browser_failure_resilience_report


def test_stakeholder_browser_failure_resilience_report_passes_for_current_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    report = build_stakeholder_browser_failure_resilience_report(repo_root=repo_root)

    assert report["metadata"]["work_package"] == "AP-13"
    assert report["summary"]["role_check_count"] >= 5
    assert report["summary"]["role_check_passed_count"] == report["summary"]["role_check_count"]
    assert report["summary"]["required_target_count"] >= 5
    assert report["summary"]["missing_required_target_count"] == 0
    assert report["summary"]["broken_internal_link_count"] == 0
    assert all(report["stop_criteria"].values())
