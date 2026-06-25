"""ALGO-RUNGATE-01 (AP-25): fail-loud gate for the analytical run stages.

Closes finding F10 (silent degradation). The daily-run orchestrator executes
seven optional analytical modules (rule engine, cross-domain fusion,
probabilistic scoring, uncertainty propagation, dependency graph, provenance
graph, information epidemiology). Each currently wraps its body in
``except Exception: log-and-continue``, so a thrown stage left no trace beyond a
log line — an empty result was indistinguishable from a genuinely-empty one.

This module turns each swallowed exception into an explicit degradation entry and
aggregates the entries into a deterministic run-level completeness verdict that is
surfaced via ``artifact_status`` and readiness (informational; release-blocking
severity remains project-owner authority).
"""
from __future__ import annotations

from typing import Any

# The seven analytical stages gated by ALGO-RUNGATE-01 (orchestrator stages a-g),
# in pipeline order. A legitimate ImportError (optional module absent) is a skip,
# not a degradation; only a thrown exception is recorded here.
ANALYTICAL_STAGES = (
    "rule_engine",
    "cross_domain_fusion",
    "probabilistic",
    "uncertainty_propagation",
    "dependency_graph",
    "provenance_graph",
    "info_epidemiology",
)


def record_degradation(degradations: list[dict[str, Any]], stage: str, exc: BaseException) -> None:
    """Append an explicit degradation entry for a swallowed analytical-stage exception."""
    degradations.append(
        {
            "stage": stage,
            "status": "degraded",
            "exception_type": type(exc).__name__,
            "reason": str(exc) or type(exc).__name__,
        }
    )


def build_analytical_completeness(degradations: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate analytical-stage degradations into a deterministic run-level gate.

    Returns ``status`` (``complete``/``degraded``), the sorted unique
    ``degraded_stages`` with their count, and the full ``entries`` ordered by
    stage so two identical runs yield bit-identical output.
    """
    entries = sorted(degradations, key=lambda entry: str(entry.get("stage", "")))
    degraded_stages = sorted({str(entry.get("stage", "")) for entry in entries if entry.get("stage")})
    return {
        "status": "degraded" if degraded_stages else "complete",
        "degraded_stage_count": len(degraded_stages),
        "degraded_stages": degraded_stages,
        "entries": entries,
    }
