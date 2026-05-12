from __future__ import annotations


def build_source_coverage_read_model(
    sources: list[dict[str, object]],
    *,
    missing_sources: list[str] | None = None,
) -> dict[str, object]:
    failed_sources = [str(source["source_id"]) for source in sources if source.get("status") == "failed"]
    return {
        "sources": sources,
        "failed_sources": failed_sources,
        "missing_sources": missing_sources or [],
    }
