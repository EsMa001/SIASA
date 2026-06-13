from __future__ import annotations


def _build_source_activation_readiness_summary(
    source_activation_readiness: list[dict[str, object]],
) -> dict[str, object]:
    status_counts: dict[str, int] = {}
    source_ids_by_status: dict[str, list[str]] = {}
    country_scope_by_status: dict[str, set[str]] = {}
    for item in source_activation_readiness:
        status = str(item.get("activation_status", "unknown"))
        source_id = str(item.get("source_id", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        source_ids_by_status.setdefault(status, []).append(source_id)
        country_scope_by_status.setdefault(status, set()).update(
            str(country_id)
            for country_id in item.get("applicable_country_ids", [])
            if str(country_id).strip()
        )
    blocked_sources = list(source_ids_by_status.get("blocked_missing_credentials", []))
    ready_sources = list(source_ids_by_status.get("configured_ready", []))
    blocked_countries = sorted(country_scope_by_status.get("blocked_missing_credentials", set()))
    ready_countries = sorted(country_scope_by_status.get("configured_ready", set()))
    return {
        "total_sources": len(source_activation_readiness),
        "blocked_source_count": len(blocked_sources),
        "configured_ready_count": len(ready_sources),
        "status_counts": status_counts,
        "blocked_sources": blocked_sources,
        "configured_ready_sources": ready_sources,
        "blocked_applicable_country_count": len(blocked_countries),
        "blocked_applicable_countries": blocked_countries,
        "configured_ready_applicable_country_count": len(ready_countries),
        "configured_ready_applicable_countries": ready_countries,
    }


def build_source_coverage_read_model(
    sources: list[dict[str, object]],
    *,
    missing_sources: list[str] | None = None,
    source_activation_readiness: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    failed_sources = [str(source["source_id"]) for source in sources if source.get("status") == "failed"]
    degraded_sources = [str(source["source_id"]) for source in sources if source.get("status") != "success"]
    source_status_summary: dict[str, int] = {}
    for source in sources:
        status = str(source.get("status", "unknown"))
        source_status_summary[status] = source_status_summary.get(status, 0) + 1
    readiness_rows = list(source_activation_readiness or [])
    return {
        "sources": sources,
        "failed_sources": failed_sources,
        "missing_sources": missing_sources or [],
        "degraded_sources": degraded_sources,
        "source_status_summary": source_status_summary,
        "source_activation_readiness": readiness_rows,
        "source_activation_readiness_summary": _build_source_activation_readiness_summary(readiness_rows),
    }
