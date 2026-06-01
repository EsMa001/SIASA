from __future__ import annotations

import argparse
import json
from pathlib import Path

from siasa.readmodels.live_probe_policy_gate import (
    LiveProbePolicy,
    evaluate_live_probe_digest_policy,
    load_live_probe_policy_profile,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate CI policy gate from live probe evidence digest")
    parser.add_argument(
        "--digest-path",
        type=Path,
        default=Path("build/run_artifacts/latest/readmodels/live_probe_evidence_digest.json"),
        help="Path to live probe evidence digest JSON",
    )
    parser.add_argument(
        "--policy-file",
        type=Path,
        default=Path("vmodel/project/live_probe_policy_profiles.yaml"),
        help="YAML file containing named live-probe governance policy profiles",
    )
    parser.add_argument(
        "--policy-profile",
        type=str,
        default="standard",
        help="Policy profile name from --policy-file (e.g., strict, standard, degraded)",
    )
    parser.add_argument(
        "--min-combined-ce-ratio",
        type=float,
        default=None,
        help="Optional override: minimum required combined C/E utilization ratio [0..1]",
    )
    parser.add_argument(
        "--allowed-verdicts",
        type=str,
        default=None,
        help="Optional override: comma-separated allowed governance verdicts (e.g., green or green,amber)",
    )
    parser.add_argument(
        "--max-failed-sources",
        type=int,
        default=None,
        help="Optional override: maximum allowed failed source count",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.digest_path.exists():
        print(json.dumps({"gate_verdict": "fail", "blockers": [f"digest_not_found:{args.digest_path}"]}, indent=2))
        return 1

    digest = json.loads(args.digest_path.read_text(encoding="utf-8"))
    policy = load_live_probe_policy_profile(policy_file=args.policy_file, profile=args.policy_profile)
    if args.min_combined_ce_ratio is not None:
        policy = LiveProbePolicy(
            min_combined_ce_ratio=float(args.min_combined_ce_ratio),
            allowed_verdicts=policy.allowed_verdicts,
            max_failed_sources=policy.max_failed_sources,
        )
    if args.allowed_verdicts is not None:
        allowed_verdicts = tuple(item.strip() for item in args.allowed_verdicts.split(",") if item.strip())
        policy = LiveProbePolicy(
            min_combined_ce_ratio=policy.min_combined_ce_ratio,
            allowed_verdicts=allowed_verdicts or policy.allowed_verdicts,
            max_failed_sources=policy.max_failed_sources,
        )
    if args.max_failed_sources is not None:
        policy = LiveProbePolicy(
            min_combined_ce_ratio=policy.min_combined_ce_ratio,
            allowed_verdicts=policy.allowed_verdicts,
            max_failed_sources=int(args.max_failed_sources),
        )
    evaluation = evaluate_live_probe_digest_policy(digest, policy=policy)
    print(json.dumps(evaluation, indent=2))
    return 0 if evaluation.get("gate_verdict") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
