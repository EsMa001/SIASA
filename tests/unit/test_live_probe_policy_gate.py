from __future__ import annotations

from siasa.readmodels.live_probe_policy_gate import LiveProbePolicy, evaluate_live_probe_digest_policy


def _digest(*, verdict: str = "green", ce_ratio: float = 1.0, failed_source_count: int = 0) -> dict:
    return {
        "governance_summary": {"verdict": verdict},
        "run_context": {
            "run_id": "RUN-CI-001",
            "run_status": "success",
            "failed_source_count": failed_source_count,
        },
        "ce_utilization": {"combined_ce_ratio": ce_ratio},
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
