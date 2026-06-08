from __future__ import annotations

import argparse
from pathlib import Path

from siasa.runs.operational_latest import DEFAULT_OPERATIONAL_LATEST_PILOT_SET, build_operational_latest_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SIASA operational latest artifact + GUI bundle")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--run-id", required=True, help="Run identifier for the operational latest build")
    parser.add_argument("--pilot-set", default=DEFAULT_OPERATIONAL_LATEST_PILOT_SET, help="Governed live pilot set to use")
    parser.add_argument("--artifacts-dir", default="build/run_artifacts/latest", help="Artifact output directory")
    parser.add_argument("--gui-output-dir", default="build/local_gui/latest", help="GUI output directory")
    parser.add_argument(
        "--history-db",
        default="build/run_history/latest_runs.sqlite",
        help="SQLite path for operational latest run history",
    )
    parser.add_argument(
        "--allow-partial-success",
        action="store_true",
        help="Accept run_status=partial_success for operational bundle generation.",
    )
    parser.add_argument(
        "--allow-failed-sources",
        action="store_true",
        help="Allow non-empty failed_sources when run status is accepted.",
    )
    parser.add_argument(
        "--allow-policy-gate-fail",
        action="store_true",
        help="Allow live-probe policy gate failure for explicit degraded inspection mode.",
    )
    args = parser.parse_args()

    result = build_operational_latest_bundle(
        repo_root=Path(args.repo_root),
        run_id=args.run_id,
        pilot_set=args.pilot_set,
        artifacts_dir=Path(args.artifacts_dir),
        gui_output_dir=Path(args.gui_output_dir),
        history_db_path=Path(args.history_db),
        allow_partial_success=args.allow_partial_success,
        allow_failed_sources=args.allow_failed_sources,
        allow_policy_gate_fail=args.allow_policy_gate_fail,
    )
    print(
        f"run_status={result['run_status']} pilot_set={result['pilot_set']} "
        f"artifacts_dir={result['artifacts_dir']} gui_index={result['gui_index']} history_db={result['history_db']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
