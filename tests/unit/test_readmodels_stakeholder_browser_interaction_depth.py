from pathlib import Path

from siasa.readmodels.stakeholder_browser_interaction_depth import build_stakeholder_browser_interaction_depth_report


def test_stakeholder_browser_interaction_depth_report_passes_for_current_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    report = build_stakeholder_browser_interaction_depth_report(repo_root=repo_root)

    assert report["metadata"]["work_package"] == "AP-12"
    assert report["summary"]["transition_count"] >= 8
    assert report["summary"]["passed_transition_count"] == report["summary"]["transition_count"]
    assert report["summary"]["country_page_count"] > 0
    assert report["summary"]["domain_page_count"] > 0
    assert all(report["stop_criteria"].values())
