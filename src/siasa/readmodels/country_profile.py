from __future__ import annotations


def build_country_profile_read_model(
    country_id: str,
    multi_domain_status: str,
    domain_states: dict[str, str],
    trends: dict[str, list[str]],
    drivers: list[str],
    linked_events: list[str],
) -> dict[str, object]:
    return {
        "country_id": country_id,
        "multi_domain_status": multi_domain_status,
        "domain_states": domain_states,
        "trends": trends,
        "drivers": drivers,
        "linked_events": linked_events,
    }
