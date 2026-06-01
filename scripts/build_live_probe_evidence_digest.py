from __future__ import annotations

import argparse
import json
from pathlib import Path

from siasa.readmodels.live_probe_evidence_digest import build_live_probe_evidence_digest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build compact CI live-probe evidence digest readmodel")
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("build/run_artifacts/latest"),
        help="Path to run artifact bundle containing readmodels/",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: <artifacts-dir>/readmodels/live_probe_evidence_digest.json)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_path = args.output or (args.artifacts_dir / "readmodels" / "live_probe_evidence_digest.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    digest = build_live_probe_evidence_digest(artifacts_dir=args.artifacts_dir)
    output_path.write_text(json.dumps(digest, indent=2, sort_keys=True), encoding="utf-8")

    governance = digest.get("governance_summary", {})
    run_context = digest.get("run_context", {})
    print(
        json.dumps(
            {
                "output": str(output_path),
                "run_id": run_context.get("run_id"),
                "run_status": run_context.get("run_status"),
                "verdict": governance.get("verdict"),
                "combined_ce_ratio": digest.get("ce_utilization", {}).get("combined_ce_ratio"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
