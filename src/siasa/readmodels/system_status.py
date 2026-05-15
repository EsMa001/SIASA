from __future__ import annotations


def build_system_status_read_model(
    run_id: str,
    run_status: str,
    active_domains: list[str],
    countries_total: int,
    countries_with_updates: int,
    failed_sources: list[str],
    available_reports: list[str],
    snapshot_id: str | None,
    *,
    reprocessing_status: str = "idle",
    last_run: str | None = None,
    top_status_changes: list[dict[str, object]] | None = None,
    data_gaps: list[str] | None = None,
    artifact_status: dict[str, dict[str, object | None]] | None = None,
    country_coverage_visibility: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "run_status": run_status,
        "active_domains": active_domains,
        "coverage": {
            "countries_total": countries_total,
            "countries_with_updates": countries_with_updates,
        },
        "failed_sources": failed_sources,
        "available_reports": available_reports,
        "snapshot_id": snapshot_id,
        "reprocessing_status": reprocessing_status,
        "last_run": last_run,
        "top_status_changes": list(top_status_changes or []),
        "data_gaps": list(data_gaps or []),
        "artifact_status": dict(artifact_status or {}),
        "country_coverage_visibility": dict(country_coverage_visibility or {}),
    }
