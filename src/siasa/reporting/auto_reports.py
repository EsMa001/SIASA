"""SIASA automatic report generation.

Generates structured daily snapshot and anomaly reports from run results,
with configurable templates and scheduling integration.

Key APIs:
- ``generate_daily_snapshot_report(run_data)`` — daily status summary
- ``generate_anomaly_report(run_data, rules_results)`` — anomaly-focused report
- ``ReportConfig`` — configurable report parameters from YAML

Requirement trace: AP-F21, StR-301..310 (Automatische Reports)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ReportConfig:
    """Configuration for automatic report generation."""
    output_dir: str = "build/reports"
    daily_snapshot_enabled: bool = True
    anomaly_report_enabled: bool = True
    include_country_details: bool = True
    include_domain_breakdown: bool = True
    include_rule_assessments: bool = True
    max_countries_in_summary: int = 30


@dataclass(frozen=True)
class DailySnapshotReport:
    """Generated daily snapshot report."""
    report_id: str
    generated_at: str
    run_id: str
    title: str
    summary: str
    country_count: int
    domain_count: int
    overall_status: str
    country_summaries: list[dict[str, Any]]
    markdown: str


@dataclass(frozen=True)
class AnomalyReport:
    """Generated anomaly report."""
    report_id: str
    generated_at: str
    run_id: str
    title: str
    anomaly_count: int
    critical_count: int
    high_count: int
    anomalies: list[dict[str, Any]]
    markdown: str


def load_report_config(path: str | Path) -> ReportConfig:
    """Load report configuration from YAML."""
    content = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(content) or {}
    config = data.get("report_config", {})
    return ReportConfig(
        output_dir=str(config.get("output_dir", "build/reports")),
        daily_snapshot_enabled=bool(config.get("daily_snapshot_enabled", True)),
        anomaly_report_enabled=bool(config.get("anomaly_report_enabled", True)),
        include_country_details=bool(config.get("include_country_details", True)),
        include_domain_breakdown=bool(config.get("include_domain_breakdown", True)),
        include_rule_assessments=bool(config.get("include_rule_assessments", True)),
        max_countries_in_summary=int(config.get("max_countries_in_summary", 30)),
    )


def generate_daily_snapshot_report(
    run_id: str,
    country_scores: list[dict[str, Any]],
    config: ReportConfig | None = None,
) -> DailySnapshotReport:
    """Generate a daily status snapshot report.

    Args:
        run_id: The run identifier.
        country_scores: List of dicts with country_id, domain, status, score, data_sufficiency.
        config: Optional report configuration.

    Returns:
        DailySnapshotReport with summary and markdown content.
    """
    if config is None:
        config = ReportConfig()

    now = datetime.now(timezone.utc)
    report_id = f"SNAP-{now.strftime('%Y%m%d-%H%M%S')}"

    # Aggregate by country
    countries: dict[str, list[dict[str, Any]]] = {}
    for score in country_scores:
        cid = score.get("country_id", "")
        countries.setdefault(cid, []).append(score)

    country_summaries: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}

    for country_id in sorted(countries):
        scores = countries[country_id]
        domains = {s.get("domain", "") for s in scores}
        statuses = [s.get("status", "unknown") for s in scores]
        worst_status = _worst_status(statuses)
        avg_score = sum(s.get("score", 0.0) for s in scores) / max(len(scores), 1)

        status_counts[worst_status] = status_counts.get(worst_status, 0) + 1

        country_summaries.append({
            "country_id": country_id,
            "domain_count": len(domains),
            "worst_status": worst_status,
            "average_score": round(avg_score, 3),
            "domains": sorted(domains),
            "statuses": statuses,
        })

    # Determine overall status
    if status_counts.get("D4", 0) > 0:
        overall_status = "critical"
    elif status_counts.get("D3", 0) > 0:
        overall_status = "elevated"
    elif status_counts.get("D5", 0) > 0:
        overall_status = "contradictory"
    elif status_counts.get("D0", 0) > 0:
        overall_status = "data_gaps"
    else:
        overall_status = "normal"

    domain_set = {s.get("domain", "") for s in country_scores}
    summary = (
        f"Daily snapshot for run {run_id}: "
        f"{len(countries)} countries, {len(domain_set)} domains, "
        f"overall status: {overall_status}"
    )

    # Generate markdown
    markdown = _render_daily_markdown(
        report_id, now, run_id, summary, overall_status,
        country_summaries, status_counts, config,
    )

    return DailySnapshotReport(
        report_id=report_id,
        generated_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        run_id=run_id,
        title=f"SIASA Daily Snapshot — {now.strftime('%Y-%m-%d')}",
        summary=summary,
        country_count=len(countries),
        domain_count=len(domain_set),
        overall_status=overall_status,
        country_summaries=country_summaries,
        markdown=markdown,
    )


def generate_anomaly_report(
    run_id: str,
    rule_results: list[dict[str, Any]],
    config: ReportConfig | None = None,
) -> AnomalyReport:
    """Generate an anomaly report from rule evaluation results.

    Args:
        run_id: The run identifier.
        rule_results: List of dicts with rule_id, country_id, domain, severity,
            annotation_text, tags.
        config: Optional report configuration.

    Returns:
        AnomalyReport with anomalies and markdown content.
    """
    if config is None:
        config = ReportConfig()

    now = datetime.now(timezone.utc)
    report_id = f"ANOM-{now.strftime('%Y%m%d-%H%M%S')}"

    critical = [r for r in rule_results if r.get("severity") == "critical"]
    high = [r for r in rule_results if r.get("severity") == "high"]

    anomalies: list[dict[str, Any]] = []
    for result in sorted(rule_results, key=lambda r: _severity_order(r.get("severity", ""))):
        anomalies.append({
            "rule_id": result.get("rule_id", ""),
            "country_id": result.get("country_id", ""),
            "domain": result.get("domain", ""),
            "severity": result.get("severity", ""),
            "text": result.get("annotation_text", ""),
            "tags": result.get("tags", []),
        })

    markdown = _render_anomaly_markdown(
        report_id, now, run_id, anomalies, len(critical), len(high),
    )

    return AnomalyReport(
        report_id=report_id,
        generated_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        run_id=run_id,
        title=f"SIASA Anomaly Report — {now.strftime('%Y-%m-%d')}",
        anomaly_count=len(anomalies),
        critical_count=len(critical),
        high_count=len(high),
        anomalies=anomalies,
        markdown=markdown,
    )


def _worst_status(statuses: list[str]) -> str:
    """Return the worst domain status from a list."""
    order = {"D4": 0, "D5": 1, "D3": 2, "D2": 3, "D0": 4, "D1": 5}
    if not statuses:
        return "unknown"
    return min(statuses, key=lambda s: order.get(s, 99))


def _severity_order(severity: str) -> int:
    """Sort order: critical first."""
    return {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}.get(severity, 99)


def _render_daily_markdown(
    report_id: str,
    now: datetime,
    run_id: str,
    summary: str,
    overall_status: str,
    country_summaries: list[dict[str, Any]],
    status_counts: dict[str, int],
    config: ReportConfig,
) -> str:
    lines: list[str] = []
    lines.append(f"# SIASA Daily Snapshot — {now.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(f"**Report ID:** {report_id}")
    lines.append(f"**Run:** {run_id}")
    lines.append(f"**Generated:** {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append(f"**Overall Status:** {overall_status.upper()}")
    lines.append("")
    lines.append("## Status Distribution")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("| --- | --- |")
    for status in sorted(status_counts):
        lines.append(f"| {status} | {status_counts[status]} |")
    lines.append("")

    if config.include_country_details and country_summaries:
        lines.append("## Country Details")
        lines.append("")
        lines.append("| Country | Worst Status | Avg Score | Domains |")
        lines.append("| --- | --- | --- | --- |")
        for cs in country_summaries[:config.max_countries_in_summary]:
            lines.append(
                f"| {cs['country_id']} | {cs['worst_status']} | "
                f"{cs['average_score']:.3f} | {', '.join(cs['domains'])} |"
            )
        lines.append("")

    return "\n".join(lines)


def _render_anomaly_markdown(
    report_id: str,
    now: datetime,
    run_id: str,
    anomalies: list[dict[str, Any]],
    critical_count: int,
    high_count: int,
) -> str:
    lines: list[str] = []
    lines.append(f"# SIASA Anomaly Report — {now.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(f"**Report ID:** {report_id}")
    lines.append(f"**Run:** {run_id}")
    lines.append(f"**Generated:** {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append(f"**Anomalies:** {len(anomalies)} (critical: {critical_count}, high: {high_count})")
    lines.append("")

    if anomalies:
        lines.append("## Anomalies")
        lines.append("")
        lines.append("| Severity | Country | Domain | Rule | Description |")
        lines.append("| --- | --- | --- | --- | --- |")
        for a in anomalies:
            lines.append(
                f"| {a['severity']} | {a['country_id']} | {a['domain']} | "
                f"{a['rule_id']} | {a['text']} |"
            )
        lines.append("")
    else:
        lines.append("No anomalies detected.")
        lines.append("")

    return "\n".join(lines)
