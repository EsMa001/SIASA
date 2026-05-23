from __future__ import annotations

import json
from pathlib import Path

from siasa.readmodels.stakeholder_e2e_ui_smoke import build_stakeholder_e2e_ui_smoke_report


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_stakeholder_e2e_ui_smoke_report(repo_root=repo_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(report.get("stop_criteria", {}).values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
