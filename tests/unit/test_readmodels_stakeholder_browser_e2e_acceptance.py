from pathlib import Path

from siasa.readmodels.stakeholder_browser_e2e_acceptance import build_stakeholder_browser_e2e_acceptance_report


def test_stakeholder_browser_e2e_acceptance_report_passes_for_current_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    report = build_stakeholder_browser_e2e_acceptance_report(repo_root=repo_root)

    assert report["metadata"]["work_package"] == "AP-11"
    assert report["summary"]["bundle_count"] == 3
    assert report["summary"]["checked_link_count"] > 0
    assert report["summary"]["broken_link_count"] == 0
    assert all(report["stop_criteria"].values())
