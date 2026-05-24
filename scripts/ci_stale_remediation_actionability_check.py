from __future__ import annotations

import json
from pathlib import Path

from siasa.readmodels.release_evidence import build_repo_release_gate_assessment


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    assessment = build_repo_release_gate_assessment(repo_root=repo_root)
    gates = assessment.get("release_readiness_index", {}).get("gates", [])
    gate_state = {
        str(item.get("gate_id")): bool(item.get("passed"))
        for item in gates
        if isinstance(item, dict)
    }
    passed = gate_state.get("stale_remediation_actionable", False)
    print(
        json.dumps(
            {
                "stale_remediation_actionable": passed,
                "release_readiness_percent": assessment.get("release_readiness_index", {}).get("percent"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
