from __future__ import annotations

import json
from pathlib import Path

from siasa.readmodels.stakeholder_browser_failure_resilience import build_stakeholder_browser_failure_resilience_report


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_stakeholder_browser_failure_resilience_report(repo_root=repo_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all((report.get("stop_criteria") or {}).values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
