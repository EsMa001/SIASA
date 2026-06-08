from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class LiveProbePolicy:
    min_combined_ce_ratio: float = 0.5
    allowed_verdicts: tuple[str, ...] = ("green", "amber")
    max_failed_sources: int = 3
    max_countries_missing_both_ce: int = 0


def load_live_probe_policy_profile(*, policy_file: Path, profile: str) -> LiveProbePolicy:
    payload = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("policy file must contain a top-level mapping")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("policy file missing 'profiles' mapping")
    profile_payload = profiles.get(profile)
    if not isinstance(profile_payload, dict):
        raise ValueError(f"unknown live-probe policy profile: {profile}")
    min_combined_ce_ratio = float(profile_payload.get("min_combined_ce_ratio", 0.5))
    allowed_verdicts_raw = profile_payload.get("allowed_verdicts")
    if not isinstance(allowed_verdicts_raw, list) or not allowed_verdicts_raw:
        raise ValueError(f"profile '{profile}' must define non-empty allowed_verdicts list")
    allowed_verdicts = tuple(str(item) for item in allowed_verdicts_raw)
    max_failed_sources = int(profile_payload.get("max_failed_sources", 3))
    max_countries_missing_both_ce = int(profile_payload.get("max_countries_missing_both_ce", 0))
    return LiveProbePolicy(
        min_combined_ce_ratio=min_combined_ce_ratio,
        allowed_verdicts=allowed_verdicts,
        max_failed_sources=max_failed_sources,
        max_countries_missing_both_ce=max_countries_missing_both_ce,
    )


def evaluate_live_probe_digest_policy(
    digest: dict[str, Any], *, policy: LiveProbePolicy = LiveProbePolicy()
) -> dict[str, Any]:
    governance = digest.get("governance_summary") if isinstance(digest.get("governance_summary"), dict) else {}
    run_context = digest.get("run_context") if isinstance(digest.get("run_context"), dict) else {}
    ce_utilization = digest.get("ce_utilization") if isinstance(digest.get("ce_utilization"), dict) else {}

    verdict = str(governance.get("verdict", "unknown"))
    combined_ce_ratio = float(ce_utilization.get("combined_ce_ratio", 0.0) or 0.0)
    failed_source_count = int(run_context.get("failed_source_count", 0) or 0)
    countries_missing_both_ce = [
        str(item) for item in (ce_utilization.get("countries_missing_both_ce") or []) if str(item).strip()
    ]
    countries_missing_both_ce_count = len(countries_missing_both_ce)

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
    if countries_missing_both_ce_count > policy.max_countries_missing_both_ce:
        blockers.append(
            "countries_missing_both_ce_above_threshold:"
            f"{countries_missing_both_ce_count}>{policy.max_countries_missing_both_ce}:"
            f"{','.join(countries_missing_both_ce)}"
        )

    return {
        "gate_verdict": "pass" if not blockers else "fail",
        "blockers": blockers,
        "policy": {
            "min_combined_ce_ratio": policy.min_combined_ce_ratio,
            "allowed_verdicts": list(policy.allowed_verdicts),
            "max_failed_sources": policy.max_failed_sources,
            "max_countries_missing_both_ce": policy.max_countries_missing_both_ce,
        },
        "observed": {
            "governance_verdict": verdict,
            "combined_ce_ratio": round(combined_ce_ratio, 4),
            "failed_source_count": failed_source_count,
            "countries_missing_both_ce_count": countries_missing_both_ce_count,
            "countries_missing_both_ce": countries_missing_both_ce,
            "run_id": str(run_context.get("run_id", "unknown")),
            "run_status": str(run_context.get("run_status", "unknown")),
        },
    }
