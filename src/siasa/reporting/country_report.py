from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from siasa.governance.export_policy import enforce_export_policy


@dataclass(frozen=True)
class GeneratedReport:
    report_id: str
    report_type: str
    markdown: str
    json_payload: dict[str, Any]



def generate_country_report(
    country_id: str,
    multi_domain_status: str,
    domain_states: dict[str, str],
    drivers: list[str],
    counter_indicators: list[str],
    coverage: float,
    uncertainty: list[str],
    linked_events: list[str],
    *,
    contains_personal_data: bool = False,
    capability: str = "analysis",
) -> GeneratedReport:
    payload = {
        "country_id": country_id,
        "multi_domain_status": multi_domain_status,
        "domain_states": domain_states,
        "drivers": drivers,
        "counter_indicators": counter_indicators,
        "coverage": coverage,
        "uncertainty": uncertainty,
        "linked_events": linked_events,
        "contains_personal_data": contains_personal_data,
        "capability": capability,
    }
    enforce_export_policy(payload)
    markdown = "\n".join(
        [
            f"# Country Report: {country_id}",
            f"Multi-domain status: {multi_domain_status}",
            f"Coverage: {coverage}",
            f"Drivers: {', '.join(drivers) if drivers else '-'}",
            f"Counter indicators: {', '.join(counter_indicators) if counter_indicators else '-'}",
            f"Uncertainty: {', '.join(uncertainty) if uncertainty else '-'}",
            f"Linked events: {', '.join(linked_events) if linked_events else '-'}",
        ]
    )
    return GeneratedReport(
        report_id=f"REP-COUNTRY-{country_id}",
        report_type="country_profile",
        markdown=markdown,
        json_payload=payload,
    )
