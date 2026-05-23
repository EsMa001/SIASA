from __future__ import annotations

import json
from pathlib import Path

from siasa.readmodels.stakeholder_e2e_flow_coverage import build_stakeholder_e2e_flow_coverage_report


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_stakeholder_e2e_flow_coverage_report(repo_root=repo_root)
    summary = report.get("summary", {})
    stop_criteria = report.get("stop_criteria", {})

    result = {
        "flow_count": int(summary.get("flow_count", 0)),
        "covered_flow_count": int(summary.get("covered_flow_count", 0)),
        "flow_gap_count": int(summary.get("flow_gap_count", 1)),
        "covered_role_count": int(summary.get("covered_role_count", 0)),
        "required_role_count": int(summary.get("required_role_count", 0)),
        "missing_evidence_ref_count": int(summary.get("missing_evidence_ref_count", 1)),
        "missing_requirement_ref_count": int(summary.get("missing_requirement_ref_count", 1)),
        "failed_stop_criteria": [key for key, value in stop_criteria.items() if not bool(value)],
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    if result["flow_count"] <= 0:
        return 1
    if result["flow_gap_count"] != 0:
        return 1
    if result["missing_evidence_ref_count"] != 0:
        return 1
    if result["missing_requirement_ref_count"] != 0:
        return 1
    if result["covered_role_count"] != result["required_role_count"]:
        return 1
    return 0 if not result["failed_stop_criteria"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
