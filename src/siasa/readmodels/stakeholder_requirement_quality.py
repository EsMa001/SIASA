from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

_STAKEHOLDER_ID_PATTERN = re.compile(r"StR-(\d{3})(?:\.\.(\d{3}))?")


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def _expand_stakeholder_refs(text: str) -> list[str]:
    ids: list[str] = []
    for match in _STAKEHOLDER_ID_PATTERN.finditer(text):
        start = int(match.group(1))
        end = int(match.group(2) or match.group(1))
        ids.extend(f"StR-{idx:03d}" for idx in range(start, end + 1))
    return ids


def _acceptance_criteria_by_stakeholder(acceptance_payload: dict[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for criterion in acceptance_payload.get("acceptance_criteria", []):
        if not isinstance(criterion, dict):
            continue
        criterion_id = str(criterion.get("AC ID", "")).strip()
        refs_text = str(criterion.get("Verknüpfte Anforderungen", ""))
        if not criterion_id:
            continue
        for stakeholder_id in _expand_stakeholder_refs(refs_text):
            result.setdefault(stakeholder_id, set()).add(criterion_id)
    return result


def build_stakeholder_requirement_quality_report(*, repo_root: Path) -> dict[str, Any]:
    stakeholder_path = repo_root / "vmodel" / "requirements" / "stakeholder_requirements.yaml"
    acceptance_path = repo_root / "vmodel" / "verification" / "acceptance_criteria.yaml"
    policy_path = repo_root / "vmodel" / "verification" / "stakeholder_requirement_quality_criteria.yaml"

    stakeholder_payload = _load_yaml(stakeholder_path)
    acceptance_payload = _load_yaml(acceptance_path)
    policy_payload = _load_yaml(policy_path)

    requirements = stakeholder_payload.get("stakeholder_requirements", [])
    if not isinstance(requirements, list):
        raise ValueError("stakeholder_requirements must be a list")

    required_fields = [str(item) for item in (policy_payload.get("quality_dimensions", {}) or {}).get("required_core_fields", [])]
    active_source_status_values = set(
        str(item) for item in (policy_payload.get("quality_dimensions", {}) or {}).get("active_source_status_values", [])
    )
    accepted_status_values = set(
        str(item) for item in (policy_payload.get("quality_dimensions", {}) or {}).get("accepted_status_values", [])
    )
    priority_normalization = {
        str(key): str(value)
        for key, value in ((policy_payload.get("quality_dimensions", {}) or {}).get("source_priority_normalization", {}) or {}).items()
    }
    phase_normalization = {
        str(key): str(value)
        for key, value in ((policy_payload.get("quality_dimensions", {}) or {}).get("source_phase_normalization", {}) or {}).items()
    }
    broad_terms = [str(item).lower() for item in policy_payload.get("broad_language_terms", [])]
    policy_rule_ids = [str(item.get("id")) for item in policy_payload.get("quality_acceptance_rules", []) if isinstance(item, dict)]

    canonical_ac_by_stakeholder = _acceptance_criteria_by_stakeholder(acceptance_payload)
    source_sha256 = hashlib.sha256(stakeholder_path.read_bytes()).hexdigest()

    rows: list[dict[str, Any]] = []
    active_rows: list[dict[str, Any]] = []
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        stakeholder_id = str(requirement.get("id", ""))
        source_status = str(requirement.get("source_status", ""))
        status = str(requirement.get("status", ""))
        active = source_status in active_source_status_values and status in accepted_status_values
        direct_refs = [str(item) for item in requirement.get("acceptance_criteria_refs", []) or []]
        canonical_refs = sorted(set(direct_refs).union(canonical_ac_by_stakeholder.get(stakeholder_id, set())))
        missing_core_fields = [field for field in required_fields if requirement.get(field) in (None, "", [])]
        statement_text = str(requirement.get("statement", ""))
        title_text = str(requirement.get("title", ""))
        combined_text = f"{title_text} {statement_text}".lower()
        broad_terms_present = sorted({term for term in broad_terms if term and term in combined_text})
        effective_priority = priority_normalization.get(str(requirement.get("priority", "")))
        effective_phase = phase_normalization.get(str(requirement.get("phase", "")))
        acceptance_source = "canonical_ac" if canonical_refs else "ap01_quality_policy"
        quality_closed = (
            active
            and not missing_core_fields
            and bool(acceptance_source)
            and bool(effective_priority)
            and bool(effective_phase)
        )
        row = {
            "stakeholder_requirement_id": stakeholder_id,
            "active": active,
            "category": requirement.get("category"),
            "source_priority": requirement.get("priority"),
            "effective_priority": effective_priority,
            "source_phase": requirement.get("phase"),
            "effective_phase": effective_phase,
            "canonical_acceptance_criteria_refs": canonical_refs,
            "acceptance_source": acceptance_source,
            "policy_quality_rule_refs": policy_rule_ids if not canonical_refs else [],
            "missing_core_fields": missing_core_fields,
            "broad_language_terms_present": broad_terms_present,
            "broad_language_bounded_by_policy": bool(broad_terms_present),
            "quality_status": "quality_closed" if quality_closed else "quality_gap",
        }
        rows.append(row)
        if active:
            active_rows.append(row)

    missing_core = [row for row in active_rows if row["missing_core_fields"]]
    missing_acceptance_source = [row for row in active_rows if not row["acceptance_source"]]
    missing_effective_priority = [row for row in active_rows if not row["effective_priority"]]
    missing_effective_phase = [row for row in active_rows if not row["effective_phase"]]
    unbounded_vague = [
        row
        for row in active_rows
        if row["broad_language_terms_present"] and not row["broad_language_bounded_by_policy"]
    ]
    quality_closed_count = sum(1 for row in active_rows if row["quality_status"] == "quality_closed")

    stop_criteria = {
        "core_fields_complete": len(missing_core) == 0,
        "acceptance_source_assigned": len(missing_acceptance_source) == 0,
        "broad_language_bounded": len(unbounded_vague) == 0,
        "effective_priority_phase_assigned": len(missing_effective_priority) == 0 and len(missing_effective_phase) == 0,
        "source_baseline_preserved": bool(source_sha256),
    }

    return {
        "metadata": {
            "work_package": "AP-01",
            "routing_primary_model": "5.5-class high-level review",
            "routing_execute_model": "Codex 5.3 repository artifact update",
            "source_baseline_path": str(stakeholder_path.relative_to(repo_root)),
            "source_baseline_sha256": source_sha256,
            "policy_path": str(policy_path.relative_to(repo_root)),
        },
        "summary": {
            "stakeholder_requirement_count": len(rows),
            "active_requirement_count": len(active_rows),
            "quality_closed_count": quality_closed_count,
            "quality_gap_count": len(active_rows) - quality_closed_count,
            "canonical_acceptance_source_count": sum(1 for row in active_rows if row["acceptance_source"] == "canonical_ac"),
            "ap01_policy_acceptance_source_count": sum(1 for row in active_rows if row["acceptance_source"] == "ap01_quality_policy"),
            "source_priority_tbd_count": sum(1 for row in active_rows if row["source_priority"] == "TBD / aus v0.3"),
            "effective_backlog_triage_count": sum(1 for row in active_rows if row["effective_priority"] == "Backlog-Triage"),
            "missing_core_field_count": len(missing_core),
            "acceptance_source_missing_count": len(missing_acceptance_source),
            "effective_priority_missing_count": len(missing_effective_priority),
            "effective_phase_missing_count": len(missing_effective_phase),
            "broad_language_requirement_count": sum(1 for row in active_rows if row["broad_language_terms_present"]),
            "unbounded_vague_requirement_count": len(unbounded_vague),
        },
        "stop_criteria": stop_criteria,
        "rows": rows,
    }


def render_stakeholder_requirement_quality_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    stop_criteria = report.get("stop_criteria", {})
    stop_lines = "\n".join(
        f"- {key}: {'pass' if value else 'fail'}" for key, value in stop_criteria.items()
    )
    return (
        "# SIASA AP-01 Stakeholder Requirement Quality Report\n\n"
        f"- active_requirement_count: {summary.get('active_requirement_count', 'n/a')}\n"
        f"- quality_closed_count: {summary.get('quality_closed_count', 'n/a')}\n"
        f"- quality_gap_count: {summary.get('quality_gap_count', 'n/a')}\n"
        f"- canonical_acceptance_source_count: {summary.get('canonical_acceptance_source_count', 'n/a')}\n"
        f"- ap01_policy_acceptance_source_count: {summary.get('ap01_policy_acceptance_source_count', 'n/a')}\n"
        f"- source_priority_tbd_count: {summary.get('source_priority_tbd_count', 'n/a')}\n"
        f"- broad_language_requirement_count: {summary.get('broad_language_requirement_count', 'n/a')}\n\n"
        "## Stop Criteria\n"
        f"{stop_lines}\n\n"
        "## Boundary\n"
        "AP-01 quality closure means stakeholder requirement quality is normalized and bounded. "
        "It does not claim product implementation closure; product closure remains governed by AP-02/AP-03 traceability and verification evidence.\n"
    )
