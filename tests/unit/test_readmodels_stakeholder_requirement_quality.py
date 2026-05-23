from pathlib import Path

from siasa.readmodels.stakeholder_requirement_quality import (
    build_stakeholder_requirement_quality_report,
    render_stakeholder_requirement_quality_markdown,
)


def test_stakeholder_requirement_quality_report_closes_ap01_quality_stop_criteria() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    report = build_stakeholder_requirement_quality_report(repo_root=repo_root)

    assert report["metadata"]["work_package"] == "AP-01"
    assert report["metadata"]["routing_primary_model"] == "5.5-class high-level review"
    assert report["summary"]["active_requirement_count"] == 668
    assert report["summary"]["quality_closed_count"] == 668
    assert report["summary"]["quality_gap_count"] == 0
    assert report["summary"]["canonical_acceptance_source_count"] == 375
    assert report["summary"]["ap01_policy_acceptance_source_count"] == 293
    assert report["summary"]["source_priority_tbd_count"] == 350
    assert all(report["stop_criteria"].values())

    by_id = {row["stakeholder_requirement_id"]: row for row in report["rows"]}
    assert by_id["StR-001"]["acceptance_source"] == "ap01_quality_policy"
    assert by_id["StR-013"]["acceptance_source"] == "canonical_ac"
    assert by_id["StR-001"]["effective_priority"] == "Backlog-Triage"


def test_stakeholder_requirement_quality_markdown_summarizes_boundary() -> None:
    report = {
        "summary": {
            "active_requirement_count": 668,
            "quality_closed_count": 668,
            "quality_gap_count": 0,
            "canonical_acceptance_source_count": 375,
            "ap01_policy_acceptance_source_count": 293,
            "source_priority_tbd_count": 350,
            "broad_language_requirement_count": 42,
        },
        "stop_criteria": {"core_fields_complete": True, "acceptance_source_assigned": True},
    }

    markdown = render_stakeholder_requirement_quality_markdown(report)

    assert "SIASA AP-01 Stakeholder Requirement Quality Report" in markdown
    assert "quality_closed_count: 668" in markdown
    assert "acceptance_source_assigned: pass" in markdown
    assert "does not claim product implementation closure" in markdown
