"""Unit tests for ALGO-RUNGATE-01 (AP-25): analytical-stage fail-loud gate.

Verifies SwR-044: a swallowed analytical-stage exception is recorded as an
explicit degradation entry and aggregated into a deterministic run-level
completeness verdict, instead of silently producing an empty result (F10).
"""
from __future__ import annotations

from siasa.runs.run_gate import (
    ANALYTICAL_STAGES,
    build_analytical_completeness,
    record_degradation,
)


def test_no_degradations_is_complete():
    gate = build_analytical_completeness([])
    assert gate["status"] == "complete"
    assert gate["degraded_stage_count"] == 0
    assert gate["degraded_stages"] == []
    assert gate["entries"] == []


def test_record_degradation_captures_stage_and_exception():
    degradations: list[dict] = []
    record_degradation(degradations, "cross_domain_fusion", ValueError("boom"))
    assert degradations == [
        {
            "stage": "cross_domain_fusion",
            "status": "degraded",
            "exception_type": "ValueError",
            "reason": "boom",
        }
    ]


def test_build_marks_degraded_with_sorted_unique_stages():
    degradations: list[dict] = []
    record_degradation(degradations, "probabilistic", RuntimeError("x"))
    record_degradation(degradations, "rule_engine", KeyError("k"))
    record_degradation(degradations, "probabilistic", RuntimeError("y"))  # duplicate stage
    gate = build_analytical_completeness(degradations)
    assert gate["status"] == "degraded"
    assert gate["degraded_stages"] == ["probabilistic", "rule_engine"]  # sorted, unique
    assert gate["degraded_stage_count"] == 2
    assert len(gate["entries"]) == 3  # every entry retained
    assert [e["stage"] for e in gate["entries"]] == ["probabilistic", "probabilistic", "rule_engine"]


def test_reason_falls_back_to_exception_type_when_message_empty():
    degradations: list[dict] = []
    record_degradation(degradations, "uncertainty_propagation", RuntimeError())
    assert degradations[0]["reason"] == "RuntimeError"


def test_known_analytical_stages_are_the_seven_orchestrator_modules():
    assert ANALYTICAL_STAGES == (
        "rule_engine",
        "cross_domain_fusion",
        "probabilistic",
        "uncertainty_propagation",
        "dependency_graph",
        "provenance_graph",
        "info_epidemiology",
    )
