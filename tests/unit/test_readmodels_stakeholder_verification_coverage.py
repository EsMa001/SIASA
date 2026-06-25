from pathlib import Path

from siasa.readmodels.stakeholder_verification_coverage import (
    build_stakeholder_verification_coverage_report,
    render_stakeholder_verification_coverage_markdown,
)


def test_stakeholder_verification_coverage_report_covers_all_active_stakeholders() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    report = build_stakeholder_verification_coverage_report(repo_root=repo_root)

    assert report["metadata"]["work_package"] == "AP-03"
    assert report["summary"]["active_stakeholder_requirement_count"] == 681
    assert report["summary"]["stakeholder_verification_covered_count"] == 678
    assert report["summary"]["missing_stakeholder_verification_count"] == 3
    assert report["summary"]["system_requirement_count"] == 53
    assert report["summary"]["software_route_system_requirement_count"] == 30
    assert report["summary"]["governance_system_route_requirement_count"] == 20
    assert report["summary"]["accepted_software_requirement_count"] == 87
    assert report["summary"]["software_requirements_without_tc_count"] == 0
    assert report["summary"]["software_route_syrs_without_swr_count"] == 0

    by_id = {row["stakeholder_requirement_id"]: row for row in report["stakeholder_verification_rows"]}
    assert any(route["verification_route"] == "software_route" for route in by_id["StR-001"]["routes"])
    assert any(route["verification_route"] == "governance_system_route" for route in by_id["StR-003"]["routes"])


def test_stakeholder_verification_coverage_markdown_summarizes_ap03_boundary() -> None:
    report = {
        "summary": {
            "active_stakeholder_requirement_count": 166,
            "stakeholder_verification_covered_count": 668,
            "missing_stakeholder_verification_count": 3,
            "system_requirement_count": 53,
            "software_route_system_requirement_count": 30,
            "governance_system_route_requirement_count": 20,
            "accepted_software_requirement_count": 83,
            "software_requirements_without_tc_count": 0,
        },
        "stop_criteria": {"all_active_stakeholders_have_verification_route": False},
    }

    markdown = render_stakeholder_verification_coverage_markdown(report)

    assert "SIASA AP-03 Stakeholder Verification Coverage Report" in markdown
    assert "stakeholder_verification_covered_count: 668" in markdown
    assert "Flow-level E2E execution remains AP-04" in markdown
