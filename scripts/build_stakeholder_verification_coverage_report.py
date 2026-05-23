from __future__ import annotations

import argparse
import json
from pathlib import Path

from siasa.readmodels.stakeholder_verification_coverage import (
    build_stakeholder_verification_coverage_report,
    render_stakeholder_verification_coverage_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SIASA AP-03 stakeholder verification coverage report")
    parser.add_argument(
        "--output-dir",
        default="build/analysis/stakeholder_verification_coverage",
        help="Output directory for stakeholder_verification_coverage_report.json/.md",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_stakeholder_verification_coverage_report(repo_root=repo_root)
    json_path = output_dir / "stakeholder_verification_coverage_report.json"
    md_path = output_dir / "stakeholder_verification_coverage_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_stakeholder_verification_coverage_markdown(report), encoding="utf-8")

    print(str(json_path))
    print(str(md_path))
    return 0 if all(report.get("stop_criteria", {}).values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
