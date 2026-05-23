from __future__ import annotations

import argparse
import json
from pathlib import Path

from siasa.readmodels.release_evidence import build_repo_release_gate_assessment, render_release_evidence_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SIASA release evidence pack (JSON + Markdown)")
    parser.add_argument(
        "--output-dir",
        default="build/release_evidence/latest",
        help="Output directory for release_evidence_pack.json/.md",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    assessment = build_repo_release_gate_assessment(repo_root=repo_root)
    json_path = output_dir / "release_evidence_pack.json"
    md_path = output_dir / "release_evidence_pack.md"
    json_path.write_text(json.dumps(assessment, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_release_evidence_markdown(assessment), encoding="utf-8")

    print(str(json_path))
    print(str(md_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
