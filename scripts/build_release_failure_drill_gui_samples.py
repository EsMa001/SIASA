from __future__ import annotations

import argparse
from pathlib import Path

from siasa.gui import local_app
from siasa.gui.local_app import build_local_mvp_site
from siasa.readmodels.release_evidence import build_release_failure_drill_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GUI readiness samples for release failure-drill scenarios")
    parser.add_argument(
        "--output-dir",
        default="build/release_failure_drill/gui_samples",
        help="Output directory for per-scenario GUI bundles",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    drill_report = build_release_failure_drill_report(repo_root=repo_root)
    demo_payload = local_app._demo_payload()

    for scenario_id, assessment in (drill_report.get("scenarios") or {}).items():
        scenario_output = output_dir / scenario_id
        build_local_mvp_site(
            output_dir=scenario_output,
            world_map_read_model=demo_payload["world_map_read_model"],
            country_profile_read_models=demo_payload["country_profile_read_models"],
            domain_detail_read_models=demo_payload["domain_detail_read_models"],
            source_coverage_read_model=demo_payload["source_coverage_read_model"],
            report_catalog=demo_payload["report_catalog"],
            system_status_read_model=demo_payload["system_status_read_model"],
            validation_view_model=demo_payload["validation_view_model"],
            annotations_view_model=demo_payload["annotations_view_model"],
            readiness_view_model=assessment.get("readiness"),
            release_gate_view_model=assessment.get("release_gate"),
            stakeholder_functional_closure_view_model=assessment.get("stakeholder_functional_closure"),
        )

    print(str(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
