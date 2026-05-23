from __future__ import annotations

import json
from pathlib import Path

from siasa.readmodels.stakeholder_functional_closure import build_stakeholder_functional_closure_report


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_stakeholder_functional_closure_report(repo_root=repo_root)
    focus = report.get("focus_gap_cluster", {})

    covered_count = int(focus.get("covered_count", 0))
    not_implemented_count = int(focus.get("not_implemented_count", 1))
    not_implemented_ids = [str(item) for item in focus.get("not_implemented_ids", [])]

    result = {
        "covered_count": covered_count,
        "not_implemented_count": not_implemented_count,
        "not_implemented_ids": not_implemented_ids,
    }
    print(json.dumps(result, indent=2))

    if covered_count != 19:
        return 1
    return 0 if not_implemented_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
