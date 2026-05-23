from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def _range_expand(text: str) -> set[str]:
    # Keep implementation deliberately explicit: current policy stores concrete IDs,
    # while descriptions may mention ranges for humans only.
    return {text}


def build_stakeholder_verification_coverage_report(*, repo_root: Path) -> dict[str, Any]:
    stakeholder_payload = _load_yaml(repo_root / "vmodel" / "requirements" / "stakeholder_requirements.yaml")
    system_payload = _load_yaml(repo_root / "vmodel" / "requirements" / "system_requirements.yaml")
    software_payload = _load_yaml(repo_root / "vmodel" / "requirements" / "software_requirements.yaml")
    tests_payload = _load_yaml(repo_root / "vmodel" / "verification" / "test_specifications.yaml")
    policy_payload = _load_yaml(repo_root / "vmodel" / "verification" / "stakeholder_verification_coverage_policy.yaml")

    stakeholders = stakeholder_payload.get("stakeholder_requirements", [])
    system_requirements = system_payload.get("system_requirements", [])
    software_requirements = software_payload.get("software_requirements", [])
    test_specs = tests_payload.get("test_specifications", [])
    if not all(isinstance(item, list) for item in [stakeholders, system_requirements, software_requirements, test_specs]):
        raise ValueError("stakeholders, system_requirements, software_requirements, and test_specifications must be lists")

    active_stakeholder_ids = sorted(
        str(item.get("id"))
        for item in stakeholders
        if isinstance(item, dict) and item.get("status") == "accepted" and item.get("source_status") == "aktiv"
    )
    active_set = set(active_stakeholder_ids)

    syr_to_stakeholders: dict[str, set[str]] = {}
    for syr in system_requirements:
        if isinstance(syr, dict) and str(syr.get("id", "")).startswith("SyR-"):
            syr_to_stakeholders[str(syr["id"])] = {str(item) for item in syr.get("derives_from", []) if str(item).startswith("StR-")}

    swr_to_syrs: dict[str, set[str]] = {}
    for swr in software_requirements:
        if isinstance(swr, dict) and str(swr.get("id", "")).startswith("SwR-") and swr.get("status") == "accepted":
            swr_to_syrs[str(swr["id"])] = {str(item) for item in swr.get("derives_from", []) if str(item).startswith("SyR-")}

    syr_to_swrs: dict[str, set[str]] = {syr_id: set() for syr_id in syr_to_stakeholders}
    for swr_id, syr_ids in swr_to_syrs.items():
        for syr_id in syr_ids:
            syr_to_swrs.setdefault(syr_id, set()).add(swr_id)

    syr_to_tcs: dict[str, set[str]] = {syr_id: set() for syr_id in syr_to_stakeholders}
    swr_to_tcs: dict[str, set[str]] = {swr_id: set() for swr_id in swr_to_syrs}
    for test_spec in test_specs:
        if not isinstance(test_spec, dict):
            continue
        test_id = str(test_spec.get("id", ""))
        for req_id in test_spec.get("requirement_ids", []) or []:
            req_id = str(req_id)
            if req_id.startswith("SyR-"):
                syr_to_tcs.setdefault(req_id, set()).add(test_id)
            if req_id.startswith("SwR-"):
                swr_to_tcs.setdefault(req_id, set()).add(test_id)

    route_assignments = policy_payload.get("route_assignments", {}) or {}
    syr_to_route: dict[str, str] = {}
    duplicate_route_assignments: list[str] = []
    for route_name, syr_ids in route_assignments.items():
        for syr_id in syr_ids or []:
            syr_id = str(syr_id)
            if syr_id in syr_to_route:
                duplicate_route_assignments.append(syr_id)
            syr_to_route[syr_id] = str(route_name)

    unclassified_syrs = sorted(set(syr_to_stakeholders).difference(syr_to_route))
    unknown_route_syrs = sorted(set(syr_to_route).difference(syr_to_stakeholders))
    software_route_syrs = sorted(syr_id for syr_id, route in syr_to_route.items() if route == "software_route")
    governance_route_syrs = sorted(syr_id for syr_id, route in syr_to_route.items() if route == "governance_system_route")

    software_route_syrs_without_swr = sorted(syr_id for syr_id in software_route_syrs if not syr_to_swrs.get(syr_id))
    syrs_without_system_tc = sorted(syr_id for syr_id in syr_to_stakeholders if not syr_to_tcs.get(syr_id))
    swrs_without_tc = sorted(swr_id for swr_id in swr_to_syrs if not swr_to_tcs.get(swr_id))
    governance_route_syrs_without_tc = sorted(syr_id for syr_id in governance_route_syrs if not syr_to_tcs.get(syr_id))

    stakeholder_rows: list[dict[str, Any]] = []
    stakeholder_ids_with_verification_route: set[str] = set()
    for stakeholder_id in active_stakeholder_ids:
        covering_syrs = sorted(syr_id for syr_id, refs in syr_to_stakeholders.items() if stakeholder_id in refs)
        route_rows = []
        for syr_id in covering_syrs:
            route = syr_to_route.get(syr_id)
            system_tcs = sorted(syr_to_tcs.get(syr_id, set()))
            swrs = sorted(syr_to_swrs.get(syr_id, set()))
            swr_tcs = sorted({tc_id for swr_id in swrs for tc_id in swr_to_tcs.get(swr_id, set())})
            if route == "software_route":
                route_ok = bool(system_tcs and swrs and swr_tcs)
            elif route == "governance_system_route":
                route_ok = bool(system_tcs)
            else:
                route_ok = False
            if route_ok:
                stakeholder_ids_with_verification_route.add(stakeholder_id)
            route_rows.append(
                {
                    "system_requirement_id": syr_id,
                    "verification_route": route or "unclassified",
                    "system_test_specs": system_tcs,
                    "software_requirements": swrs,
                    "software_test_specs": swr_tcs,
                    "route_ok": route_ok,
                }
            )
        stakeholder_rows.append(
            {
                "stakeholder_requirement_id": stakeholder_id,
                "verification_status": "covered" if stakeholder_id in stakeholder_ids_with_verification_route else "missing",
                "routes": route_rows,
            }
        )

    missing_stakeholder_verification = sorted(active_set.difference(stakeholder_ids_with_verification_route))

    return {
        "metadata": {
            "work_package": "AP-03",
            "routing_primary_model": "5.5-class verification strategy review",
            "routing_execute_model": "Codex 5.3 repository artifact update",
            "policy_path": "vmodel/verification/stakeholder_verification_coverage_policy.yaml",
        },
        "summary": {
            "active_stakeholder_requirement_count": len(active_stakeholder_ids),
            "stakeholder_verification_covered_count": len(stakeholder_ids_with_verification_route),
            "missing_stakeholder_verification_count": len(missing_stakeholder_verification),
            "system_requirement_count": len(syr_to_stakeholders),
            "software_route_system_requirement_count": len(software_route_syrs),
            "governance_system_route_requirement_count": len(governance_route_syrs),
            "unclassified_system_requirement_count": len(unclassified_syrs),
            "software_route_syrs_without_swr_count": len(software_route_syrs_without_swr),
            "system_requirements_without_system_tc_count": len(syrs_without_system_tc),
            "accepted_software_requirement_count": len(swr_to_syrs),
            "software_requirements_without_tc_count": len(swrs_without_tc),
            "governance_route_syrs_without_tc_count": len(governance_route_syrs_without_tc),
        },
        "stop_criteria": {
            "all_active_stakeholders_have_verification_route": len(missing_stakeholder_verification) == 0,
            "all_system_requirements_have_route_classification": len(unclassified_syrs) == 0 and len(unknown_route_syrs) == 0 and len(duplicate_route_assignments) == 0,
            "all_system_requirements_have_system_tc": len(syrs_without_system_tc) == 0,
            "all_software_route_syrs_have_swr": len(software_route_syrs_without_swr) == 0,
            "all_accepted_swrs_have_tc": len(swrs_without_tc) == 0,
            "all_governance_route_syrs_have_system_tc": len(governance_route_syrs_without_tc) == 0,
        },
        "missing_stakeholder_verification_ids": missing_stakeholder_verification,
        "unclassified_system_requirements": unclassified_syrs,
        "unknown_route_system_requirements": unknown_route_syrs,
        "duplicate_route_assignments": sorted(set(duplicate_route_assignments)),
        "software_route_syrs_without_swr": software_route_syrs_without_swr,
        "system_requirements_without_system_tc": syrs_without_system_tc,
        "software_requirements_without_tc": swrs_without_tc,
        "governance_route_syrs_without_tc": governance_route_syrs_without_tc,
        "stakeholder_verification_rows": stakeholder_rows,
    }


def render_stakeholder_verification_coverage_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    stop_criteria = report.get("stop_criteria", {})
    stop_lines = "\n".join(f"- {key}: {'pass' if value else 'fail'}" for key, value in stop_criteria.items())
    return (
        "# SIASA AP-03 Stakeholder Verification Coverage Report\n\n"
        f"- active_stakeholder_requirement_count: {summary.get('active_stakeholder_requirement_count', 'n/a')}\n"
        f"- stakeholder_verification_covered_count: {summary.get('stakeholder_verification_covered_count', 'n/a')}\n"
        f"- missing_stakeholder_verification_count: {summary.get('missing_stakeholder_verification_count', 'n/a')}\n"
        f"- system_requirement_count: {summary.get('system_requirement_count', 'n/a')}\n"
        f"- software_route_system_requirement_count: {summary.get('software_route_system_requirement_count', 'n/a')}\n"
        f"- governance_system_route_requirement_count: {summary.get('governance_system_route_requirement_count', 'n/a')}\n"
        f"- accepted_software_requirement_count: {summary.get('accepted_software_requirement_count', 'n/a')}\n"
        f"- software_requirements_without_tc_count: {summary.get('software_requirements_without_tc_count', 'n/a')}\n\n"
        "## Stop Criteria\n"
        f"{stop_lines}\n\n"
        "## Boundary\n"
        "AP-03 closes verification specification coverage for every active stakeholder requirement. Flow-level E2E execution remains AP-04.\n"
    )
