from __future__ import annotations

from typing import Any

from siasa.governance.export_policy import enforce_export_policy

from .country_report import GeneratedReport, require_safe_identifier


def generate_domain_report(
    *,
    country_id: str,
    domain: str,
    anomaly_state: str,
    feature_values: list[dict[str, Any]],
    source_state: dict[str, str],
    uncertainty: list[str],
    linked_event_ids: list[str],
    contains_personal_data: bool = False,
    capability: str = "analysis",
) -> GeneratedReport:
    country_id = require_safe_identifier(country_id, "country_id")
    domain = require_safe_identifier(domain, "domain")
    for event_id in linked_event_ids:
        require_safe_identifier(event_id, "linked event identifier")
    payload = {
        "country_id": country_id,
        "domain": domain,
        "anomaly_state": anomaly_state,
        "feature_values": feature_values,
        "source_state": source_state,
        "uncertainty": uncertainty,
        "linked_event_ids": linked_event_ids,
        "contains_personal_data": contains_personal_data,
        "capability": capability,
    }
    enforce_export_policy(payload)
    markdown = "\n".join(
        [
            f"# Domain report: {country_id} / {domain}",
            f"Anomaly state: {anomaly_state}",
            f"Source state: {source_state}",
            f"Uncertainty: {', '.join(uncertainty) if uncertainty else '-'}",
            f"Linked events: {', '.join(linked_event_ids) if linked_event_ids else '-'}",
            f"Feature count: {len(feature_values)}",
        ]
    )
    return GeneratedReport(
        report_id=f"REP-DOMAIN-{country_id}-{domain}",
        report_type="domain_report",
        markdown=markdown,
        json_payload=payload,
    )


def generate_event_report(
    *,
    country_id: str,
    event_id: str,
    title: str,
    summary: str,
    related_domains: list[str],
    source_state: dict[str, str],
    contains_personal_data: bool = False,
    capability: str = "analysis",
) -> GeneratedReport:
    country_id = require_safe_identifier(country_id, "country_id")
    event_id = require_safe_identifier(event_id, "event_id")
    for domain in related_domains:
        require_safe_identifier(domain, "related domain identifier")
    payload = {
        "country_id": country_id,
        "event_id": event_id,
        "title": title,
        "summary": summary,
        "related_domains": related_domains,
        "source_state": source_state,
        "contains_personal_data": contains_personal_data,
        "capability": capability,
    }
    enforce_export_policy(payload)
    markdown = "\n".join(
        [
            f"# Event report: {event_id}",
            f"Country: {country_id}",
            f"Title: {title}",
            f"Summary: {summary}",
            f"Related domains: {', '.join(related_domains) if related_domains else '-'}",
            f"Source state: {source_state}",
        ]
    )
    return GeneratedReport(
        report_id=f"REP-EVENT-{event_id}",
        report_type="event_report",
        markdown=markdown,
        json_payload=payload,
    )


def generate_coverage_report(
    *,
    run_id: str,
    source_rows: list[dict[str, Any]],
    failed_sources: list[str],
    missing_sources: list[str],
    source_state: dict[str, str],
    contains_personal_data: bool = False,
    capability: str = "analysis",
) -> GeneratedReport:
    run_id = require_safe_identifier(run_id, "run_id")
    payload = {
        "run_id": run_id,
        "source_rows": source_rows,
        "failed_sources": failed_sources,
        "missing_sources": missing_sources,
        "source_state": source_state,
        "contains_personal_data": contains_personal_data,
        "capability": capability,
    }
    enforce_export_policy(payload)
    markdown = "\n".join(
        [
            f"# Coverage report: {run_id}",
            f"Failed sources: {', '.join(failed_sources) if failed_sources else '-'}",
            f"Missing sources: {', '.join(missing_sources) if missing_sources else '-'}",
            f"Source state: {source_state}",
            f"Tracked source rows: {len(source_rows)}",
        ]
    )
    return GeneratedReport(
        report_id=f"REP-COVERAGE-{run_id}",
        report_type="coverage_report",
        markdown=markdown,
        json_payload=payload,
    )
