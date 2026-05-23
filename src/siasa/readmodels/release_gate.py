from __future__ import annotations

from typing import Any


def build_release_gate_view_model(
    *,
    readiness_view_model: dict[str, Any],
    traceability_integrity_report: dict[str, Any] | None,
) -> dict[str, Any]:
    known_gaps = [str(item) for item in readiness_view_model.get("known_gaps", [])]
    suppressed_known_gaps = [str(item) for item in readiness_view_model.get("suppressed_known_gaps", [])]
    traceability_summary = (
        traceability_integrity_report.get("summary", {})
        if isinstance(traceability_integrity_report, dict)
        else {}
    )

    checks = [
        {
            "check_id": "demo_verdict_ready",
            "passed": readiness_view_model.get("demo_verdict") == "ready",
            "detail": str(readiness_view_model.get("demo_verdict", "unknown")),
        },
        {
            "check_id": "release_verdict_ready",
            "passed": readiness_view_model.get("release_verdict") == "ready",
            "detail": str(readiness_view_model.get("release_verdict", "unknown")),
        },
        {
            "check_id": "known_gaps_clear",
            "passed": len(known_gaps) == 0,
            "detail": f"known_gaps={len(known_gaps)}",
        },
        {
            "check_id": "traceability_integrity_clean",
            "passed": bool(traceability_summary)
            and int(traceability_summary.get("missing_requirement_mapping_count", 1)) == 0
            and int(traceability_summary.get("orphan_mapped_requirement_count", 1)) == 0
            and int(traceability_summary.get("unhealthy_slice_count", 1)) == 0
            and int(traceability_summary.get("closure_at_risk", 1)) == 0,
            "detail": {
                "missing_requirement_mapping_count": int(traceability_summary.get("missing_requirement_mapping_count", -1)),
                "orphan_mapped_requirement_count": int(traceability_summary.get("orphan_mapped_requirement_count", -1)),
                "unhealthy_slice_count": int(traceability_summary.get("unhealthy_slice_count", -1)),
                "closure_at_risk": int(traceability_summary.get("closure_at_risk", -1)),
            },
        },
    ]

    blockers = [str(check["check_id"]) for check in checks if not bool(check["passed"])]
    gate_verdict = "go" if not blockers else "no_go"
    return {
        "gate_verdict": gate_verdict,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "checks": checks,
        "known_gaps": known_gaps,
        "suppressed_known_gaps": suppressed_known_gaps,
        "known_gap_suppression_reason": readiness_view_model.get("known_gap_suppression_reason"),
    }
