from __future__ import annotations

from typing import Any


def build_readiness_view_model(
    *,
    country_profile_read_models: dict[str, dict[str, Any]],
    domain_detail_read_models: dict[tuple[str, str], dict[str, Any]],
    report_catalog: dict[str, dict[str, Any]],
    system_status_read_model: dict[str, Any],
    source_coverage_read_model: dict[str, Any],
    validation_view_model: dict[str, Any] | None,
    traceability_view_model: dict[str, Any] | None,
    annotations_view_model: dict[str, Any] | None,
    repo_closure_view_model: dict[str, Any] | None,
    available_pages: set[str],
) -> dict[str, Any]:
    demo_checks = [
        {"label": "Home", "ready": "index.html" in available_pages},
        {"label": "Country Profile", "ready": bool(country_profile_read_models)},
        {"label": "Domain Detail", "ready": bool(domain_detail_read_models)},
        {"label": "Source / Coverage", "ready": "coverage.html" in available_pages},
        {"label": "Report / Export", "ready": "reports.html" in available_pages},
        {"label": "Validation / Backtest", "ready": validation_view_model is not None},
    ]
    evidence_checks = [
        {"label": "Traceability / Lineage", "ready": traceability_view_model is not None},
        {"label": "Analyst Annotations", "ready": annotations_view_model is not None},
        {"label": "Repo Closure Summary", "ready": repo_closure_view_model is not None},
        {"label": "Available Reports", "ready": bool(report_catalog)},
    ]
    artifact_status = system_status_read_model.get("artifact_status", {}) if isinstance(system_status_read_model.get("artifact_status", {}), dict) else {}
    artifact_presence_fallbacks = {
        "validation_backtest": validation_view_model is not None,
        "traceability_lineage": traceability_view_model is not None,
        "repo_closure": repo_closure_view_model is not None,
        "annotations": annotations_view_model is not None,
    }
    artifact_checks = [
        {
            "artifact": artifact_key,
            "status": str(
                (artifact_status.get(artifact_key, {}) or {}).get(
                    "status",
                    "present" if artifact_presence_fallbacks.get(artifact_key, False) else "unknown",
                )
            ),
            "reason": (artifact_status.get(artifact_key, {}) or {}).get("reason"),
        }
        for artifact_key in ["validation_backtest", "traceability_lineage", "repo_closure", "annotations"]
    ]
    demo_verdict = "ready" if all(check["ready"] for check in demo_checks) else "blocked"
    known_gaps = _deduplicated_strings(
        [str(item) for item in system_status_read_model.get("data_gaps", [])]
        + [f"failed_source:{item}" for item in system_status_read_model.get("failed_sources", [])]
        + [f"missing_source:{item}" for item in source_coverage_read_model.get("missing_sources", [])]
        + _country_gap_markers(system_status_read_model)
        + ([] if validation_view_model is not None else _optional_artifact_gap(system_status_read_model, "validation_backtest", missing_fallback="missing_validation_artifact"))
        + ([] if traceability_view_model is not None else _optional_artifact_gap(system_status_read_model, "traceability_lineage", missing_fallback="missing_traceability_artifact"))
        + ([] if repo_closure_view_model is not None else _optional_artifact_gap(system_status_read_model, "repo_closure", missing_fallback="missing_repo_closure_artifact"))
        + ([] if annotations_view_model is not None else _optional_artifact_gap(system_status_read_model, "annotations", missing_fallback="missing_annotations_artifact"))
    )
    release_verdict = "blocked_by_known_gaps" if known_gaps else ("ready" if demo_verdict == "ready" else "blocked")
    return {
        "run_id": system_status_read_model.get("run_id"),
        "snapshot_id": system_status_read_model.get("snapshot_id"),
        "demo_verdict": demo_verdict,
        "release_verdict": release_verdict,
        "demo_checks": demo_checks,
        "evidence_checks": evidence_checks,
        "artifact_checks": artifact_checks,
        "known_gaps": known_gaps,
        "report_count": len(report_catalog),
        "country_profile_count": len(country_profile_read_models),
        "domain_detail_count": len(domain_detail_read_models),
    }


def _deduplicated_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _country_gap_markers(system_status_read_model: dict[str, Any]) -> list[str]:
    coverage_visibility = system_status_read_model.get("country_coverage_visibility", {})
    country_gap_rows = coverage_visibility.get("country_gap_rows", []) if isinstance(coverage_visibility, dict) else []
    markers: list[str] = []
    for row in country_gap_rows:
        if not isinstance(row, dict):
            continue
        country_id = str(row.get("country_id", "UNKNOWN"))
        gap_details = row.get("gap_details", [])
        if isinstance(gap_details, list) and gap_details:
            for detail in gap_details:
                if not isinstance(detail, dict):
                    continue
                domain = str(detail.get("domain", "unknown"))
                reason = str(detail.get("reason", "unknown"))
                markers.append(f"country_gap:{country_id}:{domain}:{reason}")
            continue
        for domain in row.get("missing_domains", []):
            markers.append(f"country_gap:{country_id}:{str(domain)}:missing")
    return markers


def _optional_artifact_gap(
    system_status_read_model: dict[str, Any],
    artifact_key: str,
    *,
    missing_fallback: str,
) -> list[str]:
    artifact_status = system_status_read_model.get("artifact_status", {})
    artifact_entry = artifact_status.get(artifact_key, {}) if isinstance(artifact_status, dict) else {}
    status = artifact_entry.get("status") if isinstance(artifact_entry, dict) else None
    reason = artifact_entry.get("reason") if isinstance(artifact_entry, dict) else None
    if status == "absent" and reason:
        return [f"{artifact_key}_absent:{reason}"]
    if status == "present":
        return []
    return [missing_fallback]
