from __future__ import annotations


def build_country_profile_read_model(
    country_id: str,
    multi_domain_status: str,
    domain_states: dict[str, str],
    trends: dict[str, list[str]],
    drivers: list[str],
    linked_events: list[str],
    *,
    coverage: float | None = None,
    confidence: float | None = None,
    counter_indicators: list[str] | None = None,
    uncertainty: list[str] | None = None,
    annotations: list[str] | None = None,
    explanation_summary: str | None = None,
    country_context: dict[str, object] | None = None,
    source_depth: dict[str, object] | None = None,
    domain_gap_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "country_id": country_id,
        "multi_domain_status": multi_domain_status,
        "domain_states": domain_states,
        "trends": trends,
        "drivers": drivers,
        "linked_events": linked_events,
        "coverage": coverage,
        "confidence": confidence,
        "counter_indicators": counter_indicators or [],
        "uncertainty": uncertainty or [],
        "annotations": annotations or [],
        "explanation_summary": explanation_summary,
        "country_context": dict(country_context or {}),
        "source_depth": dict(source_depth or {}),
        "domain_gap_summary": dict(domain_gap_summary or {}),
    }
