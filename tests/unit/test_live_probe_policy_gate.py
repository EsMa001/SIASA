from __future__ import annotations

from pathlib import Path

import pytest

from siasa.readmodels.live_probe_policy_gate import (
    LiveProbePolicy,
    evaluate_live_probe_digest_policy,
    load_live_probe_policy_profile,
)


def _digest(
    *,
    verdict: str = "green",
    ce_ratio: float = 1.0,
    failed_source_count: int = 0,
    countries_missing_both_ce: list[str] | None = None,
) -> dict:
    return {
        "governance_summary": {"verdict": verdict},
        "run_context": {
            "run_id": "RUN-CI-001",
            "run_status": "success",
            "failed_source_count": failed_source_count,
        },
        "ce_utilization": {
            "combined_ce_ratio": ce_ratio,
            "countries_missing_both_ce": countries_missing_both_ce or [],
        },
    }


def test_policy_gate_passes_for_allowed_verdict_and_ratio() -> None:
    result = evaluate_live_probe_digest_policy(_digest(verdict="amber", ce_ratio=0.75, failed_source_count=1))
    assert result["gate_verdict"] == "pass"
    assert result["blockers"] == []


def test_policy_gate_fails_when_verdict_not_allowed() -> None:
    result = evaluate_live_probe_digest_policy(
        _digest(verdict="amber", ce_ratio=0.8),
        policy=LiveProbePolicy(allowed_verdicts=("green",)),
    )
    assert result["gate_verdict"] == "fail"
    assert "verdict_not_allowed:amber" in result["blockers"]


def test_policy_gate_fails_when_ce_ratio_below_threshold() -> None:
    result = evaluate_live_probe_digest_policy(
        _digest(verdict="green", ce_ratio=0.2),
        policy=LiveProbePolicy(min_combined_ce_ratio=0.5),
    )
    assert result["gate_verdict"] == "fail"
    assert any(item.startswith("combined_ce_ratio_below_threshold") for item in result["blockers"])


def test_policy_gate_fails_when_too_many_failed_sources() -> None:
    result = evaluate_live_probe_digest_policy(
        _digest(verdict="green", ce_ratio=0.8, failed_source_count=5),
        policy=LiveProbePolicy(max_failed_sources=2),
    )
    assert result["gate_verdict"] == "fail"
    assert "failed_source_count_above_threshold:5>2" in result["blockers"]


def test_policy_gate_fails_when_too_many_countries_miss_both_ce() -> None:
    result = evaluate_live_probe_digest_policy(
        _digest(verdict="green", ce_ratio=0.8, countries_missing_both_ce=["POL", "SAU"]),
        policy=LiveProbePolicy(max_countries_missing_both_ce=1),
    )
    assert result["gate_verdict"] == "fail"
    assert "countries_missing_both_ce_above_threshold:2>1:POL,SAU" in result["blockers"]
    assert result["observed"]["countries_missing_both_ce_count"] == 2
    assert result["observed"]["countries_missing_both_ce"] == ["POL", "SAU"]


def test_load_policy_profile_standard_from_repo_file() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    policy = load_live_probe_policy_profile(
        policy_file=repo_root / "vmodel" / "project" / "live_probe_policy_profiles.yaml",
        profile="standard",
    )
    assert policy.min_combined_ce_ratio == 0.5
    assert policy.allowed_verdicts == ("green", "amber")
    assert policy.max_failed_sources == 3
    assert policy.max_countries_missing_both_ce == 1


def test_load_policy_profile_unknown_raises() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="unknown live-probe policy profile"):
        load_live_probe_policy_profile(
            policy_file=repo_root / "vmodel" / "project" / "live_probe_policy_profiles.yaml",
            profile="does-not-exist",
        )
