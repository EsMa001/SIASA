from __future__ import annotations


def build_world_map_read_model(
    country_statuses: dict[str, str],
    active_domains: list[str],
    baseline_mode: str,
) -> dict[str, object]:
    countries = [
        {
            "country_id": country_id,
            "status": status,
            "active_domains": active_domains,
            "drill_down_target": f"/countries/{country_id}",
        }
        for country_id, status in sorted(country_statuses.items())
    ]
    return {
        "baseline_mode": baseline_mode,
        "active_domains": active_domains,
        "countries": countries,
    }
