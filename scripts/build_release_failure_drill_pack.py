from __future__ import annotations

import argparse
import json
from pathlib import Path

from siasa.readmodels.release_evidence import build_release_failure_drill_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SIASA release failure-drill pack (scenario JSON files)")
    parser.add_argument(
        "--output-dir",
        default="build/release_failure_drill/latest",
        help="Output directory for drill summary and scenario artifacts",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_release_failure_drill_report(repo_root=repo_root)
    (output_dir / "release_failure_drill_summary.json").write_text(
        json.dumps({"drill_verdict": report.get("drill_verdict"), "checks": report.get("checks", {})}, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    scenarios_dir = output_dir / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    for scenario_id, assessment in (report.get("scenarios") or {}).items():
        scenario_dir = scenarios_dir / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        (scenario_dir / "release_gate.json").write_text(
            json.dumps(assessment.get("release_gate", {}), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (scenario_dir / "readiness.json").write_text(
            json.dumps(assessment.get("readiness", {}), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (scenario_dir / "stakeholder_functional_closure.json").write_text(
            json.dumps(assessment.get("stakeholder_functional_closure", {}), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (scenario_dir / "stakeholder_e2e_flow_coverage.json").write_text(
            json.dumps(assessment.get("stakeholder_e2e_flow_coverage", {}), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (scenario_dir / "release_readiness_index.json").write_text(
            json.dumps(assessment.get("release_readiness_index", {}), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(str(output_dir / "release_failure_drill_summary.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
