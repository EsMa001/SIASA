from pathlib import Path

from siasa.readmodels.stakeholder_functional_closure import build_stakeholder_functional_closure_report


def test_stakeholder_functional_closure_report_covers_focus_gap_cluster() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_stakeholder_functional_closure_report(repo_root=repo_root)

    assert report["summary"]["functional_stakeholder_count"] >= 224
    assert report["summary"]["implemented_count"] > 0

    focus = report["focus_gap_cluster"]
    assert focus["covered_count"] == 19
    assert focus["implemented_count"] == 19
    assert focus["not_implemented_count"] == 0
    assert focus["not_implemented_ids"] == []


def test_stakeholder_functional_closure_report_includes_new_closure_swr_paths() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_stakeholder_functional_closure_report(repo_root=repo_root)
    by_id = {
        row["stakeholder_requirement_id"]: row
        for row in report["functional_stakeholder_closure"]
    }

    assert "SwR-046" in by_id["StR-001"]["software_requirements"]
    assert "SwR-046" in by_id["StR-002"]["software_requirements"]
    assert "SwR-047" in by_id["StR-007"]["software_requirements"]
    assert "SwR-048" in by_id["StR-024"]["software_requirements"]
    assert "SwR-049" in by_id["StR-135"]["software_requirements"]
    assert "SwR-050" in by_id["StR-140"]["software_requirements"]
    assert "SwR-051" in by_id["StR-142"]["software_requirements"]
    assert "TC-SwR-051-001" in by_id["StR-142"]["verifying_test_specs"]
