from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def build_stakeholder_functional_closure_report(*, repo_root: Path) -> dict[str, Any]:
    traceability_payload = _load_yaml(repo_root / "vmodel" / "traceability" / "trace_links.yaml")
    links = traceability_payload.get("traceability", {}).get("links", [])
    if not isinstance(links, list):
        raise ValueError("traceability.links must be a list")

    syr_to_stakeholders: dict[str, set[str]] = {}
    swr_to_syrs: dict[str, set[str]] = {}
    swr_verified_by_tests: dict[str, set[str]] = {}

    for link in links:
        if not isinstance(link, dict):
            continue
        source_id = str(link.get("source_id", ""))
        relation = str(link.get("relation", ""))
        target_ids = {str(item) for item in link.get("target_ids", [])}

        if relation == "derives_from" and source_id.startswith("SyR-"):
            syr_to_stakeholders[source_id] = {target_id for target_id in target_ids if target_id.startswith("StR-")}
            continue

        if relation == "derives_from" and source_id.startswith("SwR-"):
            swr_to_syrs[source_id] = {target_id for target_id in target_ids if target_id.startswith("SyR-")}
            continue

        if relation == "verifies" and source_id.startswith("TC-SwR-"):
            for target_id in target_ids:
                if target_id.startswith("SwR-"):
                    swr_verified_by_tests.setdefault(target_id, set()).add(source_id)

    closure_paths: dict[str, dict[str, Any]] = {}
    functional_stakeholders: set[str] = set()

    for syr_id, stakeholder_ids in syr_to_stakeholders.items():
        functional_stakeholders.update(stakeholder_ids)
        for stakeholder_id in stakeholder_ids:
            entry = closure_paths.setdefault(
                stakeholder_id,
                {
                    "stakeholder_requirement_id": stakeholder_id,
                    "system_requirements": set(),
                    "software_requirements": set(),
                    "verifying_test_specs": set(),
                },
            )
            entry["system_requirements"].add(syr_id)

    for swr_id, syr_ids in swr_to_syrs.items():
        tests = swr_verified_by_tests.get(swr_id, set())
        for stakeholder_id, entry in closure_paths.items():
            if entry["system_requirements"].intersection(syr_ids):
                entry["software_requirements"].add(swr_id)
                entry["verifying_test_specs"].update(tests)

    implemented_count = 0
    closure_rows: list[dict[str, Any]] = []
    for stakeholder_id in sorted(functional_stakeholders):
        entry = closure_paths.get(
            stakeholder_id,
            {
                "stakeholder_requirement_id": stakeholder_id,
                "system_requirements": set(),
                "software_requirements": set(),
                "verifying_test_specs": set(),
            },
        )
        implemented = bool(entry["software_requirements"] and entry["verifying_test_specs"])
        if implemented:
            implemented_count += 1
        closure_rows.append(
            {
                "stakeholder_requirement_id": stakeholder_id,
                "status": "umgesetzt" if implemented else "nicht_nachweisbar",
                "system_requirements": sorted(entry["system_requirements"]),
                "software_requirements": sorted(entry["software_requirements"]),
                "verifying_test_specs": sorted(entry["verifying_test_specs"]),
            }
        )

    not_closed_ids = [
        row["stakeholder_requirement_id"]
        for row in closure_rows
        if row["status"] == "nicht_nachweisbar"
    ]

    focus_gap_ids = [
        "StR-001",
        "StR-002",
        "StR-004",
        "StR-007",
        "StR-024",
        "StR-025",
        "StR-135",
        "StR-136",
        "StR-137",
        "StR-138",
        "StR-139",
        "StR-140",
        "StR-141",
        "StR-142",
        "StR-226",
        "StR-227",
        "StR-228",
        "StR-229",
        "StR-230",
    ]
    by_id = {row["stakeholder_requirement_id"]: row for row in closure_rows}
    focus_rows = [by_id[stakeholder_id] for stakeholder_id in focus_gap_ids if stakeholder_id in by_id]
    focus_not_closed = [row["stakeholder_requirement_id"] for row in focus_rows if row["status"] != "umgesetzt"]

    return {
        "summary": {
            "functional_stakeholder_count": len(functional_stakeholders),
            "implemented_count": implemented_count,
            "not_implemented_count": len(not_closed_ids),
        },
        "functional_stakeholder_closure": closure_rows,
        "focus_gap_cluster": {
            "stakeholder_ids": focus_gap_ids,
            "covered_count": len(focus_rows),
            "implemented_count": len(focus_rows) - len(focus_not_closed),
            "not_implemented_count": len(focus_not_closed),
            "not_implemented_ids": focus_not_closed,
        },
    }
