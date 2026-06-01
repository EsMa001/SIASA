from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LiveProbePolicy:
    min_combined_ce_ratio: float = 0.5
    allowed_verdicts: tuple[str, ...] = ("green", "amber")
    max_failed_sources: int = 3


def evaluate_live_probe_digest_policy(
    digest: dict[str, Any], *, policy: LiveProbePolicy = LiveProbePolicy()
) -> dict[str, Any]:
    governance = digest.get("governance_summary") if isinstance(digest.get("governance_summary"), dict) else {}
    run_context = digest.get("run_context") if isinstance(digest.get("run_context"), dict) else {}
    ce_utilization = digest.get("ce_utilization") if isinstance(digest.get("ce_utilization"), dict) else {}

    verdict = str(governance.get("verdict", "unknown"))
    combined_ce_ratio = float(ce_utilization.get("combined_ce_ratio", 0.0) or 0.0)
    failed_source_count = int(run_context.get("failed_source_count", 0) or 0)

    blockers: list[str] = []
    if verdict not in policy.allowed_verdicts:
        blockers.append(f"verdict_not_allowed:{verdict}")
    if combined_ce_ratio < policy.min_combined_ce_ratio:
        blockers.append(
            f"combined_ce_ratio_below_threshold:{combined_ce_ratio:.4f}<{policy.min_combined_ce_ratio:.4f}"
        )
    if failed_source_count > policy.max_failed_sources:
        blockers.append(
            f"failed_source_count_above_threshold:{failed_source_count}>{policy.max_failed_sources}"
        )

    return {
        "gate_verdict": "pass" if not blockers else "fail",
        "blockers": blockers,
        "policy": {
            "min_combined_ce_ratio": policy.min_combined_ce_ratio,
            "allowed_verdicts": list(policy.allowed_verdicts),
            "max_failed_sources": policy.max_failed_sources,
        },
        "observed": {
            "governance_verdict": verdict,
            "combined_ce_ratio": round(combined_ce_ratio, 4),
            "failed_source_count": failed_source_count,
            "run_id": str(run_context.get("run_id", "unknown")),
            "run_status": str(run_context.get("run_status", "unknown")),
        },
    }
