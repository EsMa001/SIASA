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

    previous_summary_path = output_dir / "release_failure_drill_summary.json"
    previous_summary = None
    if previous_summary_path.exists():
        previous_summary = json.loads(previous_summary_path.read_text(encoding="utf-8"))

    report = build_release_failure_drill_report(
        repo_root=repo_root,
        previous_report_override=previous_summary,
    )
    (output_dir / "release_failure_drill_summary.json").write_text(
        json.dumps(
            {
                "drill_verdict": report.get("drill_verdict"),
                "checks": report.get("checks", {}),
                "failure_localization": report.get("failure_localization", {}),
                "gate_diagnostics_export": report.get("gate_diagnostics_export", {}),
                "operator_failure_drill_trend_baseline": report.get("operator_failure_drill_trend_baseline", {}),
                "operator_failure_drill_delta_ledger": report.get("operator_failure_drill_delta_ledger", {}),
                "operator_remediation_execution_loop": report.get("operator_remediation_execution_loop", {}),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    scenarios_dir = output_dir / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)

    diagnostics_dir = output_dir / "gate_diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    for gate_id, gate_slice in (report.get("gate_diagnostics_export") or {}).items():
        (diagnostics_dir / f"{gate_id}.json").write_text(
            json.dumps(gate_slice, indent=2, sort_keys=True),
            encoding="utf-8",
        )
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
