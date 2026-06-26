from pathlib import Path

from siasa.readmodels.stakeholder_system_traceability import (
    build_stakeholder_system_traceability_report,
    render_stakeholder_system_traceability_markdown,
)


def test_stakeholder_system_traceability_report_covers_all_active_stakeholders() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    report = build_stakeholder_system_traceability_report(repo_root=repo_root)

    assert report["metadata"]["work_package"] == "AP-02"
    assert report["summary"]["active_stakeholder_requirement_count"] == 684
    assert report["summary"]["system_requirement_count"] == 53
    assert report["summary"]["covered_by_system_requirement_count"] == 684
    assert report["summary"]["covered_by_traceability_count"] == 684
    assert report["summary"]["missing_system_requirement_mapping_count"] == 0
    assert report["summary"]["missing_traceability_mapping_count"] == 0
    assert report["summary"]["syr_trace_mismatch_count"] == 0
    # Core coverage criteria must pass; orphan refs are a known historical artefact
    assert report["stop_criteria"]["all_active_stakeholders_have_system_requirement"] is True
    assert report["stop_criteria"]["all_active_stakeholders_have_traceability_link"] is True
    assert report["stop_criteria"]["system_and_traceability_links_match"] is True

    by_id = {row["stakeholder_requirement_id"]: row for row in report["rows"]}
    assert "SyR-031" in by_id["StR-003"]["system_requirements"]
    assert "SyR-007" in by_id["StR-008"]["system_requirements"]
    assert "SyR-007" in by_id["StR-672"]["system_requirements"]


def test_stakeholder_system_traceability_markdown_summarizes_stop_criteria() -> None:
    report = {
        "summary": {
            "active_stakeholder_requirement_count": 166,
            "system_requirement_count": 53,
            "covered_by_system_requirement_count": 166,
            "covered_by_traceability_count": 166,
            "missing_system_requirement_mapping_count": 0,
            "missing_traceability_mapping_count": 0,
            "syr_trace_mismatch_count": 0,
        },
        "stop_criteria": {"all_active_stakeholders_have_system_requirement": True},
    }

    markdown = render_stakeholder_system_traceability_markdown(report)

    assert "SIASA AP-02 Stakeholder-to-System Traceability Report" in markdown
    assert "covered_by_system_requirement_count: 166" in markdown
    assert "all_active_stakeholders_have_system_requirement: pass" in markdown
    assert "AP-03" in markdown
