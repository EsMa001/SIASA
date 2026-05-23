from pathlib import Path

from siasa.readmodels.release_evidence import build_repo_release_gate_assessment, render_release_evidence_markdown


def test_build_repo_release_gate_assessment_is_go_for_current_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assessment = build_repo_release_gate_assessment(repo_root=repo_root)
    assert assessment["release_gate"]["gate_verdict"] == "go"
    assert assessment["release_gate"]["blockers"] == []
    readiness_index = assessment["release_readiness_index"]
    assert readiness_index["total_gates"] == 6
    assert readiness_index["passed_gates"] == 6
    assert readiness_index["percent"] == 100.0
    gate_ids = [item["gate_id"] for item in readiness_index["gates"]]
    assert "stakeholder_functional_focus_cluster_closed" in gate_ids


def test_render_release_evidence_markdown_contains_gate_summary() -> None:
    markdown = render_release_evidence_markdown(
        {
            "generated_at_utc": "2026-05-23T10:00:00+00:00",
            "release_gate": {"gate_verdict": "no_go", "blocker_count": 1, "blockers": ["known_gaps_clear"]},
            "release_readiness_index": {
                "passed_gates": 3,
                "total_gates": 6,
                "percent": 50.0,
                "gates": [
                    {"gate_id": "release_gate_go", "passed": False},
                    {"gate_id": "stakeholder_functional_focus_cluster_closed", "passed": False},
                    {"gate_id": "go_no_go_runbook_present", "passed": True},
                ],
            },
            "readiness": {"release_verdict": "blocked_by_known_gaps", "demo_verdict": "ready"},
            "traceability_integrity": {"summary": {"unhealthy_slice_count": 0, "closure_at_risk": 0}},
        }
    )
    assert "SIASA Release Evidence Pack" in markdown
    assert "gate_verdict: no_go" in markdown
    assert "release_readiness_gates: 3/6" in markdown
    assert "release_gate_go: fail" in markdown
    assert "stakeholder_functional_focus_cluster_closed: fail" in markdown
    assert "known_gaps_clear" in markdown
