from __future__ import annotations

import json
from pathlib import Path

from siasa.readmodels.release_evidence import build_release_failure_drill_report


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_release_failure_drill_report(repo_root=repo_root)
    summary = {
        "drill_verdict": report.get("drill_verdict"),
        "checks": report.get("checks", {}),
        "failure_localization": report.get("failure_localization", {}),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if str(report.get("drill_verdict")) == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
