from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def _python_test_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}


def build_stakeholder_e2e_flow_coverage_report(*, repo_root: Path) -> dict[str, Any]:
    flow_payload = _load_yaml(repo_root / "vmodel" / "verification" / "stakeholder_e2e_flows.yaml")
    stakeholder_payload = _load_yaml(repo_root / "vmodel" / "requirements" / "stakeholder_requirements.yaml")
    system_payload = _load_yaml(repo_root / "vmodel" / "requirements" / "system_requirements.yaml")

    flows = flow_payload.get("flows", [])
    if not isinstance(flows, list):
        raise ValueError("stakeholder_e2e_flows.flows must be a list")

    rules = flow_payload.get("coverage_rules", {}) or {}
    required_fields = [str(item) for item in rules.get("required_flow_fields", [])]
    required_roles = {str(item) for item in rules.get("required_roles", [])}
    minimum_flow_count = int(rules.get("minimum_flow_count", 0))

    active_stakeholder_ids = {
        str(item.get("id"))
        for item in stakeholder_payload.get("stakeholder_requirements", [])
        if isinstance(item, dict) and item.get("status") == "accepted" and item.get("source_status") == "aktiv"
    }
    system_requirement_ids = {
        str(item.get("id"))
        for item in system_payload.get("system_requirements", [])
        if isinstance(item, dict) and item.get("status") == "accepted"
    }

    rows: list[dict[str, Any]] = []
    missing_flow_fields: list[dict[str, Any]] = []
    missing_evidence_refs: list[dict[str, Any]] = []
    missing_requirement_refs: list[dict[str, Any]] = []
    roles_covered: set[str] = set()
    flows_with_happy_path = 0
    flows_with_failure_path = 0

    for flow in flows:
        if not isinstance(flow, dict):
            continue
        flow_id = str(flow.get("id", ""))
        role = str(flow.get("role", ""))
        if role:
            roles_covered.add(role)
        missing_fields = [field for field in required_fields if flow.get(field) in (None, "", [])]
        if missing_fields:
            missing_flow_fields.append({"flow_id": flow_id, "missing_fields": missing_fields})

        happy_path = flow.get("happy_path", []) or []
        failure_paths = flow.get("failure_paths", []) or []
        if happy_path:
            flows_with_happy_path += 1
        if failure_paths:
            flows_with_failure_path += 1

        unknown_stakeholders = sorted(set(str(item) for item in flow.get("stakeholder_requirement_refs", [])).difference(active_stakeholder_ids))
        unknown_system_requirements = sorted(set(str(item) for item in flow.get("system_requirement_refs", [])).difference(system_requirement_ids))
        if unknown_stakeholders or unknown_system_requirements:
            missing_requirement_refs.append(
                {
                    "flow_id": flow_id,
                    "unknown_stakeholder_requirement_refs": unknown_stakeholders,
                    "unknown_system_requirement_refs": unknown_system_requirements,
                }
            )

        evidence_rows = []
        for evidence in flow.get("evidence_refs", []) or []:
            evidence_type = str(evidence.get("type", "")) if isinstance(evidence, dict) else ""
            rel_path = str(evidence.get("path", "")) if isinstance(evidence, dict) else ""
            evidence_path = repo_root / rel_path
            exists = evidence_path.exists()
            test_name = str(evidence.get("test", "")) if isinstance(evidence, dict) else ""
            test_exists = True
            if evidence_type == "pytest":
                test_exists = exists and test_name in _python_test_functions(evidence_path)
            ok = exists and test_exists
            if not ok:
                missing_evidence_refs.append(
                    {
                        "flow_id": flow_id,
                        "type": evidence_type,
                        "path": rel_path,
                        "test": test_name or None,
                        "file_exists": exists,
                        "test_exists": test_exists,
                    }
                )
            evidence_rows.append(
                {
                    "type": evidence_type,
                    "path": rel_path,
                    "test": test_name or None,
                    "ok": ok,
                }
            )

        rows.append(
            {
                "flow_id": flow_id,
                "role": role,
                "happy_path_step_count": len(happy_path),
                "failure_path_count": len(failure_paths),
                "evidence_ref_count": len(evidence_rows),
                "evidence_refs": evidence_rows,
                "coverage_status": "covered"
                if not missing_fields and not unknown_stakeholders and not unknown_system_requirements and all(item["ok"] for item in evidence_rows) and happy_path and failure_paths
                else "gap",
            }
        )

    covered_flow_count = sum(1 for row in rows if row["coverage_status"] == "covered")
    uncovered_roles = sorted(required_roles.difference(roles_covered))

    return {
        "metadata": {
            "work_package": "AP-04",
            "routing_primary_model": "5.5-class stakeholder flow design review",
            "routing_execute_model": "Codex 5.3 repository artifact update",
            "flow_suite_path": "vmodel/verification/stakeholder_e2e_flows.yaml",
        },
        "summary": {
            "flow_count": len(rows),
            "covered_flow_count": covered_flow_count,
            "flow_gap_count": len(rows) - covered_flow_count,
            "required_role_count": len(required_roles),
            "covered_role_count": len(required_roles.intersection(roles_covered)),
            "minimum_flow_count": minimum_flow_count,
            "flows_with_happy_path_count": flows_with_happy_path,
            "flows_with_failure_path_count": flows_with_failure_path,
            "missing_evidence_ref_count": len(missing_evidence_refs),
            "missing_requirement_ref_count": len(missing_requirement_refs),
            "missing_flow_field_count": len(missing_flow_fields),
        },
        "stop_criteria": {
            "minimum_prioritized_flows_defined": len(rows) >= minimum_flow_count,
            "required_roles_covered": len(uncovered_roles) == 0,
            "all_flows_have_happy_and_failure_paths": flows_with_happy_path == len(rows) and flows_with_failure_path == len(rows),
            "all_flow_requirement_refs_resolve": len(missing_requirement_refs) == 0,
            "all_flow_evidence_refs_resolve": len(missing_evidence_refs) == 0,
            "all_flows_covered": covered_flow_count == len(rows),
        },
        "uncovered_roles": uncovered_roles,
        "missing_flow_fields": missing_flow_fields,
        "missing_requirement_refs": missing_requirement_refs,
        "missing_evidence_refs": missing_evidence_refs,
        "flows": rows,
    }


def render_stakeholder_e2e_flow_coverage_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    stop_criteria = report.get("stop_criteria", {})
    stop_lines = "\n".join(f"- {key}: {'pass' if value else 'fail'}" for key, value in stop_criteria.items())
    return (
        "# SIASA AP-04 Stakeholder E2E Flow Coverage Report\n\n"
        f"- flow_count: {summary.get('flow_count', 'n/a')}\n"
        f"- covered_flow_count: {summary.get('covered_flow_count', 'n/a')}\n"
        f"- flow_gap_count: {summary.get('flow_gap_count', 'n/a')}\n"
        f"- covered_role_count: {summary.get('covered_role_count', 'n/a')}/{summary.get('required_role_count', 'n/a')}\n"
        f"- flows_with_happy_path_count: {summary.get('flows_with_happy_path_count', 'n/a')}\n"
        f"- flows_with_failure_path_count: {summary.get('flows_with_failure_path_count', 'n/a')}\n"
        f"- missing_evidence_ref_count: {summary.get('missing_evidence_ref_count', 'n/a')}\n\n"
        "## Stop Criteria\n"
        f"{stop_lines}\n\n"
        "## Boundary\n"
        "AP-04 defines and gates prioritized stakeholder-facing E2E flow evidence. Additional browser automation depth can be added later without reopening AP-01..AP-03.\n"
    )
