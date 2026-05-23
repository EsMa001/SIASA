from pathlib import Path

from siasa.readmodels.stakeholder_e2e_flow_coverage import (
    build_stakeholder_e2e_flow_coverage_report,
    render_stakeholder_e2e_flow_coverage_markdown,
)


def test_stakeholder_e2e_flow_coverage_report_gates_prioritized_role_flows() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    report = build_stakeholder_e2e_flow_coverage_report(repo_root=repo_root)

    assert report["metadata"]["work_package"] == "AP-04"
    assert report["summary"]["flow_count"] == 6
    assert report["summary"]["covered_flow_count"] == 6
    assert report["summary"]["flow_gap_count"] == 0
    assert report["summary"]["covered_role_count"] == 4
    assert report["summary"]["required_role_count"] == 4
    assert report["summary"]["missing_evidence_ref_count"] == 0
    assert report["summary"]["missing_requirement_ref_count"] == 0
    assert all(report["stop_criteria"].values())

    by_id = {row["flow_id"]: row for row in report["flows"]}
    assert by_id["FLOW-PL-READINESS-GONO-001"]["failure_path_count"] >= 1
    assert by_id["FLOW-VIEWER-ROLE-BOUNDARY-001"]["role"] == "viewer"


def test_stakeholder_e2e_flow_coverage_markdown_summarizes_flow_boundary() -> None:
    report = {
        "summary": {
            "flow_count": 6,
            "covered_flow_count": 6,
            "flow_gap_count": 0,
            "covered_role_count": 4,
            "required_role_count": 4,
            "flows_with_happy_path_count": 6,
            "flows_with_failure_path_count": 6,
            "missing_evidence_ref_count": 0,
        },
        "stop_criteria": {"all_flows_covered": True},
    }

    markdown = render_stakeholder_e2e_flow_coverage_markdown(report)

    assert "SIASA AP-04 Stakeholder E2E Flow Coverage Report" in markdown
    assert "covered_flow_count: 6" in markdown
    assert "all_flows_covered: pass" in markdown
    assert "prioritized stakeholder-facing E2E flow evidence" in markdown
