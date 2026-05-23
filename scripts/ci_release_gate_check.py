from __future__ import annotations

import json
import sys
from pathlib import Path

from siasa.readmodels.release_evidence import build_repo_release_gate_assessment


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    assessment = build_repo_release_gate_assessment(repo_root=repo_root)
    gate = assessment["release_gate"]
    print(json.dumps({"gate_verdict": gate.get("gate_verdict"), "blockers": gate.get("blockers", [])}, indent=2))
    return 0 if str(gate.get("gate_verdict")) == "go" else 1


if __name__ == "__main__":
    raise SystemExit(main())
