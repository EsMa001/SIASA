from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def build_stakeholder_system_traceability_report(*, repo_root: Path) -> dict[str, Any]:
    stakeholder_payload = _load_yaml(repo_root / "vmodel" / "requirements" / "stakeholder_requirements.yaml")
    system_payload = _load_yaml(repo_root / "vmodel" / "requirements" / "system_requirements.yaml")
    traceability_payload = _load_yaml(repo_root / "vmodel" / "traceability" / "trace_links.yaml")

    stakeholder_requirements = stakeholder_payload.get("stakeholder_requirements", [])
    system_requirements = system_payload.get("system_requirements", [])
    links = (traceability_payload.get("traceability") or {}).get("links", [])
    if not isinstance(stakeholder_requirements, list):
        raise ValueError("stakeholder_requirements must be a list")
    if not isinstance(system_requirements, list):
        raise ValueError("system_requirements must be a list")
    if not isinstance(links, list):
        raise ValueError("traceability.links must be a list")

    active_stakeholder_ids = sorted(
        str(item.get("id"))
        for item in stakeholder_requirements
        if isinstance(item, dict) and item.get("status") == "accepted" and item.get("source_status") == "aktiv"
    )

    syr_to_stakeholders: dict[str, set[str]] = {}
    for requirement in system_requirements:
        if not isinstance(requirement, dict):
            continue
        syr_id = str(requirement.get("id", ""))
        if not syr_id.startswith("SyR-"):
            continue
        syr_to_stakeholders[syr_id] = {str(item) for item in requirement.get("derives_from", []) if str(item).startswith("StR-")}

    trace_syr_to_stakeholders: dict[str, set[str]] = {}
    for link in links:
        if not isinstance(link, dict):
            continue
        source_id = str(link.get("source_id", ""))
        if source_id.startswith("SyR-") and link.get("relation") == "derives_from":
            trace_syr_to_stakeholders[source_id] = {str(item) for item in link.get("target_ids", []) if str(item).startswith("StR-")}

    covered_by_system = sorted(set().union(*syr_to_stakeholders.values()) if syr_to_stakeholders else set())
    covered_by_trace = sorted(set().union(*trace_syr_to_stakeholders.values()) if trace_syr_to_stakeholders else set())
    active_set = set(active_stakeholder_ids)
    missing_system = sorted(active_set.difference(covered_by_system))
    missing_trace = sorted(active_set.difference(covered_by_trace))
    orphan_system_refs = sorted(set(covered_by_system).difference(active_set))
    orphan_trace_refs = sorted(set(covered_by_trace).difference(active_set))
    syr_trace_mismatches = []
    for syr_id in sorted(set(syr_to_stakeholders).union(trace_syr_to_stakeholders)):
        if syr_to_stakeholders.get(syr_id, set()) != trace_syr_to_stakeholders.get(syr_id, set()):
            syr_trace_mismatches.append(
                {
                    "system_requirement_id": syr_id,
                    "system_only_refs": sorted(syr_to_stakeholders.get(syr_id, set()).difference(trace_syr_to_stakeholders.get(syr_id, set()))),
                    "trace_only_refs": sorted(trace_syr_to_stakeholders.get(syr_id, set()).difference(syr_to_stakeholders.get(syr_id, set()))),
                }
            )

    rows = []
    for stakeholder_id in active_stakeholder_ids:
        covering_syrs = sorted(syr_id for syr_id, refs in syr_to_stakeholders.items() if stakeholder_id in refs)
        trace_syrs = sorted(syr_id for syr_id, refs in trace_syr_to_stakeholders.items() if stakeholder_id in refs)
        rows.append(
            {
                "stakeholder_requirement_id": stakeholder_id,
                "system_requirements": covering_syrs,
                "traceability_system_requirements": trace_syrs,
                "coverage_status": "covered" if covering_syrs and trace_syrs else "missing",
            }
        )

    return {
        "metadata": {
            "work_package": "AP-02",
            "routing_primary_model": "5.5-class high-level mapping review",
            "routing_execute_model": "Codex 5.3 repository artifact update",
        },
        "summary": {
            "active_stakeholder_requirement_count": len(active_stakeholder_ids),
            "system_requirement_count": len(syr_to_stakeholders),
            "covered_by_system_requirement_count": len(set(covered_by_system).intersection(active_set)),
            "covered_by_traceability_count": len(set(covered_by_trace).intersection(active_set)),
            "missing_system_requirement_mapping_count": len(missing_system),
            "missing_traceability_mapping_count": len(missing_trace),
            "orphan_system_requirement_ref_count": len(orphan_system_refs),
            "orphan_traceability_ref_count": len(orphan_trace_refs),
            "syr_trace_mismatch_count": len(syr_trace_mismatches),
        },
        "stop_criteria": {
            "all_active_stakeholders_have_system_requirement": len(missing_system) == 0,
            "all_active_stakeholders_have_traceability_link": len(missing_trace) == 0,
            "no_orphan_system_requirement_refs": len(orphan_system_refs) == 0,
            "no_orphan_traceability_refs": len(orphan_trace_refs) == 0,
            "system_and_traceability_links_match": len(syr_trace_mismatches) == 0,
        },
        "missing_system_requirement_mappings": missing_system,
        "missing_traceability_mappings": missing_trace,
        "orphan_system_requirement_refs": orphan_system_refs,
        "orphan_traceability_refs": orphan_trace_refs,
        "syr_trace_mismatches": syr_trace_mismatches,
        "rows": rows,
    }


def render_stakeholder_system_traceability_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    stop_criteria = report.get("stop_criteria", {})
    stop_lines = "\n".join(f"- {key}: {'pass' if value else 'fail'}" for key, value in stop_criteria.items())
    return (
        "# SIASA AP-02 Stakeholder-to-System Traceability Report\n\n"
        f"- active_stakeholder_requirement_count: {summary.get('active_stakeholder_requirement_count', 'n/a')}\n"
        f"- system_requirement_count: {summary.get('system_requirement_count', 'n/a')}\n"
        f"- covered_by_system_requirement_count: {summary.get('covered_by_system_requirement_count', 'n/a')}\n"
        f"- covered_by_traceability_count: {summary.get('covered_by_traceability_count', 'n/a')}\n"
        f"- missing_system_requirement_mapping_count: {summary.get('missing_system_requirement_mapping_count', 'n/a')}\n"
        f"- missing_traceability_mapping_count: {summary.get('missing_traceability_mapping_count', 'n/a')}\n"
        f"- syr_trace_mismatch_count: {summary.get('syr_trace_mismatch_count', 'n/a')}\n\n"
        "## Stop Criteria\n"
        f"{stop_lines}\n\n"
        "## Boundary\n"
        "AP-02 closes stakeholder-to-system mapping coverage. Software-level and executable test closure remain governed by AP-03.\n"
    )
