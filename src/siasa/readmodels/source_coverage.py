from __future__ import annotations


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
    return {
        "sources": sources,
        "failed_sources": failed_sources,
        "missing_sources": missing_sources or [],
        "degraded_sources": degraded_sources,
        "source_status_summary": source_status_summary,
        "source_activation_readiness": list(source_activation_readiness or []),
    }
