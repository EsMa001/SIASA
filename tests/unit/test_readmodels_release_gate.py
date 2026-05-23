from siasa.readmodels.release_gate import build_release_gate_view_model


def test_release_gate_is_go_for_clean_ready_inputs() -> None:
    gate = build_release_gate_view_model(
        readiness_view_model={
            "demo_verdict": "ready",
            "release_verdict": "ready",
            "known_gaps": [],
            "suppressed_known_gaps": [],
            "known_gap_suppression_reason": None,
        },
        traceability_integrity_report={
            "summary": {
                "missing_requirement_mapping_count": 0,
                "orphan_mapped_requirement_count": 0,
                "unhealthy_slice_count": 0,
                "closure_at_risk": 0,
            }
        },
    )
    assert gate["gate_verdict"] == "go"
    assert gate["blocker_count"] == 0
    assert gate["blockers"] == []


def test_release_gate_is_no_go_when_readiness_or_traceability_is_not_clean() -> None:
    gate = build_release_gate_view_model(
        readiness_view_model={
            "demo_verdict": "blocked",
            "release_verdict": "blocked_by_known_gaps",
            "known_gaps": ["failed_source:SRC-GDELT-DOC"],
            "suppressed_known_gaps": [],
            "known_gap_suppression_reason": None,
        },
        traceability_integrity_report={
            "summary": {
                "missing_requirement_mapping_count": 0,
                "orphan_mapped_requirement_count": 1,
                "unhealthy_slice_count": 0,
                "closure_at_risk": 0,
            }
        },
    )
    assert gate["gate_verdict"] == "no_go"
    assert set(gate["blockers"]) == {
        "demo_verdict_ready",
        "release_verdict_ready",
        "known_gaps_clear",
        "traceability_integrity_clean",
    }
