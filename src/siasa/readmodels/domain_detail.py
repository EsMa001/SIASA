from __future__ import annotations


def build_domain_detail_read_model(
    country_id: str,
    domain: str,
    time_series: list[dict[str, object]],
    baseline_comparison: dict[str, object],
    feature_values: list[dict[str, object]],
    source_context: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "country_id": country_id,
        "domain": domain,
        "time_series": time_series,
        "baseline_comparison": baseline_comparison,
        "feature_values": feature_values,
        "source_context": source_context,
    }
