from pathlib import Path

from siasa.readmodels.release_evidence import build_repo_release_gate_assessment, render_release_evidence_markdown


def test_build_repo_release_gate_assessment_is_go_for_current_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assessment = build_repo_release_gate_assessment(repo_root=repo_root)
    assert assessment["release_gate"]["gate_verdict"] == "go"
    assert assessment["release_gate"]["blockers"] == []


def test_render_release_evidence_markdown_contains_gate_summary() -> None:
    markdown = render_release_evidence_markdown(
        {
            "generated_at_utc": "2026-05-23T10:00:00+00:00",
            "release_gate": {"gate_verdict": "no_go", "blocker_count": 1, "blockers": ["known_gaps_clear"]},
            "readiness": {"release_verdict": "blocked_by_known_gaps", "demo_verdict": "ready"},
            "traceability_integrity": {"summary": {"unhealthy_slice_count": 0, "closure_at_risk": 0}},
        }
    )
    assert "SIASA Release Evidence Pack" in markdown
    assert "gate_verdict: no_go" in markdown
    assert "known_gaps_clear" in markdown
