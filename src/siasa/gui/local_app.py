from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from siasa.catalog import load_country_set
from siasa.readmodels.readiness import build_readiness_view_model
from siasa.readmodels.validation_backtest import build_historical_replay_summary
from siasa.traceability.consistency import build_repo_closure_report


SitePayload = dict[str, Any]


@dataclass(frozen=True)
class SiteBuildResult:
    output_dir: Path
    generated_files: list[Path]


def _page(title: str, body: str, *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    available_pages = available_pages or set()
    nav_entries = [
        ('index.html', 'Home'),
        ('coverage.html', 'Source / Coverage'),
        ('trends.html', 'Yearly Trend Page'),
        ('events.html', 'Current Events Page'),
        ('comparison.html', 'Cross-Country Comparison'),
        ('validation.html', 'Validation / Backtest View'),
        ('traceability.html', 'Traceability / Lineage View'),
        ('annotations.html', 'Analyst Annotations View'),
        ('reports.html', 'Report / Export View'),
        ('runs.html', 'System Status / Runs'),
        ('readiness.html', 'Demo / Release Readiness'),
    ]
    nav_html = ''.join(
        f"<a href='{html.escape(nav_prefix + href)}'>{html.escape(label)}</a>"
        for href, label in nav_entries
        if href in available_pages
    )
    return (
        "<!DOCTYPE html>"
        "<html lang='en'><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:Arial,sans-serif;margin:2rem;line-height:1.4;}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0;}"
        "th,td{border:1px solid #ccc;padding:0.5rem;text-align:left;vertical-align:top;}"
        "code,pre{background:#f5f5f5;padding:0.2rem 0.4rem;}"
        "nav a{margin-right:1rem;} .status{font-weight:bold;} ul{margin-top:0.3rem;}"
        ".uncertainty-badge{display:inline-block;margin:0.1rem 0.25rem 0.1rem 0;padding:0.15rem 0.45rem;border-radius:999px;background:#fee2e2;color:#991b1b;font-size:0.85rem;}"
        ".uncertainty-none{background:#e5e7eb;color:#374151;}"
        ".metric-meter p{margin:0.2rem 0;}"
        "</style></head><body>"
        f"<nav>{nav_html}</nav>"
        f"<h1>{html.escape(title)}</h1>"
        f"{body}"
        "</body></html>"
    )


def _json_block(data: Any) -> str:
    return f"<pre>{html.escape(json.dumps(data, indent=2, sort_keys=True))}</pre>"



def _coerce_chart_points(series: list[Any], *, label_key: str) -> list[tuple[str, float]]:
    points: list[tuple[str, float]] = []
    for index, item in enumerate(series, start=1):
        if isinstance(item, dict):
            value = item.get('value')
            label = item.get(label_key) or item.get('label') or index
            if isinstance(value, (int, float)):
                points.append((str(label), float(value)))
            continue
        if isinstance(item, (int, float)):
            points.append((str(index), float(item)))
    return points



def _trend_labels(series: list[Any], *, label_key: str) -> list[str]:
    labels: list[str] = []
    for index, item in enumerate(series, start=1):
        if isinstance(item, dict):
            label = item.get(label_key) or item.get('label')
            if label is not None:
                labels.append(str(label))
            continue
        if isinstance(item, str):
            labels.append(item)
            continue
        if isinstance(item, (int, float)):
            labels.append(str(index))
    return labels



def _render_line_chart(series: list[Any], *, label_key: str, chart_label: str) -> str:
    points = _coerce_chart_points(series, label_key=label_key)
    if not points:
        return "<p>No chartable data available.</p>"

    width = 320
    height = 120
    margin = 16
    values = [value for _, value in points]
    min_value = min(values)
    max_value = max(values)
    value_range = max_value - min_value

    coordinates: list[str] = []
    circle_markup: list[str] = []
    usable_width = max(width - (2 * margin), 1)
    usable_height = max(height - (2 * margin), 1)
    for index, (label, value) in enumerate(points):
        x = margin if len(points) == 1 else margin + (usable_width * index / (len(points) - 1))
        if value_range == 0:
            y = margin + (usable_height / 2)
        else:
            y = margin + ((max_value - value) / value_range) * usable_height
        coordinates.append(f"{x:.1f},{y:.1f}")
        circle_markup.append(
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3' fill='#0b6cff'><title>{html.escape(label)}: {value:.2f}</title></circle>"
        )

    labels_html = ''.join(
        f"<li>{html.escape(label)}: {value:.2f}</li>"
        for label, value in points
    )
    return (
        f"<figure><figcaption>{html.escape(chart_label)}</figcaption>"
        f"<svg viewBox='0 0 {width} {height}' width='{width}' height='{height}' role='img' aria-label='{html.escape(chart_label)}'>"
        f"<line x1='{margin}' y1='{height - margin}' x2='{width - margin}' y2='{height - margin}' stroke='#999' stroke-width='1' />"
        f"<line x1='{margin}' y1='{margin}' x2='{margin}' y2='{height - margin}' stroke='#999' stroke-width='1' />"
        f"<polyline fill='none' stroke='#0b6cff' stroke-width='2' points='{' '.join(coordinates)}' />"
        f"{''.join(circle_markup)}</svg>"
        f"<ul>{labels_html}</ul></figure>"
    )



def _delta_band(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return 'unknown'
    numeric = float(value)
    if numeric >= 0.25:
        return 'strong increase'
    if numeric >= 0.05:
        return 'increase'
    if numeric > -0.05:
        return 'stable'
    if numeric > -0.25:
        return 'decrease'
    return 'strong decrease'



def _render_historical_comparison_summary(series: list[Any], *, label_key: str) -> str:
    points = _coerce_chart_points(series, label_key=label_key)
    if not points:
        return "<p>No historical comparison summary available.</p>"

    first_label, first_value = points[0]
    last_label, last_value = points[-1]
    peak_label, peak_value = max(points, key=lambda item: item[1])
    trough_label, trough_value = min(points, key=lambda item: item[1])
    net_change = last_value - first_value
    return (
        "<h4>Historical Comparison Summary</h4>"
        "<table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>"
        f"<tr><td>Current vs First Label</td><td>{html.escape(last_label)} vs {html.escape(first_label)}</td></tr>"
        f"<tr><td>Net Change</td><td>{net_change:.2f}</td></tr>"
        f"<tr><td>Peak Label</td><td>{html.escape(peak_label)}</td></tr>"
        f"<tr><td>Peak Value</td><td>{peak_value:.2f}</td></tr>"
        f"<tr><td>Lowest Label</td><td>{html.escape(trough_label)}</td></tr>"
        f"<tr><td>Lowest Value</td><td>{trough_value:.2f}</td></tr>"
        f"<tr><td>Observation Count</td><td>{len(points)}</td></tr>"
        "</tbody></table>"
    )



def _render_baseline_comparison_summary(baseline_comparison: dict[str, Any], time_series: list[Any]) -> str:
    current_window = baseline_comparison.get('current_window')
    baseline_30d = baseline_comparison.get('baseline_30d')
    delta_to_baseline = baseline_comparison.get('delta_to_baseline')
    return (
        "<h3>Comparison vs Baseline</h3>"
        "<table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>"
        f"<tr><td>Current Window</td><td>{html.escape(str(current_window))}</td></tr>"
        f"<tr><td>30d Baseline</td><td>{html.escape(str(baseline_30d))}</td></tr>"
        f"<tr><td>Delta to Baseline</td><td>{html.escape(str(delta_to_baseline))}</td></tr>"
        f"<tr><td>Baseline Delta Band</td><td>{html.escape(_delta_band(delta_to_baseline))}</td></tr>"
        "</tbody></table>"
        "<h3>Historical Window Context</h3>"
        f"{_render_historical_comparison_summary(time_series, label_key='timestamp')}"
    )



def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())



def _country_metadata_lookup() -> dict[str, dict[str, str]]:
    repo_root = Path(__file__).resolve().parents[3]
    country_set_path = repo_root / 'vmodel' / 'project' / 'mvp_countries.yaml'
    lookup: dict[str, dict[str, str]] = {}
    for record in load_country_set(country_set_path):
        lookup[record.iso3] = {
            'country_name': record.country_name,
            'priority': record.priority,
            'selection_type': record.selection_type,
            'region': record.region,
            'rationale': record.rationale,
        }
    return lookup



def _region_anchor(region: str) -> tuple[float, float]:
    normalized = region.lower()
    if 'europe' in normalized:
        return (180.0, 70.0)
    if 'middle east' in normalized:
        return (205.0, 120.0)
    if 'asia' in normalized:
        return (255.0, 90.0)
    if 'africa' in normalized:
        return (185.0, 155.0)
    if 'north america' in normalized:
        return (75.0, 85.0)
    if 'oceania' in normalized or 'indo-pacific' in normalized:
        return (290.0, 170.0)
    return (155.0, 115.0)



def _status_color(status: str) -> str:
    return {
        'S0': '#6b7280',
        'S1': '#2563eb',
        'S2': '#0ea5e9',
        'S3': '#f59e0b',
        'S4': '#f97316',
        'S5': '#dc2626',
        'S6': '#7f1d1d',
    }.get(status, '#6b7280')



def _coerce_ratio(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    return None



def _ratio_band(value: Any) -> str:
    ratio = _coerce_ratio(value)
    if ratio is None:
        return 'unknown'
    if ratio >= 0.8:
        return 'high'
    if ratio >= 0.5:
        return 'medium'
    return 'low'



def _band_color(band: str) -> str:
    return {
        'high': '#15803d',
        'medium': '#d97706',
        'low': '#dc2626',
        'unknown': '#6b7280',
    }.get(band, '#6b7280')



def _freshness_band(value: Any) -> str:
    if value is None:
        return 'unknown'
    if isinstance(value, bool):
        return 'unknown'
    if isinstance(value, (int, float)):
        if float(value) <= 24.0:
            return 'fresh'
        if float(value) <= 168.0:
            return 'aging'
        return 'stale'
    return 'unknown'



def _freshness_band_color(band: str) -> str:
    return {
        'fresh': '#15803d',
        'aging': '#d97706',
        'stale': '#dc2626',
        'unknown': '#6b7280',
    }.get(band, '#6b7280')



def _format_freshness(value: Any) -> str:
    band = _freshness_band(value)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return band
    hours = int(value) if float(value).is_integer() else round(float(value), 1)
    return f'{band} ({hours}h)'



def _render_metric_meter(label: str, value: Any, *, fill_color: str) -> str:
    ratio = _coerce_ratio(value)
    band = _ratio_band(value)
    percent = int(round((ratio or 0.0) * 100))
    value_label = 'n/a' if ratio is None else f'{ratio:.2f}'
    width = 220
    height = 16
    fill_width = int(round((ratio or 0.0) * width))
    return (
        f"<div class='metric-meter metric-meter-{html.escape(label.lower().replace(' ', '-'))}'>"
        f"<p><strong>{html.escape(label)}</strong>: {html.escape(value_label)} ({html.escape(band)})</p>"
        f"<svg viewBox='0 0 {width} {height}' width='{width}' height='{height}' role='img' aria-label='{html.escape(label)} meter'>"
        f"<rect x='0' y='0' width='{width}' height='{height}' rx='6' fill='#e5e7eb'></rect>"
        f"<rect x='0' y='0' width='{fill_width}' height='{height}' rx='6' fill='{html.escape(fill_color)}'></rect>"
        f"<text x='{min(fill_width + 6, width - 36)}' y='12' font-size='10'>{percent}%</text>"
        "</svg>"
        "</div>"
    )



def _render_uncertainty_badges(items: list[Any]) -> str:
    labels = [str(item) for item in items if str(item)]
    if not labels:
        return "<span class='uncertainty-badge uncertainty-none'>none</span>"
    return ''.join(
        f"<span class='uncertainty-badge'>{html.escape(label)}</span>"
        for label in labels
    )



def _source_depth_band(source_count: Any) -> str:
    try:
        count = int(source_count)
    except (TypeError, ValueError):
        count = 0
    if count <= 1:
        return 'minimal'
    if count <= 3:
        return 'moderate'
    return 'deep'



def _render_missing_domain_badges(items: list[Any]) -> str:
    labels = [str(item) for item in items if str(item)]
    if not labels:
        return "<span class='uncertainty-badge uncertainty-none'>none</span>"
    return ''.join(
        f"<span class='uncertainty-badge'>missing:{html.escape(label)}</span>"
        for label in labels
    )



def _source_anchor_id(source_id: str) -> str:
    return f"source-{source_id}"



def _render_gap_details(gap_details: list[dict[str, Any]], *, coverage_href_prefix: str = 'coverage.html') -> str:
    if not gap_details:
        return "<span class='uncertainty-badge uncertainty-none'>none</span>"
    return ''.join(
        "<div class='gap-detail'>"
        f"<strong>{html.escape(str(detail.get('domain', 'UNKNOWN')))}</strong>: "
        f"{html.escape(str(detail.get('reason', 'unknown')))}"
        f" | sources={''.join(_render_gap_source_link(source_id, coverage_href_prefix) for source_id in detail.get('source_ids', [])) or 'none'}"
        f"{_render_gap_diagnostics(detail.get('diagnostics_by_source', {}))}"
        f"{_render_source_reason_details(list(detail.get('source_reason_details', [])))}"
        "</div>"
        for detail in gap_details
    )



def _render_gap_source_link(source_id: Any, coverage_href_prefix: str) -> str:
    source_label = str(source_id)
    href = f"{coverage_href_prefix}#{_source_anchor_id(source_label)}"
    return f"<a href='{html.escape(href)}'>{html.escape(source_label)}</a> "



def _render_gap_diagnostics(diagnostics_by_source: dict[str, Any]) -> str:
    if not diagnostics_by_source:
        return ''
    diagnostics = '; '.join(
        f"{source_id}: {diagnostic}"
        for source_id, diagnostic in diagnostics_by_source.items()
    )
    return f" | diagnostics={html.escape(diagnostics)}"



def _render_source_reason_details(source_reason_details: list[dict[str, Any]]) -> str:
    if not source_reason_details:
        return ''
    parts = []
    for detail in source_reason_details:
        source_id = html.escape(str(detail.get('source_id', 'UNKNOWN')))
        reason = html.escape(str(detail.get('reason', 'unknown')))
        diagnostics = html.escape(str(detail.get('diagnostics', '')))
        action_category = html.escape(str(detail.get('action_category', 'unknown')))
        severity = html.escape(str(detail.get('severity', 'low')))
        suffix = f" ({diagnostics})" if diagnostics else ''
        parts.append(f"{source_id}: {reason} | action={action_category} | severity={severity}{suffix}")
    return f" | source_causes={'; '.join(parts)}"



def _country_coverage_visibility_rows(system_status_read_model: dict[str, Any]) -> dict[str, Any]:
    visibility = system_status_read_model.get('country_coverage_visibility', {})
    if not isinstance(visibility, dict):
        return {
        'priority_summary': [],
        'source_depth_band_summary': [],
        'freshness_band_summary': [],
        'country_freshness_rows': [],
        'country_gap_rows': [],
        'missing_domain_totals': {},
        'remediation_watchlist': [],
    }
    return {
        'priority_summary': list(visibility.get('priority_summary', [])),
        'source_depth_band_summary': list(visibility.get('source_depth_band_summary', [])),
        'freshness_band_summary': list(visibility.get('freshness_band_summary', [])),
        'country_freshness_rows': list(visibility.get('country_freshness_rows', [])),
        'country_gap_rows': list(visibility.get('country_gap_rows', [])),
        'missing_domain_totals': dict(visibility.get('missing_domain_totals', {})),
        'remediation_watchlist': list(visibility.get('remediation_watchlist', [])),
    }



def _render_remediation_watchlist(visibility: dict[str, Any]) -> str:
    rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('priority_rank', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('priority_score', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('action_category', 'unknown')))}</td>"
        f"<td>severity={html.escape(str(row.get('severity', 'low')))}</td>"
        f"<td>{html.escape(str(row.get('country_count', 0)))}</td>"
        f"<td>{html.escape(str(row.get('source_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('countries', [])) or 'none')}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('source_ids', [])) or 'none')}</td>"
        f"<td>{html.escape(str(row.get('suggested_next_action', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('owner_hint', 'n/a')))}</td>"
        f"<td>{_render_watchlist_evidence_link(str(row.get('evidence_link', '')))}</td>"
        "</tr>"
        for row in visibility.get('remediation_watchlist', [])
    ) or "<tr><td colspan='11'>No remediation priorities recorded.</td></tr>"
    return (
        "<h3>Remediation Watchlist</h3>"
        "<p>Aggregated action categories highlight which operational problem classes should be addressed first.</p>"
        "<table><thead><tr><th>Priority Rank</th><th>Priority Score</th><th>Action Category</th><th>Severity</th><th>Countries</th><th>Sources</th><th>Country IDs</th><th>Source IDs</th><th>Suggested Next Action</th><th>Owner Hint</th><th>Evidence</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )



def _render_watchlist_evidence_link(evidence_link: str) -> str:
    if not evidence_link:
        return 'n/a'
    if not _is_safe_internal_evidence_link(evidence_link):
        return 'invalid evidence link'
    escaped = html.escape(evidence_link)
    return f"<a href='{escaped}'>{escaped}</a>"



def _is_safe_internal_evidence_link(evidence_link: str) -> bool:
    return bool(re.fullmatch(r"coverage\.html(?:#source-[A-Za-z0-9_.-]+)?", evidence_link))



def _render_country_coverage_visibility(visibility: dict[str, Any]) -> str:
    priority_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('priority', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('country_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('countries', [])) or 'none')}</td>"
        "</tr>"
        for row in visibility.get('priority_summary', [])
    ) or "<tr><td colspan='3'>No priority coverage summary available.</td></tr>"
    depth_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('band', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('country_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('countries', [])) or 'none')}</td>"
        "</tr>"
        for row in visibility.get('source_depth_band_summary', [])
    ) or "<tr><td colspan='3'>No source depth summary available.</td></tr>"
    freshness_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('band', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('country_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('countries', [])) or 'none')}</td>"
        "</tr>"
        for row in visibility.get('freshness_band_summary', [])
    ) or "<tr><td colspan='3'>No freshness summary available.</td></tr>"
    gap_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('priority', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('source_depth_band', 'n/a')))}</td>"
        f"<td>{html.escape(_format_freshness(row.get('freshness_hours')))}</td>"
        f"<td>{html.escape(str(row.get('source_count', 0)))}</td>"
        f"<td>{_render_missing_domain_badges(list(row.get('missing_domains', [])))}</td>"
        f"<td>{_render_gap_details(list(row.get('gap_details', [])))}</td>"
        "</tr>"
        for row in visibility.get('country_gap_rows', [])
    ) or "<tr><td colspan='7'>No explicit country domain gaps recorded.</td></tr>"
    missing_domain_totals = ''.join(
        f"<li>{html.escape(str(domain))}: {html.escape(str(count))}</li>"
        for domain, count in sorted(visibility.get('missing_domain_totals', {}).items())
    ) or '<li>none</li>'
    return (
        "<h3>Priority Coverage Summary</h3>"
        "<table><thead><tr><th>Priority</th><th>Countries</th><th>Country IDs</th></tr></thead>"
        f"<tbody>{priority_rows}</tbody></table>"
        "<h3>Source Depth Band Summary</h3>"
        "<table><thead><tr><th>Depth Band</th><th>Countries</th><th>Country IDs</th></tr></thead>"
        f"<tbody>{depth_rows}</tbody></table>"
        "<h3>Freshness Band Summary</h3>"
        "<table><thead><tr><th>Freshness Band</th><th>Countries</th><th>Country IDs</th></tr></thead>"
        f"<tbody>{freshness_rows}</tbody></table>"
        f"{_render_remediation_watchlist(visibility)}"
        "<h3>Country Coverage / Gap Watchlist</h3>"
        f"<div><strong>Missing domain totals</strong><ul>{missing_domain_totals}</ul></div>"
        "<table><thead><tr><th>Country</th><th>Priority</th><th>Depth Band</th><th>Freshness</th><th>Source Count</th><th>Missing Domains</th><th>Gap Cause</th></tr></thead>"
        f"<tbody>{gap_rows}</tbody></table>"
    )



def _render_country_coverage_matrix(visibility: dict[str, Any]) -> str:
    freshness_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('band', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('country_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('countries', [])) or 'none')}</td>"
        "</tr>"
        for row in visibility.get('freshness_band_summary', [])
    ) or "<tr><td colspan='3'>No freshness summary available.</td></tr>"
    rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('priority', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('source_depth_band', 'n/a')))}</td>"
        f"<td>{html.escape(_format_freshness(row.get('freshness_hours')))}</td>"
        f"<td>{html.escape(str(row.get('source_count', 0)))}</td>"
        f"<td>{html.escape(str(row.get('missing_domain_count', 0)))}</td>"
        f"<td>{_render_missing_domain_badges(list(row.get('missing_domains', [])))}</td>"
        f"<td>{_render_gap_details(list(row.get('gap_details', [])))}</td>"
        "</tr>"
        for row in visibility.get('country_gap_rows', [])
    ) or "<tr><td colspan='8'>No per-country coverage gaps recorded.</td></tr>"
    return (
        f"{_render_remediation_watchlist(visibility)}"
        "<h3>Freshness Band Summary</h3>"
        "<table><thead><tr><th>Freshness Band</th><th>Countries</th><th>Country IDs</th></tr></thead>"
        f"<tbody>{freshness_rows}</tbody></table>"
        "<h3>Country Coverage / Gap Matrix</h3>"
        "<p>Priority, source depth, explicit missing-domain badges, and freshness bands stay visible alongside source-level coverage.</p>"
        "<table><thead><tr><th>Country</th><th>Priority</th><th>Depth Band</th><th>Freshness</th><th>Source Count</th><th>Gap Count</th><th>Missing Domains</th><th>Gap Cause</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )



def _render_country_trust_visualization(country_profile_read_models: dict[str, dict[str, Any]]) -> str:
    if not country_profile_read_models:
        return "<p>No country trust metrics available.</p>"

    rows: list[str] = []
    svg_rows: list[str] = []
    for index, (country_id, profile) in enumerate(sorted(country_profile_read_models.items())):
        coverage = profile.get('coverage')
        confidence = profile.get('confidence')
        coverage_ratio = _coerce_ratio(coverage) or 0.0
        confidence_ratio = _coerce_ratio(confidence) or 0.0
        y = 28 + (index * 26)
        svg_rows.append(
            f"<text x='8' y='{y + 11}' font-size='10'>{html.escape(country_id)}</text>"
            f"<rect x='64' y='{y}' width='100' height='8' rx='4' fill='#e5e7eb'></rect>"
            f"<rect x='64' y='{y}' width='{int(round(coverage_ratio * 100))}' height='8' rx='4' fill='#0ea5e9'></rect>"
            f"<rect x='182' y='{y}' width='100' height='8' rx='4' fill='#e5e7eb'></rect>"
            f"<rect x='182' y='{y}' width='{int(round(confidence_ratio * 100))}' height='8' rx='4' fill='#8b5cf6'></rect>"
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td>{html.escape(str(coverage))}</td>"
            f"<td>{html.escape(_ratio_band(coverage))}</td>"
            f"<td>{html.escape(str(confidence))}</td>"
            f"<td>{html.escape(_ratio_band(confidence))}</td>"
            f"<td>{_render_uncertainty_badges(profile.get('uncertainty', []))}</td>"
            "</tr>"
        )
    chart_height = max(72, 40 + (len(country_profile_read_models) * 26))
    return (
        "<h3>Coverage / Confidence Visualization</h3>"
        "<p>Coverage and confidence are rendered as country-level trust bars so gaps remain visually explicit.</p>"
        "<svg viewBox='0 0 300 {height}' width='300' height='{height}' role='img' aria-label='Coverage and confidence by country'>"
        "<text x='64' y='18' font-size='10'>Coverage</text>"
        "<text x='182' y='18' font-size='10'>Confidence</text>"
        "{rows}"
        "</svg>"
        "<table><thead><tr><th>Country</th><th>Coverage</th><th>Coverage Band</th><th>Confidence</th><th>Confidence Band</th><th>Uncertainty</th></tr></thead>"
        "<tbody>{table_rows}</tbody></table>"
    ).format(height=chart_height, rows=''.join(svg_rows), table_rows=''.join(rows))



def _render_domain_projection(country_profile_read_models: dict[str, dict[str, Any]], active_domains: list[str]) -> str:
    if not country_profile_read_models or not active_domains:
        return "<p>No domain projection data available.</p>"

    rows: list[str] = []
    for country_id, profile in sorted(country_profile_read_models.items()):
        domain_cells = ''.join(
            f"<td class='domain-projection-value'>{html.escape(str(profile.get('domain_states', {}).get(domain, 'n/a')))}</td>"
            for domain in active_domains
        )
        rows.append(
            f"<tr class='domain-projection-row' data-country-id='{html.escape(country_id)}'>"
            f"<td>{html.escape(country_id)}</td>"
            f"{domain_cells}"
            f"<td>{_render_uncertainty_badges(profile.get('uncertainty', []))}</td>"
            "</tr>"
        )
    header_cells = ''.join(f"<th>{html.escape(domain)} Status</th>" for domain in active_domains)
    return (
        "<h3>Domain Projection View</h3>"
        "<p>Domain-specific projection makes the active domain status slice explicit per visible country.</p>"
        f"<table id='domain-projection-table'><thead><tr><th>Country</th>{header_cells}<th>Uncertainty</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )



def _render_world_map_visualization(
    world_map_read_model: dict[str, Any],
    available_country_ids: set[str],
    coverage_visibility: dict[str, Any] | None = None,
) -> str:
    metadata_lookup = _country_metadata_lookup()
    coverage_by_country = {
        str(row.get('country_id', 'UNKNOWN')): row
        for row in (coverage_visibility or {}).get('country_freshness_rows', [])
    }
    region_offsets: dict[str, int] = {}
    markers: list[str] = []
    labels: list[str] = []
    legend_rows: list[str] = []

    for country in world_map_read_model.get('countries', []):
        country_id = str(country.get('country_id', 'UNKNOWN'))
        status = str(country.get('status', 'n/a'))
        country_visibility = coverage_by_country.get(country_id, {})
        freshness_label = _format_freshness(country_visibility.get('freshness_hours'))
        freshness_band = _freshness_band(country_visibility.get('freshness_hours'))
        metadata = metadata_lookup.get(country_id, {})
        region = str(metadata.get('region', 'Other / Unknown'))
        anchor_x, anchor_y = _region_anchor(region)
        offset_index = region_offsets.get(region, 0)
        region_offsets[region] = offset_index + 1
        x = anchor_x + (offset_index % 4) * 18
        y = anchor_y + (offset_index // 4) * 18
        color = _status_color(status)
        freshness_stroke = _freshness_band_color(freshness_band)
        href = f"countries/{country_id}.html" if country_id in available_country_ids else None
        marker = (
            f"<a href='{html.escape(href)}'><circle cx='{x:.1f}' cy='{y:.1f}' r='7' fill='{color}' stroke='{freshness_stroke}' stroke-width='2'>"
            f"<title>{html.escape(country_id)} — {html.escape(status)} — {html.escape(region)} — freshness={html.escape(freshness_label)}</title></circle></a>"
            if href
            else f"<circle cx='{x:.1f}' cy='{y:.1f}' r='7' fill='{color}' stroke='{freshness_stroke}' stroke-width='2'>"
                 f"<title>{html.escape(country_id)} — {html.escape(status)} — {html.escape(region)} — freshness={html.escape(freshness_label)}</title></circle>"
        )
        markers.append(marker)
        labels.append(f"<text x='{x + 10:.1f}' y='{y + 4:.1f}' font-size='10'>{html.escape(country_id)}</text>")
        legend_rows.append(
            "<tr>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td>{html.escape(metadata.get('country_name', country_id))}</td>"
            f"<td>{html.escape(region)}</td>"
            f"<td>{html.escape(str(metadata.get('priority', 'n/a')))}</td>"
            f"<td>{html.escape(freshness_label)}</td>"
            f"<td><span class='status'>{html.escape(status)}</span></td>"
            "</tr>"
        )

    return (
        "<h3>Map Visualization</h3>"
        "<p>Region-anchored anomaly markers based on governed MVP country metadata, with freshness-colored marker outlines.</p>"
        "<svg viewBox='0 0 340 210' width='340' height='210' role='img' aria-label='World anomaly map'>"
        "<rect x='5' y='5' width='330' height='200' rx='8' fill='#eef6ff' stroke='#cbd5e1' />"
        "<text x='25' y='35' font-size='12'>North America</text>"
        "<text x='165' y='35' font-size='12'>Europe</text>"
        "<text x='245' y='35' font-size='12'>Asia</text>"
        "<text x='165' y='150' font-size='12'>Africa / Middle East</text>"
        f"{''.join(markers)}{''.join(labels)}"
        "</svg>"
        "<table><thead><tr><th>Country</th><th>Name</th><th>Region</th><th>Priority</th><th>Freshness</th><th>Status</th></tr></thead>"
        f"<tbody>{''.join(legend_rows)}</tbody></table>"
    )



def _annotation_index(annotations_view_model: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if annotations_view_model is None:
        return {}
    return {
        str(annotation.get('annotation_id')): annotation
        for annotation in annotations_view_model.get('annotations', [])
    }



def _trend_filter_options(country_profile_read_models: dict[str, dict[str, Any]]) -> list[str]:
    labels: set[str] = set()
    for profile in country_profile_read_models.values():
        labels.update(_trend_labels(profile.get('trends', {}).get('yearly', []), label_key='label'))
    return sorted(labels)



def _annotation_details_html(annotation_ids: list[str], annotations_view_model: dict[str, Any] | None) -> str:
    annotation_lookup = _annotation_index(annotations_view_model)
    if not annotation_ids:
        return "<p>No annotations.</p>"

    rows: list[str] = []
    for annotation_id in annotation_ids:
        annotation = annotation_lookup.get(str(annotation_id))
        if annotation is None:
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(annotation_id))}</td>"
                "<td colspan='6'>Annotation details unavailable.</td>"
                "</tr>"
            )
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(annotation.get('annotation_id', '')))}</td>"
            f"<td>{html.escape(str(annotation.get('scope', '')))}</td>"
            f"<td>{html.escape(str(annotation.get('annotation_type', '')))}</td>"
            f"<td>{html.escape(str(annotation.get('author', '')))}</td>"
            f"<td>{html.escape(str(annotation.get('review_status', '')))}</td>"
            f"<td>{html.escape(', '.join(str(item) for item in annotation.get('linked_items', [])))}</td>"
            f"<td>{html.escape(str(annotation.get('text', '')))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>ID</th><th>Scope</th><th>Type</th><th>Author</th><th>Review</th><th>Linked Items</th><th>Text</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )



def _annotation_workflow_href(*, nav_prefix: str, scope: str, linked_item: str, annotation_type: str) -> str:
    query = (
        f"scope={quote(scope, safe='')}"
        f"&linked_item={quote(linked_item, safe='')}"
        f"&annotation_type={quote(annotation_type, safe='')}"
    )
    return f"{nav_prefix}annotations.html?{query}"



def _annotation_workflow_seed(annotations_view_model: dict[str, Any]) -> str:
    payload = {
        'annotations': list(annotations_view_model.get('annotations', [])),
        'allowed_scopes': ['country', 'domain', 'signal', 'event', 'snapshot'],
        'allowed_annotation_types': ['context_note', 'false_positive_note', 'source_quality_note', 'lineage_note', 'review_note'],
        'allowed_severity_assessments': ['not_security_relevant', 'relevant', 'uncertain'],
        'allowed_confidence_assessments': ['low', 'medium', 'high'],
        'allowed_review_statuses': ['unreviewed', 'draft', 'reviewed', 'accepted', 'rejected'],
    }
    return json.dumps(payload, sort_keys=True).replace('</', '<\\/')



def load_site_payload_from_artifacts(artifacts_dir: Path) -> SitePayload:
    snapshot = _load_json(artifacts_dir / 'snapshot.json')

    readmodels_dir = artifacts_dir / 'readmodels'
    world_map_read_model = _load_json(readmodels_dir / 'world_map.json')
    source_coverage_read_model = _load_json(readmodels_dir / 'source_coverage.json')
    system_status_read_model = _load_json(readmodels_dir / 'system_status.json')
    system_status_read_model.setdefault('run_id', snapshot.get('run_id'))
    system_status_read_model.setdefault('run_status', snapshot.get('status'))
    system_status_read_model.setdefault('snapshot_id', snapshot.get('snapshot_id'))
    system_status_read_model.setdefault('active_domains', snapshot.get('active_domains', []))

    country_profile_read_models = {
        country_file.stem: _load_json(country_file)
        for country_file in sorted((readmodels_dir / 'country_profiles').glob('*.json'))
    }
    domain_detail_read_models = {
        (str(read_model['country_id']), str(read_model['domain'])): read_model
        for read_model in (
            _load_json(domain_file)
            for domain_file in sorted((readmodels_dir / 'domain_details').glob('*.json'))
        )
    }
    report_catalog = {
        report_file.stem: _load_json(report_file)
        for report_file in sorted((artifacts_dir / 'reports').glob('*.json'))
    }
    validation_view_model = None
    validation_view_path = readmodels_dir / 'validation_backtest.json'
    if validation_view_path.exists():
        validation_view_model = _load_json(validation_view_path)
    traceability_view_model = None
    traceability_view_path = readmodels_dir / 'traceability_lineage.json'
    if traceability_view_path.exists():
        traceability_view_model = _load_json(traceability_view_path)
    repo_closure_view_model = None
    repo_closure_view_path = readmodels_dir / 'repo_closure.json'
    if repo_closure_view_path.exists():
        repo_closure_view_model = _load_json(repo_closure_view_path)
    else:
        repo_closure_view_model = build_repo_closure_report(repo_root=Path(__file__).resolve().parents[3])
    annotations_view_model = None
    annotations_view_path = readmodels_dir / 'annotations.json'
    if annotations_view_path.exists():
        annotations_view_model = _load_json(annotations_view_path)
    else:
        annotations_view_model = {'annotations': [], 'by_scope': {}, 'by_linked_item': {}}
    readiness_view_model = None
    readiness_view_path = readmodels_dir / 'readiness.json'
    if readiness_view_path.exists():
        readiness_view_model = _load_json(readiness_view_path)

    return {
        'world_map_read_model': world_map_read_model,
        'country_profile_read_models': country_profile_read_models,
        'domain_detail_read_models': domain_detail_read_models,
        'source_coverage_read_model': source_coverage_read_model,
        'report_catalog': report_catalog,
        'system_status_read_model': system_status_read_model,
        'validation_view_model': validation_view_model,
        'traceability_view_model': traceability_view_model,
        'repo_closure_view_model': repo_closure_view_model,
        'annotations_view_model': annotations_view_model,
        'readiness_view_model': readiness_view_model,
    }


def _render_index(
    world_map_read_model: dict[str, Any],
    available_country_ids: set[str] | None = None,
    country_profile_read_models: dict[str, dict[str, Any]] | None = None,
    system_status_read_model: dict[str, Any] | None = None,
    *,
    nav_prefix: str = '',
    available_pages: set[str] | None = None,
) -> str:
    rows = []
    available_country_ids = available_country_ids or set()
    country_profile_read_models = country_profile_read_models or {}
    system_status_read_model = system_status_read_model or {}
    coverage_visibility = _country_coverage_visibility_rows(system_status_read_model)
    coverage_by_country = {
        str(row.get('country_id', 'UNKNOWN')): row
        for row in coverage_visibility.get('country_freshness_rows', [])
    }
    trend_options = _trend_filter_options(country_profile_read_models)
    for country in world_map_read_model.get("countries", []):
        country_id = str(country["country_id"])
        status = str(country["status"])
        active_domains = [str(domain) for domain in country.get('active_domains', [])]
        country_profile = country_profile_read_models.get(country_id, {})
        country_context = country_profile.get('country_context', {})
        source_depth = country_profile.get('source_depth', {})
        domain_gap_summary = country_profile.get('domain_gap_summary', {})
        trend_labels = ','.join(
            _trend_labels(
                country_profile.get('trends', {}).get('yearly', []),
                label_key='label',
            )
        )
        domain_state_attributes = ''.join(
            f" data-domain-{html.escape(domain.lower())}-status='{html.escape(str(country_profile.get('domain_states', {}).get(domain, 'n/a')))}'"
            for domain in world_map_read_model.get('active_domains', [])
        )
        has_country_page = country_id in available_country_ids
        country_cell = (
            f"<a href='countries/{html.escape(country_id)}.html'>{html.escape(country_id)}</a>"
            if has_country_page
            else html.escape(country_id)
        )
        drill_down_cell = f"countries/{html.escape(country_id)}.html" if has_country_page else "not available"
        support_status = "supported" if has_country_page else "not available"
        source_ids = [str(item) for item in source_depth.get('source_ids', [])]
        source_depth_band = _source_depth_band(source_depth.get('source_count', 0))
        freshness_entry = coverage_by_country.get(country_id, {})
        freshness_hours = freshness_entry.get('freshness_hours')
        freshness_band = _freshness_band(freshness_hours)
        missing_domains = [str(item) for item in domain_gap_summary.get('missing_domains', [])]
        rows.append(
            f"<tr class='overview-row' data-country-id='{html.escape(country_id)}' data-active-domains='{html.escape(','.join(active_domains))}' data-status='{html.escape(status)}' data-trend-labels='{html.escape(trend_labels)}' data-priority='{html.escape(str(country_context.get('priority', 'n/a')))}' data-source-depth-band='{html.escape(source_depth_band)}' data-freshness-band='{html.escape(freshness_band)}' data-missing-domain-count='{html.escape(str(len(missing_domains)))}'{domain_state_attributes}>"
            f"<td>{country_cell}</td>"
            f"<td>{html.escape(support_status)}</td>"
            f"<td>{html.escape(str(country_context.get('priority', 'n/a')))}</td>"
            f"<td class='status'>{html.escape(status)}</td>"
            f"<td>{html.escape(', '.join(active_domains))}</td>"
            f"<td>{html.escape(str(source_depth.get('source_count', 0)))} ({html.escape(', '.join(source_ids) or 'none')})</td>"
            f"<td>{html.escape(source_depth_band)}</td>"
            f"<td>{html.escape(_format_freshness(freshness_hours))}</td>"
            f"<td>{_render_missing_domain_badges(missing_domains)}</td>"
            f"<td>{drill_down_cell}</td>"
            "</tr>"
        )

    top_status_changes_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(change.get('country_id', '')))}</td>"
        f"<td>{html.escape(str(change.get('from_status', 'n/a')))} → {html.escape(str(change.get('to_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(change.get('direction', 'n/a')))}</td>"
        "</tr>"
        for change in system_status_read_model.get('top_status_changes', [])
    ) or "<tr><td colspan='3'>No status changes recorded.</td></tr>"
    data_gap_items = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in system_status_read_model.get('data_gaps', [])
    ) or "<li>none</li>"
    failed_sources = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in system_status_read_model.get('failed_sources', [])
    ) or "<li>none</li>"

    controls_html = (
        "<h3>Baseline / View Controls</h3>"
        f"<p>Baseline Mode: <strong>{html.escape(str(world_map_read_model.get('baseline_mode', 'unknown')))}</strong></p>"
        "<label for='priority-filter'>Priority Filter</label> "
        "<select id='priority-filter' name='priority-filter'>"
        "<option value='all'>All priorities</option>"
        + ''.join(
            f"<option value='{html.escape(str(row.get('priority', 'n/a')))}'>{html.escape(str(row.get('priority', 'n/a')))}</option>"
            for row in coverage_visibility.get('priority_summary', [])
        )
        + "</select> "
        "<label for='domain-filter'>Domain Filter</label> "
        "<select id='domain-filter' name='domain-filter'>"
        "<option value='all'>All active domains</option>"
        + ''.join(
            f"<option value='{html.escape(domain)}'>{html.escape(domain)}</option>"
            for domain in world_map_read_model.get('active_domains', [])
        )
        + "</select> "
        "<label for='time-window'>Time Window</label> "
        "<select id='time-window' name='time-window'><option value='all'>All trend labels</option>"
        + ''.join(
            f"<option value='{html.escape(label)}'>{html.escape(label)}</option>"
            for label in trend_options
        )
        + "</select> "
        "<label for='view-mode'>View Mode</label> "
        "<select id='view-mode' name='view-mode'>"
        "<option value='multi-domain'>Multi-domain status</option>"
        "<option value='coverage'>Coverage emphasis</option>"
        + ''.join(
            f"<option value='domain-{html.escape(domain)}'>Domain {html.escape(domain)} projection</option>"
            for domain in world_map_read_model.get('active_domains', [])
        )
        + "</select>"
    )

    body = (
        "<h2>Daily Global Review</h2>"
        f"<p>Run status: <span class='status'>{html.escape(str(system_status_read_model.get('run_status', 'n/a')))}</span></p>"
        f"<p>Snapshot ID: {html.escape(str(system_status_read_model.get('snapshot_id', 'n/a')))}</p>"
        f"<p>Coverage summary: {html.escape(str(system_status_read_model.get('coverage', {})))}</p>"
        f"<h3>Failed Sources</h3><ul>{failed_sources}</ul>"
        "<h3>Data Gaps / Trust Limits</h3>"
        f"<ul>{data_gap_items}</ul>"
        "<h3>Top Status Changes</h3>"
        "<table><thead><tr><th>Country</th><th>Status Change</th><th>Direction</th></tr></thead>"
        f"<tbody>{top_status_changes_rows}</tbody></table>"
        "<h2>World Anomaly Map</h2>"
        f"<p>Baseline mode: <strong>{html.escape(str(world_map_read_model.get('baseline_mode', 'unknown')))}</strong></p>"
        f"<p>Active domains: {html.escape(', '.join(world_map_read_model.get('active_domains', [])))}</p>"
        f"{controls_html}"
        "<p id='overview-filter-result'>Selected Time Window: all trend labels | View Mode: multi-domain status</p>"
        f"<div id='map-visualization-block'>{_render_world_map_visualization(world_map_read_model, available_country_ids, coverage_visibility)}</div>"
        f"<div id='coverage-visualization-block' style='display:none'>{_render_country_trust_visualization(country_profile_read_models)}</div>"
        f"<div id='domain-projection-block' style='display:none'>{_render_domain_projection(country_profile_read_models, [str(domain) for domain in world_map_read_model.get('active_domains', [])])}</div>"
        f"{_render_country_coverage_visibility(coverage_visibility)}"
        "<h2>Global Overview</h2>"
        "<div id='overview-table-block'><table id='overview-table'><thead><tr><th>Country</th><th>Support Status</th><th>Priority Class</th><th>Multi-Domain Status</th><th>Active Domains</th><th>Source Depth</th><th>Depth Band</th><th>Freshness</th><th>Domain Gaps</th><th>Drill-down</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
        "<script>"
        "function applyOverviewViewMode(){"
        "const viewMode=document.getElementById('view-mode').value;"
        "const showCoverage=viewMode==='coverage';"
        "const showDomain=viewMode.startsWith('domain-');"
        "const selectedDomain=showDomain?viewMode.replace('domain-','').toUpperCase():'';"
        "document.getElementById('map-visualization-block').style.display=(!showCoverage&&!showDomain)?'':'none';"
        "document.getElementById('coverage-visualization-block').style.display=showCoverage?'':'none';"
        "document.getElementById('domain-projection-block').style.display=showDomain?'':'none';"
        "document.querySelectorAll('.domain-projection-value').forEach((cell)=>{cell.style.display='';});"
        "if(showDomain){"
        "const headers=Array.from(document.querySelectorAll('#domain-projection-table thead th'));"
        "headers.forEach((header,index)=>{if(index===0||index===headers.length-1){header.style.display='';return;} const domainLabel=(header.textContent||'').split(' ')[0]; header.style.display=(domainLabel===selectedDomain)?'':'none';});"
        "document.querySelectorAll('#domain-projection-table tbody tr').forEach((row)=>{const domainAStatus=row.dataset.domainAStatus||''; const domainBStatus=row.dataset.domainBStatus||''; const domainDStatus=row.dataset.domainDStatus||''; row.querySelectorAll('.domain-projection-value').forEach((cell,index)=>{const mapped=['A','B','D','C','E'][index]||''; cell.style.display=(mapped===selectedDomain)?'':'none';}); row.style.display=row.style.display==='none'?'none':'';});"
        "}"
        "}"
        "function applyOverviewFilters(){"
        "const priority=document.getElementById('priority-filter').value;"
        "const domain=document.getElementById('domain-filter').value;"
        "const timeWindow=document.getElementById('time-window').value;"
        "const viewMode=document.getElementById('view-mode').value;"
        "document.querySelectorAll('.overview-row').forEach((row)=>{"
        "const rowPriority=row.dataset.priority||'';"
        "const domains=(row.dataset.activeDomains||'').split(',').filter(Boolean);"
        "const trendLabels=(row.dataset.trendLabels||'').split(',').filter(Boolean);"
        "const priorityMatch=(priority==='all'||rowPriority===priority);"
        "const domainMatch=(domain==='all'||domains.includes(domain));"
        "const timeMatch=(timeWindow==='all'||trendLabels.includes(timeWindow));"
        "row.style.display=(priorityMatch&&domainMatch&&timeMatch)?'':'none';"
        "});"
        "document.querySelectorAll('.domain-projection-row').forEach((row)=>{"
        "const sourceRow=document.querySelector(`.overview-row[data-country-id='${row.dataset.countryId}']`);"
        "row.dataset.domainAStatus=sourceRow?.dataset.domainAStatus||'';"
        "row.dataset.domainBStatus=sourceRow?.dataset.domainBStatus||'';"
        "row.dataset.domainDStatus=sourceRow?.dataset.domainDStatus||'';"
        "row.style.display=(sourceRow&&sourceRow.style.display!=='none')?'':'none';"
        "});"
        "applyOverviewViewMode();"
        "document.getElementById('overview-filter-result').textContent='Priority Filter: '+priority+' | Selected Time Window: '+timeWindow+' | View Mode: '+viewMode;"
        "}"
        "document.getElementById('priority-filter').addEventListener('change', applyOverviewFilters);"
        "document.getElementById('domain-filter').addEventListener('change', applyOverviewFilters);"
        "document.getElementById('time-window').addEventListener('change', applyOverviewFilters);"
        "document.getElementById('view-mode').addEventListener('change', applyOverviewFilters);"
        "applyOverviewFilters();"
        "</script>"
    )
    return _page("World Anomaly Map / Global Overview", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_country(
    country_profile: dict[str, Any],
    annotations_view_model: dict[str, Any] | None = None,
    available_domain_targets: dict[str, str] | None = None,
    *,
    nav_prefix: str = '',
    available_pages: set[str] | None = None,
) -> str:
    domain_rows = ''.join(
        f"<tr><td>{html.escape(domain)}</td><td>{html.escape(status)}</td></tr>"
        for domain, status in country_profile.get('domain_states', {}).items()
    )
    annotation_ids = [str(item) for item in country_profile.get('annotations', [])]
    available_domain_targets = available_domain_targets or {}
    domain_link_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(domain)}</td>"
        f"<td><a href='{html.escape(target)}'>{html.escape(domain)} detail</a></td>"
        "</tr>"
        if target
        else "<tr>"
             f"<td>{html.escape(domain)}</td>"
             f"<td>{html.escape(domain)} — not available</td>"
             "</tr>"
        for domain, target in (
            (domain, available_domain_targets.get(domain))
            for domain in country_profile.get('domain_states', {}).keys()
        )
    )
    explanation_summary = country_profile.get('explanation_summary') or 'No explanation summary available.'
    country_context = country_profile.get('country_context', {})
    source_depth = country_profile.get('source_depth', {})
    domain_gap_summary = country_profile.get('domain_gap_summary', {})
    source_ids = [str(item) for item in source_depth.get('source_ids', [])]
    missing_domains = [str(item) for item in domain_gap_summary.get('missing_domains', [])]
    gap_details = [dict(item) for item in domain_gap_summary.get('gap_details', []) if isinstance(item, dict)]
    country_id = str(country_profile.get('country_id', 'UNKNOWN'))
    annotation_workflow_href = _annotation_workflow_href(
        nav_prefix=nav_prefix,
        scope='country',
        linked_item=country_id,
        annotation_type='context_note',
    )
    annotation_workflow_link_html = (
        f"<p><a href='{html.escape(annotation_workflow_href)}'>Open Annotation Workflow for this Country</a></p>"
        if annotations_view_model is not None and available_pages is not None and 'annotations.html' in available_pages
        else ''
    )
    trust_summary_html = (
        "<h3>Trust / Uncertainty Summary</h3>"
        f"<p>Coverage band: <strong>{html.escape(_ratio_band(country_profile.get('coverage')))}</strong> | Confidence band: <strong>{html.escape(_ratio_band(country_profile.get('confidence')))}</strong></p>"
        f"<h4>Coverage Meter</h4>{_render_metric_meter('Coverage', country_profile.get('coverage'), fill_color='#0ea5e9')}"
        f"<h4>Confidence Meter</h4>{_render_metric_meter('Confidence', country_profile.get('confidence'), fill_color='#8b5cf6')}"
        f"<h4>Uncertainty Flags</h4><div>{_render_uncertainty_badges(country_profile.get('uncertainty', []))}</div>"
    )
    body = (
        "<h2>Country Profile</h2>"
        f"<p>Country: <strong>{html.escape(str(country_profile.get('country_id', 'UNKNOWN')))}</strong></p>"
        f"<p>Priority: <strong>{html.escape(str(country_context.get('priority', 'n/a')))}</strong> | Selection Type: <strong>{html.escape(str(country_context.get('selection_type', 'n/a')))}</strong> | Region: <strong>{html.escape(str(country_context.get('region', 'n/a')))}</strong></p>"
        f"<p>Multi-domain status: <span class='status'>{html.escape(str(country_profile.get('multi_domain_status', 'n/a')))}</span></p>"
        f"<p>Coverage: {html.escape(str(country_profile.get('coverage', 'n/a')))} | Confidence: {html.escape(str(country_profile.get('confidence', 'n/a')))}</p>"
        f"{trust_summary_html}"
        "<h3>Source Depth</h3>"
        f"<p>Source count: <strong>{html.escape(str(source_depth.get('source_count', 0)))}</strong></p>"
        f"<ul>{''.join(f'<li>{html.escape(item)}</li>' for item in source_ids) or '<li>none</li>'}</ul>"
        "<h3>Domain Gap Summary</h3>"
        f"<p>Expected domains: {html.escape(', '.join(str(item) for item in domain_gap_summary.get('expected_domains', [])) or 'none')}</p>"
        f"<p>Observed domains: {html.escape(', '.join(str(item) for item in domain_gap_summary.get('observed_domains', [])) or 'none')}</p>"
        f"<p>Missing domains: {html.escape(', '.join(missing_domains) or 'none')}</p>"
        f"<h4>Gap Cause Details</h4>{_render_gap_details(gap_details, coverage_href_prefix='../coverage.html')}"
        "<h3>Why this country is in this state</h3>"
        f"<p>{html.escape(str(explanation_summary))}</p>"
        "<h3>Domain States</h3>"
        f"<table><thead><tr><th>Domain</th><th>Status</th></tr></thead><tbody>{domain_rows}</tbody></table>"
        "<h3>Domain Deep Dives</h3>"
        f"<table><thead><tr><th>Domain</th><th>Target</th></tr></thead><tbody>{domain_link_rows}</tbody></table>"
        "<h3>Explanation Overview</h3>"
        f"<h4>Drivers</h4><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('drivers', []))}</ul>"
        f"<h4>Counter Indicators</h4><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('counter_indicators', []))}</ul>"
        f"<h4>Linked Events</h4><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('linked_events', []))}</ul>"
        f"<h4>Uncertainty</h4><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('uncertainty', []))}</ul>"
        f"<h3>Annotation IDs</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in annotation_ids)}</ul>"
        f"{annotation_workflow_link_html}"
        f"<h3>Analyst Annotations in Context</h3>{_annotation_details_html(annotation_ids, annotations_view_model)}"
        f"<h3>Trends</h3>{_json_block(country_profile.get('trends', {}))}"
    )
    return _page(f"Country Profile - {country_profile.get('country_id', 'UNKNOWN')}", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_domain_detail(domain_detail: dict[str, Any], annotations_view_model: dict[str, Any] | None = None, *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    annotation_ids = [str(item) for item in domain_detail.get('annotations', [])]
    if not annotation_ids and annotations_view_model is not None:
        linked_item_key = f"{domain_detail.get('country_id', 'UNKNOWN')}:{domain_detail.get('domain', 'UNKNOWN')}"
        annotation_ids = [
            str(item)
            for item in annotations_view_model.get('by_linked_item', {}).get(linked_item_key, [])
        ]
    time_series = domain_detail.get('time_series', [])
    domain_linked_item = f"{domain_detail.get('country_id', 'UNKNOWN')}:{domain_detail.get('domain', 'UNKNOWN')}"
    annotation_workflow_href = _annotation_workflow_href(
        nav_prefix=nav_prefix,
        scope='domain',
        linked_item=domain_linked_item,
        annotation_type='lineage_note',
    )
    annotation_workflow_link_html = (
        f"<p><a href='{html.escape(annotation_workflow_href)}'>Open Annotation Workflow for this Domain</a></p>"
        if annotations_view_model is not None and available_pages is not None and 'annotations.html' in available_pages
        else ''
    )
    body = (
        "<h2>Domain Detail</h2>"
        f"<p>Country: <strong>{html.escape(str(domain_detail.get('country_id', 'UNKNOWN')))}</strong></p>"
        f"<p>Domain: <strong>{html.escape(str(domain_detail.get('domain', 'UNKNOWN')))}</strong></p>"
        f"<p>Anomaly state: <span class='status'>{html.escape(str(domain_detail.get('anomaly_state', 'n/a')))}</span></p>"
        f"<h3>Time Series Chart</h3>{_render_line_chart(time_series, label_key='timestamp', chart_label='Domain time series') }"
        f"<h3>Time Series</h3>{_json_block(time_series)}"
        f"{_render_baseline_comparison_summary(domain_detail.get('baseline_comparison', {}), time_series)}"
        f"<h3>Raw Baseline Comparison Payload</h3>{_json_block(domain_detail.get('baseline_comparison', {}))}"
        f"<h3>Feature Values</h3>{_json_block(domain_detail.get('feature_values', []))}"
        f"<h3>Source Context</h3>{_json_block(domain_detail.get('source_context', []))}"
        f"<h3>Uncertainty</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in domain_detail.get('uncertainty', []))}</ul>"
        f"<h3>Annotation IDs</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in annotation_ids)}</ul>"
        f"{annotation_workflow_link_html}"
        f"<h3>Annotation Details</h3>{_annotation_details_html(annotation_ids, annotations_view_model)}"
    )
    return _page(
        f"Domain Detail - {domain_detail.get('country_id', 'UNKNOWN')} / {domain_detail.get('domain', 'UNKNOWN')}",
        body,
        nav_prefix=nav_prefix,
        available_pages=available_pages,
    )


def _render_source_coverage(
    source_coverage_read_model: dict[str, Any],
    system_status_read_model: dict[str, Any] | None = None,
    *,
    nav_prefix: str = '',
    available_pages: set[str] | None = None,
) -> str:
    rows = ''.join(
        "<tr>"
        f"<td id='{html.escape(_source_anchor_id(str(source.get('source_id', ''))))}'>{html.escape(str(source.get('source_id', '')))}</td>"
        f"<td>{html.escape(str(source.get('status', '')))}</td>"
        f"<td>{html.escape(str(source.get('history_horizon', '')))}</td>"
        f"<td>{html.escape(str(source.get('freshness_hours', '')))}</td>"
        f"<td>{html.escape(str(source.get('confidence', '')))}</td>"
        f"<td>{html.escape(str(source.get('record_count', '')))}</td>"
        f"<td>{html.escape(str(source.get('diagnostics', '')))}</td>"
        "</tr>"
        for source in source_coverage_read_model.get('sources', [])
    )
    matrix_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(source.get('source_id', '')))}</td>"
        f"<td>{html.escape(_ratio_band(source.get('confidence')))}</td>"
        f"<td>{_render_metric_meter('Confidence', source.get('confidence'), fill_color=_band_color(_ratio_band(source.get('confidence'))))}</td>"
        f"<td>{html.escape(str(source.get('freshness_hours', 'n/a')))}</td>"
        f"<td>{html.escape(str(source.get('status', '')))}</td>"
        "</tr>"
        for source in source_coverage_read_model.get('sources', [])
    ) or "<tr><td colspan='5'>No source metrics available.</td></tr>"
    system_status_read_model = system_status_read_model or {}
    coverage_visibility = _country_coverage_visibility_rows(system_status_read_model)
    trust_gaps = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in system_status_read_model.get('data_gaps', [])
    ) or "<li>none</li>"
    degraded_sources = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in source_coverage_read_model.get('degraded_sources', [])
    ) or "<li>none</li>"
    body = (
        "<h2>Source / Coverage View</h2>"
        "<h3>Trust Summary</h3>"
        f"<p>Run status: <span class='status'>{html.escape(str(system_status_read_model.get('run_status', 'n/a')))}</span></p>"
        f"<p>Status summary: {html.escape(str(source_coverage_read_model.get('source_status_summary', {})))}</p>"
        f"<h4>Data Gaps / Trust Limits</h4><ul>{trust_gaps}</ul>"
        f"<h4>Degraded Sources</h4><ul>{degraded_sources}</ul>"
        f"{_render_country_coverage_matrix(coverage_visibility)}"
        "<h3>Coverage / Confidence Matrix</h3>"
        "<p>Confidence Band highlights source trust at a glance while keeping freshness visible.</p>"
        "<table><thead><tr><th>Source</th><th>Confidence Band</th><th>Confidence Meter</th><th>Freshness (h)</th><th>Status</th></tr></thead>"
        f"<tbody>{matrix_rows}</tbody></table>"
        "<table><thead><tr><th>Source</th><th>Status</th><th>History Horizon</th><th>Freshness (h)</th><th>Confidence</th><th>Record Count</th><th>Diagnostics</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        f"<h3>Failed Sources</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in source_coverage_read_model.get('failed_sources', []))}</ul>"
        f"<h3>Missing Sources</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in source_coverage_read_model.get('missing_sources', []))}</ul>"
    )
    return _page("Source / Coverage View", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _prepare_report_catalog(report_catalog: dict[str, Any], output_dir: Path) -> tuple[dict[str, dict[str, Any]], list[Path]]:
    prepared_catalog: dict[str, dict[str, Any]] = {}
    copied_files: list[Path] = []
    for report_type, report_info in sorted(report_catalog.items()):
        prepared_info = dict(report_info)
        prepared_exports: list[dict[str, Any]] = []
        for export_file in report_info.get('export_files', []):
            relative_path = Path(str(export_file.get('relative_path', f"exports/{Path(str(export_file.get('path', 'export'))).name}")))
            source_path = Path(str(export_file.get('path', '')))
            destination_path = output_dir / relative_path
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if source_path.exists():
                shutil.copy2(source_path, destination_path)
                copied_files.append(destination_path)
            prepared_export = dict(export_file)
            prepared_export['href'] = relative_path.as_posix()
            prepared_exports.append(prepared_export)
        prepared_info['export_files'] = prepared_exports
        prepared_catalog[report_type] = prepared_info
    return prepared_catalog, copied_files


def _render_reports(report_catalog: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    def _render_export_links(report_info: dict[str, Any]) -> str:
        export_links = ''.join(
            (
                f"<div><a href=\"{html.escape(str(export_file.get('href', export_file.get('relative_path', ''))))}\">"
                f"{html.escape(str(export_file.get('label', export_file.get('format', 'download'))))}</a></div>"
            )
            for export_file in report_info.get('export_files', [])
        )
        return export_links or '-'

    rows = ''.join(
        "<tr>"
        f"<td>{html.escape(report_type)}</td>"
        f"<td>{html.escape(str(report_info.get('report_id', '')))}</td>"
        f"<td>{html.escape(str(report_info.get('format', '')))}</td>"
        f"<td>{_render_export_links(report_info)}</td>"
        f"<td>{html.escape(json.dumps({k: v for k, v in report_info.items() if k != 'export_files'}, sort_keys=True))}</td>"
        "</tr>"
        for report_type, report_info in sorted(report_catalog.items())
    )
    export_count = sum(len(report_info.get('export_files', [])) for report_info in report_catalog.values())
    evidence_items = ''.join(
        "<li>"
        f"{html.escape(str(report_info.get('report_id', report_type)))}"
        f" | snapshot={html.escape(str(report_info.get('snapshot_id', 'n/a')))}"
        f" | uncertainty={html.escape(', '.join(str(item) for item in report_info.get('uncertainty', [])) or 'none')}"
        f" | failed_sources={html.escape(', '.join(str(item) for item in report_info.get('failed_sources', [])) or 'none')}"
        "</li>"
        for report_type, report_info in sorted(report_catalog.items())
    ) or "<li>none</li>"
    body = (
        "<h2>Report / Export View</h2>"
        "<h3>Evidence Summary</h3>"
        f"<p>Reports available: <strong>{html.escape(str(len(report_catalog)))}</strong></p>"
        f"<p>Download-ready artifacts: <strong>{html.escape(str(export_count))}</strong></p>"
        f"<ul>{evidence_items}</ul>"
        "<table><thead><tr><th>Type</th><th>Report ID</th><th>Format</th><th>Downloads</th><th>Metadata</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )
    return _page("Report / Export View", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_runs(system_status_read_model: dict[str, Any], repo_closure_view_model: dict[str, Any] | None = None, *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    repo_closure_section = ""
    if repo_closure_view_model is not None:
        repo_closure_rows = ''.join(
            "<tr>"
            f"<td>{html.escape(str(slice_report.get('slice_id', '')))}</td>"
            f"<td>{html.escape(str(slice_report.get('summary', {}).get('closed', 'n/a')))}</td>"
            f"<td>{html.escape(str(slice_report.get('summary', {}).get('at_risk', 'n/a')))}</td>"
            "</tr>"
            for slice_report in repo_closure_view_model.get('slices', [])
        )
        summary = repo_closure_view_model.get('summary', {})
        repo_closure_section = (
            "<h3>Repo Closure Summary</h3>"
            f"<p>Slices: <strong>{html.escape(str(summary.get('slice_count', 'n/a')))}</strong></p>"
            f"<p>Requirements: <strong>{html.escape(str(summary.get('requirement_count', 'n/a')))}</strong></p>"
            f"<p>Closed: <strong>{html.escape(str(summary.get('closed', 'n/a')))}</strong> | At risk: <strong>{html.escape(str(summary.get('at_risk', 'n/a')))}</strong></p>"
            "<table><thead><tr><th>Slice</th><th>Closed</th><th>At Risk</th></tr></thead>"
            f"<tbody>{repo_closure_rows}</tbody></table>"
        )
    body = (
        "<h2>System Status / Runs</h2>"
        f"<p>Run ID: <strong>{html.escape(str(system_status_read_model.get('run_id', 'n/a')))}</strong></p>"
        f"<p>Run status: <span class='status'>{html.escape(str(system_status_read_model.get('run_status', 'n/a')))}</span></p>"
        f"<p>Last run: {html.escape(str(system_status_read_model.get('last_run', 'n/a')))}</p>"
        f"<p>Snapshot ID: {html.escape(str(system_status_read_model.get('snapshot_id', 'n/a')))}</p>"
        f"<p>Reprocessing status: {html.escape(str(system_status_read_model.get('reprocessing_status', 'n/a')))}</p>"
        f"<h3>Coverage</h3>{_json_block(system_status_read_model.get('coverage', {}))}"
        f"<h3>Failed Sources</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in system_status_read_model.get('failed_sources', []))}</ul>"
        f"<h3>Available Reports</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in system_status_read_model.get('available_reports', []))}</ul>"
        f"{repo_closure_section}"
    )
    return _page("System Status / Runs", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_readiness(readiness_view_model: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    def _artifact_status_text(check: dict[str, Any]) -> str:
        status = str(check.get('status', 'unknown'))
        reason = check.get('reason')
        return status if not reason else f"{status} ({reason})"

    demo_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(check.get('label', '')))}</td>"
        f"<td>{html.escape('ready' if bool(check.get('ready')) else 'missing')}</td>"
        "</tr>"
        for check in readiness_view_model.get('demo_checks', [])
    )
    evidence_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(check.get('label', '')))}</td>"
        f"<td>{html.escape('ready' if bool(check.get('ready')) else 'missing')}</td>"
        "</tr>"
        for check in readiness_view_model.get('evidence_checks', [])
    )
    artifact_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(check.get('artifact', '')))}</td>"
        f"<td>{html.escape(_artifact_status_text(check))}</td>"
        "</tr>"
        for check in readiness_view_model.get('artifact_checks', [])
    )
    known_gap_items = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in readiness_view_model.get('known_gaps', [])
    ) or "<li>none</li>"
    body = (
        "<h2>Demo / Release Readiness</h2>"
        f"<p>Run ID: <strong>{html.escape(str(readiness_view_model.get('run_id', 'n/a')))}</strong></p>"
        f"<p>Snapshot ID: <strong>{html.escape(str(readiness_view_model.get('snapshot_id', 'n/a')))}</strong></p>"
        f"<p>Demo Verdict: <strong>{html.escape(str(readiness_view_model.get('demo_verdict', 'n/a')))}</strong></p>"
        f"<p>Release Verdict: <strong>{html.escape(str(readiness_view_model.get('release_verdict', 'n/a')))}</strong></p>"
        f"<p>Country Profiles: <strong>{html.escape(str(readiness_view_model.get('country_profile_count', 0)))}</strong> | Domain Details: <strong>{html.escape(str(readiness_view_model.get('domain_detail_count', 0)))}</strong> | Reports: <strong>{html.escape(str(readiness_view_model.get('report_count', 0)))}</strong></p>"
        "<h3>Demo Flow Checklist</h3>"
        "<table><thead><tr><th>Flow Step</th><th>Status</th></tr></thead>"
        f"<tbody>{demo_rows}</tbody></table>"
        "<h3>Evidence Checklist</h3>"
        "<table><thead><tr><th>Evidence</th><th>Status</th></tr></thead>"
        f"<tbody>{evidence_rows}</tbody></table>"
        "<h3>Artifact Readiness Summary</h3>"
        "<table><thead><tr><th>Artifact</th><th>Status</th></tr></thead>"
        f"<tbody>{artifact_rows}</tbody></table>"
        "<h3>Known Gaps Before Release</h3>"
        f"<ul>{known_gap_items}</ul>"
    )
    return _page("Demo / Release Readiness", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_trends(country_profile_read_models: dict[str, dict[str, Any]], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    rows = []
    country_options = []
    trend_options = _trend_filter_options(country_profile_read_models)
    trend_option_tags = ''.join(
        f"<option value='{html.escape(label)}'>{html.escape(label)}</option>"
        for label in trend_options
    )
    for country_id, profile in sorted(country_profile_read_models.items()):
        yearly = profile.get('trends', {}).get('yearly', [])
        labels = ','.join(_trend_labels(yearly, label_key='label'))
        event_ids = [str(item) for item in profile.get('linked_events', [])]
        event_overlay = ''.join(f"<li>{html.escape(event_id)}</li>" for event_id in event_ids) or "<li>none</li>"
        rows.append(
            f"<tr class='trend-row' data-country-id='{html.escape(country_id)}' data-trend-labels='{html.escape(labels)}' data-event-ids='{html.escape(','.join(event_ids))}'>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td><div class='trend-chart-block'><h4>Trend Chart</h4>{_render_line_chart(yearly, label_key='label', chart_label=f'{country_id} yearly trend')}{_render_historical_comparison_summary(yearly, label_key='label')}</div><div class='trend-event-overlay' style='display:none'><h4>Event Overlay Summary</h4><ul>{event_overlay}</ul></div></td>"
            f"<td>{html.escape(str(profile.get('multi_domain_status', 'n/a')))}</td>"
            "</tr>"
        )
        country_options.append(f"<option value='{html.escape(country_id)}'>{html.escape(country_id)}</option>")
    body = (
        "<h2>Yearly Trend Page</h2>"
        "<h3>Trend Controls</h3>"
        "<label for='trend-country-filter'>Country Filter</label> "
        "<select id='trend-country-filter' name='trend-country-filter'><option value='all'>All countries</option>"
        f"{''.join(country_options)}</select> "
        "<label for='trend-time-window'>Time Window</label> "
        "<select id='trend-time-window' name='trend-time-window'><option value='all'>All labels</option>"
        f"{trend_option_tags}</select> "
        "<label for='trend-view-mode'>Trend View Mode</label> "
        "<select id='trend-view-mode' name='trend-view-mode'><option value='chart'>Chart view</option><option value='events'>Event overlay view</option></select>"
        "<p id='trend-filter-result'>Selected Trend Window: all labels</p>"
        "<table id='trend-table'><thead><tr><th>Country</th><th>Yearly Trend</th><th>Current Multi-Domain Status</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<script>"
        "function applyTrendViewMode(){"
        "const mode=document.getElementById('trend-view-mode').value;"
        "document.querySelectorAll('.trend-row').forEach((row)=>{"
        "const chart=row.querySelector('.trend-chart-block');"
        "const overlay=row.querySelector('.trend-event-overlay');"
        "if(chart){chart.style.display=mode==='events'?'none':'';}"
        "if(overlay){overlay.style.display=mode==='events'?'':'none';}"
        "});"
        "}"
        "function applyTrendFilters(){"
        "const country=document.getElementById('trend-country-filter').value;"
        "const windowValue=document.getElementById('trend-time-window').value;"
        "document.querySelectorAll('.trend-row').forEach((row)=>{"
        "const labels=(row.dataset.trendLabels||'').split(',').filter(Boolean);"
        "const matchesCountry=(country==='all'||row.dataset.countryId===country);"
        "const matchesWindow=(windowValue==='all'||labels.includes(windowValue));"
        "row.style.display=(matchesCountry&&matchesWindow)?'':'none';"
        "});"
        "applyTrendViewMode();"
        "document.getElementById('trend-filter-result').textContent='Selected Trend Window: '+windowValue;"
        "}"
        "document.getElementById('trend-country-filter').addEventListener('change', applyTrendFilters);"
        "document.getElementById('trend-time-window').addEventListener('change', applyTrendFilters);"
        "document.getElementById('trend-view-mode').addEventListener('change', applyTrendViewMode);"
        "applyTrendFilters();"
        "</script>"
    )
    return _page("Yearly Trend Page", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_events(country_profile_read_models: dict[str, dict[str, Any]], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    rows = []
    country_options = []
    for country_id, profile in sorted(country_profile_read_models.items()):
        country_options.append(f"<option value='{html.escape(country_id)}'>{html.escape(country_id)}</option>")
        for event_id in profile.get('linked_events', []):
            rows.append(
                f"<tr class='event-row' data-country-id='{html.escape(country_id)}' data-event-id='{html.escape(str(event_id))}'>"
                f"<td>{html.escape(country_id)}</td>"
                f"<td>{html.escape(str(event_id))}</td>"
                f"<td>{html.escape(str(profile.get('multi_domain_status', 'n/a')))}</td>"
                "</tr>"
            )
    body = (
        "<h2>Current Events Page</h2>"
        "<h3>Event Controls</h3>"
        "<label for='event-country-filter'>Country Filter</label> "
        "<select id='event-country-filter' name='event-country-filter'><option value='all'>All countries</option>"
        f"{''.join(country_options)}</select>"
        "<p id='event-filter-result'>Selected Event Country: all countries</p>"
        "<table id='event-table'><thead><tr><th>Country</th><th>Event</th><th>Context Status</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<script>"
        "function applyEventFilters(){"
        "const country=document.getElementById('event-country-filter').value;"
        "document.querySelectorAll('.event-row').forEach((row)=>{"
        "const show=(country==='all'||row.dataset.countryId===country);"
        "row.style.display=show?'':'none';"
        "});"
        "document.getElementById('event-filter-result').textContent='Selected Event Country: '+country;"
        "}"
        "document.getElementById('event-country-filter').addEventListener('change', applyEventFilters);"
        "applyEventFilters();"
        "</script>"
    )
    return _page("Current Events Page", body, nav_prefix=nav_prefix, available_pages=available_pages)



def _render_comparison(country_profile_read_models: dict[str, dict[str, Any]], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    rows = []
    for country_id, profile in sorted(country_profile_read_models.items()):
        domain_states = profile.get('domain_states', {})
        coverage_band = _ratio_band(profile.get('coverage'))
        confidence_band = _ratio_band(profile.get('confidence'))
        uncertainty_count = len(profile.get('uncertainty', []))
        rows.append(
            f"<tr class='comparison-row' data-country-id='{html.escape(country_id)}' data-coverage-band='{html.escape(coverage_band)}' data-confidence-band='{html.escape(confidence_band)}' data-uncertainty-count='{uncertainty_count}'>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td>{html.escape(str(profile.get('multi_domain_status', 'n/a')))}</td>"
            f"<td>{html.escape(', '.join(f'{domain}:{status}' for domain, status in sorted(domain_states.items())))}</td>"
            f"<td>{_render_metric_meter('Coverage', profile.get('coverage'), fill_color=_band_color(coverage_band))}</td>"
            f"<td>{_render_metric_meter('Confidence', profile.get('confidence'), fill_color=_band_color(confidence_band))}</td>"
            f"<td>{html.escape(', '.join(str(item) for item in profile.get('drivers', [])))}</td>"
            f"<td>{_render_uncertainty_badges(profile.get('uncertainty', []))}</td>"
            "</tr>"
        )
    body = (
        "<h2>Cross-Country Comparison</h2>"
        "<h3>Comparison controls</h3>"
        "<label for='comparison-filter'>Coverage / Uncertainty Focus</label> "
        "<select id='comparison-filter' name='comparison-filter'>"
        "<option value='all'>All countries</option>"
        "<option value='low_coverage'>Low coverage only</option>"
        "<option value='low_confidence'>Low confidence only</option>"
        "<option value='has_uncertainty'>With uncertainty flags</option>"
        "</select>"
        "<p id='comparison-filter-result'>Selected Comparison Filter: all countries</p>"
        "<h3>Coverage / Confidence Comparison</h3>"
        "<table><thead><tr><th>Country</th><th>Multi-Domain Status</th><th>Domain States</th><th>Coverage</th><th>Confidence</th><th>Drivers</th><th>Uncertainty</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<script>"
        "function applyComparisonFilters(){"
        "const mode=document.getElementById('comparison-filter').value;"
        "document.querySelectorAll('.comparison-row').forEach((row)=>{"
        "const lowCoverage=row.dataset.coverageBand==='low';"
        "const lowConfidence=row.dataset.confidenceBand==='low';"
        "const hasUncertainty=Number(row.dataset.uncertaintyCount||'0')>0;"
        "const show=(mode==='all'||(mode==='low_coverage'&&lowCoverage)||(mode==='low_confidence'&&lowConfidence)||(mode==='has_uncertainty'&&hasUncertainty));"
        "row.style.display=show?'':'none';"
        "});"
        "document.getElementById('comparison-filter-result').textContent='Selected Comparison Filter: '+mode;"
        "}"
        "document.getElementById('comparison-filter').addEventListener('change', applyComparisonFilters);"
        "applyComparisonFilters();"
        "</script>"
    )
    return _page("Cross-Country Comparison", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_validation(validation_view_model: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    time_range = validation_view_model.get('time_range', {})
    reprocessing = validation_view_model.get('reprocessing_comparison', {})
    expected_domains = [str(item) for item in validation_view_model.get('expected_domains', [])]
    observed_domains = [str(item) for item in validation_view_model.get('observed_domains', [])]
    missing_expected_domain_values = validation_view_model.get('missing_expected_domains')
    if missing_expected_domain_values is None:
        missing_expected_domain_values = [domain for domain in expected_domains if domain not in observed_domains]
    unexpected_observed_domain_values = validation_view_model.get('unexpected_observed_domains')
    if unexpected_observed_domain_values is None:
        unexpected_observed_domain_values = [domain for domain in observed_domains if domain not in expected_domains]
    review_verdict = validation_view_model.get('review_verdict')
    if review_verdict is None:
        status_match = validation_view_model.get('status_match')
        if status_match and not missing_expected_domain_values and not unexpected_observed_domain_values:
            review_verdict = 'match'
        elif status_match:
            review_verdict = 'match_with_gaps'
        else:
            review_verdict = 'mismatch'
    validation_cases = [item for item in validation_view_model.get('validation_cases', []) if isinstance(item, dict)]
    portfolio_summary = validation_view_model.get('portfolio_summary', {}) if isinstance(validation_view_model.get('portfolio_summary', {}), dict) else {}
    reference_case_library = [item for item in validation_view_model.get('reference_case_library', []) if isinstance(item, dict)]
    reference_case_library_summary = (
        validation_view_model.get('reference_case_library_summary', {})
        if isinstance(validation_view_model.get('reference_case_library_summary', {}), dict)
        else {}
    )
    historical_reference_reviews = [
        item for item in validation_view_model.get('historical_reference_reviews', []) if isinstance(item, dict)
    ]
    historical_reference_review_summary = (
        validation_view_model.get('historical_reference_review_summary', {})
        if isinstance(validation_view_model.get('historical_reference_review_summary', {}), dict)
        else {}
    )
    historical_replay_reviews = [
        item for item in validation_view_model.get('historical_replay_reviews', []) if isinstance(item, dict)
    ]
    historical_replay_summary = (
        validation_view_model.get('historical_replay_summary', {})
        if isinstance(validation_view_model.get('historical_replay_summary', {}), dict)
        else {}
    )
    if historical_replay_reviews and not historical_replay_summary.get('attention_cases'):
        historical_replay_summary = {
            **historical_replay_summary,
            **build_historical_replay_summary(historical_replay_reviews),
        }
    verdict_count_rows = ''.join(
        f"<tr><td>{html.escape(str(verdict))}</td><td>{html.escape(str(count))}</td></tr>"
        for verdict, count in sorted((portfolio_summary.get('review_verdict_counts') or {}).items())
    ) or "<tr><td colspan='2'>No portfolio verdict counts.</td></tr>"
    portfolio_case_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(case.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(case.get('case_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(case.get('review_verdict', 'n/a')))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in case.get('expected_domains', [])))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in case.get('observed_domains', [])))}</td>"
        "</tr>"
        for case in validation_cases
    ) or "<tr><td colspan='5'>No portfolio cases available.</td></tr>"
    reference_case_type_rows = ''.join(
        f"<tr><td>{html.escape(str(case_type))}</td><td>{html.escape(str(count))}</td></tr>"
        for case_type, count in sorted((reference_case_library_summary.get('case_type_counts') or {}).items())
    ) or "<tr><td colspan='2'>No case types recorded.</td></tr>"
    reference_case_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(case.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(case.get('case_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(case.get('case_type', 'n/a')))}</td>"
        f"<td>{html.escape(str(case.get('case_name', 'n/a')))}</td>"
        f"<td>{html.escape(str((case.get('time_range') or {}).get('start', 'n/a')))} to {html.escape(str((case.get('time_range') or {}).get('end', 'n/a')))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in case.get('expected_domains', [])))}</td>"
        "</tr>"
        for case in reference_case_library
    ) or "<tr><td colspan='6'>No curated reference cases recorded.</td></tr>"
    historical_reference_verdict_rows = ''.join(
        f"<tr><td>{html.escape(str(verdict))}</td><td>{html.escape(str(count))}</td></tr>"
        for verdict, count in sorted((historical_reference_review_summary.get('review_verdict_counts') or {}).items())
    ) or "<tr><td colspan='2'>No historical review verdicts recorded.</td></tr>"
    historical_reference_tier_rows = ''.join(
        f"<tr><td>{html.escape(str(tier))}</td><td>{html.escape(str(count))}</td></tr>"
        for tier, count in sorted((historical_reference_review_summary.get('evidence_tier_counts') or {}).items())
    ) or "<tr><td colspan='2'>No evidence tiers recorded.</td></tr>"
    historical_reference_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(review.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('case_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('review_verdict', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('evidence_tier', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('evidence_score', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('expected_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('historical_observed_status', 'n/a')))}</td>"
        "</tr>"
        for review in historical_reference_reviews
    ) or "<tr><td colspan='7'>No historical reference reviews recorded.</td></tr>"
    historical_replay_verdict_rows = ''.join(
        f"<tr><td>{html.escape(str(verdict))}</td><td>{html.escape(str(count))}</td></tr>"
        for verdict, count in sorted((historical_replay_summary.get('review_verdict_counts') or {}).items())
    ) or "<tr><td colspan='2'>No replay verdicts recorded.</td></tr>"
    historical_replay_basis_rows = ''.join(
        f"<tr><td>{html.escape(str(basis))}</td><td>{html.escape(str(count))}</td></tr>"
        for basis, count in sorted((historical_replay_summary.get('review_basis_counts') or {}).items())
    ) or "<tr><td colspan='2'>No replay bases recorded.</td></tr>"
    historical_replay_source_coverage_rows = ''.join(
        f"<tr><td>{html.escape(str(source_id))}</td><td>{html.escape(str(count))}</td></tr>"
        for source_id, count in sorted((historical_replay_summary.get('replay_input_source_coverage_counts') or {}).items())
    ) or "<tr><td colspan='2'>No replay source coverage recorded.</td></tr>"
    historical_replay_evidence_tier_rows = ''.join(
        f"<tr><td>{html.escape(str(tier))}</td><td>{html.escape(str(count))}</td></tr>"
        for tier, count in sorted((historical_replay_summary.get('replay_evidence_tier_counts') or {}).items())
    ) or "<tr><td colspan='2'>No replay evidence tiers recorded.</td></tr>"
    replay_attention_level_rows = ''.join(
        f"<tr><td>{html.escape(str(level))}</td><td>{html.escape(str(count))}</td></tr>"
        for level, count in sorted((historical_replay_summary.get('attention_level_counts') or {}).items())
    ) or "<tr><td colspan='2'>No attention levels recorded.</td></tr>"
    replay_attention_reason_rows = ''.join(
        f"<tr><td>{html.escape(str(reason))}</td><td>{html.escape(str(count))}</td></tr>"
        for reason, count in sorted((historical_replay_summary.get('attention_reason_counts') or {}).items())
    ) or "<tr><td colspan='2'>No attention reasons recorded.</td></tr>"
    replay_attention_owner_rows = ''.join(
        f"<tr><td>{html.escape(str(owner))}</td><td>{html.escape(str(count))}</td></tr>"
        for owner, count in sorted((historical_replay_summary.get('attention_owner_counts') or {}).items())
    ) or "<tr><td colspan='2'>No follow-up owners recorded.</td></tr>"
    replay_attention_country_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('attention_case_count', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('highest_attention_level', 'n/a')))}</td>"
        f"<td>{html.escape(', '.join(str(case_id) for case_id in item.get('case_ids', [])) or 'none')}</td>"
        "</tr>"
        for item in historical_replay_summary.get('attention_country_summary', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='4'>No country attention summary recorded.</td></tr>"
    replay_attention_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('case_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('attention_level', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('attention_reason', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('owner_hint', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('review_verdict', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('replay_evidence_tier', 'n/a')))}</td>"
        f"<td>{html.escape('missing=' + (', '.join(str(domain) for domain in item.get('missing_expected_domains', [])) or 'none') + '; unexpected=' + (', '.join(str(domain) for domain in item.get('unexpected_observed_domains', [])) or 'none'))}</td>"
        f"<td>{html.escape(str(item.get('suggested_next_action', 'n/a')))}</td>"
        "</tr>"
        for item in historical_replay_summary.get('attention_cases', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='9'>No replay attention cases recorded.</td></tr>"
    historical_replay_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(review.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('case_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('review_verdict', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('review_basis', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('replay_evidence_tier', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('replay_evidence_score', 'n/a')))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in review.get('replay_input_source_ids', [])))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in review.get('archival_data_files', [])))}</td>"
        f"<td>{html.escape(str(review.get('expected_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('replayed_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('domain_match_ratio', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('replay_input_record_count', 'n/a')))}</td>"
        "</tr>"
        for review in historical_replay_reviews
    ) or "<tr><td colspan='12'>No historical replay reviews recorded.</td></tr>"
    changed_versions = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in reprocessing.get('changed_versions', [])
    ) or "<li>none</li>"
    missing_expected_domains = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in missing_expected_domain_values
    ) or "<li>none</li>"
    unexpected_observed_domains = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in unexpected_observed_domain_values
    ) or "<li>none</li>"
    body = (
        "<h2>Validation / Backtest View</h2>"
        f"<p>Case ID: <strong>{html.escape(str(validation_view_model.get('case_id', 'n/a')))}</strong></p>"
        f"<p>Country: <strong>{html.escape(str(validation_view_model.get('country_id', 'n/a')))}</strong></p>"
        f"<p>Case: {html.escape(str(validation_view_model.get('case_name', 'n/a')))}</p>"
        f"<p>Time Range: {html.escape(str(time_range.get('start', 'n/a')))} to {html.escape(str(time_range.get('end', 'n/a')))}</p>"
        "<h3>Review Summary</h3>"
        f"<p>Review verdict: <strong>{html.escape(str(review_verdict))}</strong></p>"
        f"<p>Expected Domains: {html.escape(', '.join(expected_domains))}</p>"
        f"<p>Observed Domains: {html.escape(', '.join(observed_domains))}</p>"
        f"<p>Domain Match Ratio: {html.escape(str(validation_view_model.get('domain_match_ratio', 'n/a')))}</p>"
        f"<p>Status Match: {html.escape(str(validation_view_model.get('status_match', 'n/a')))}</p>"
        f"<h4>Missing Expected Domains</h4><ul>{missing_expected_domains}</ul>"
        f"<h4>Unexpected Observed Domains</h4><ul>{unexpected_observed_domains}</ul>"
        f"<h3>Expected Pattern</h3><p>{html.escape(str(validation_view_model.get('expected_pattern', 'n/a')))}</p>"
        f"<h3>Validation Goal</h3><p>{html.escape(str(validation_view_model.get('validation_goal', 'n/a')))}</p>"
        f"<h3>Reference Sources</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in validation_view_model.get('reference_sources', []))}</ul>"
        f"<h3>Validation Metrics</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in validation_view_model.get('validation_metrics', []))}</ul>"
        f"<h3>Known Limitations</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in validation_view_model.get('known_limitations', []))}</ul>"
        "<h3>Reference Case Portfolio Summary</h3>"
        f"<p>Validation Cases: <strong>{html.escape(str(portfolio_summary.get('case_count', len(validation_cases))))}</strong></p>"
        f"<p>Countries Covered: {html.escape(', '.join(str(item) for item in portfolio_summary.get('countries_covered', [])))}</p>"
        "<table><thead><tr><th>Review Verdict</th><th>Count</th></tr></thead>"
        f"<tbody>{verdict_count_rows}</tbody></table>"
        "<h3>Validation Case Portfolio</h3>"
        "<table><thead><tr><th>Country</th><th>Case ID</th><th>Review Verdict</th><th>Expected Domains</th><th>Observed Domains</th></tr></thead>"
        f"<tbody>{portfolio_case_rows}</tbody></table>"
        "<h3>Curated Reference Case Library</h3>"
        f"<p>Library Cases: <strong>{html.escape(str(reference_case_library_summary.get('case_count', len(reference_case_library))))}</strong></p>"
        f"<p>Countries Covered: {html.escape(', '.join(str(item) for item in reference_case_library_summary.get('countries_covered', [])))}</p>"
        f"<p>Library Time Range: {html.escape(str((reference_case_library_summary.get('time_range') or {}).get('start', 'n/a')))} to {html.escape(str((reference_case_library_summary.get('time_range') or {}).get('end', 'n/a')))}</p>"
        "<table><thead><tr><th>Case Type</th><th>Count</th></tr></thead>"
        f"<tbody>{reference_case_type_rows}</tbody></table>"
        "<table><thead><tr><th>Country</th><th>Case ID</th><th>Case Type</th><th>Case</th><th>Time Range</th><th>Expected Domains</th></tr></thead>"
        f"<tbody>{reference_case_rows}</tbody></table>"
        "<h3>Historical Reference Review Summary</h3>"
        f"<p>Average Evidence Score: <strong>{html.escape(str(historical_reference_review_summary.get('average_evidence_score', 'n/a')))}</strong></p>"
        "<table><thead><tr><th>Review Verdict</th><th>Count</th></tr></thead>"
        f"<tbody>{historical_reference_verdict_rows}</tbody></table>"
        "<table><thead><tr><th>Evidence Tier</th><th>Count</th></tr></thead>"
        f"<tbody>{historical_reference_tier_rows}</tbody></table>"
        "<h3>Historical Reference Reviews</h3>"
        "<table><thead><tr><th>Country</th><th>Case ID</th><th>Review Verdict</th><th>Evidence Tier</th><th>Evidence Score</th><th>Expected Status</th><th>Historical Observed Status</th></tr></thead>"
        f"<tbody>{historical_reference_rows}</tbody></table>"
        "<h3>Historical Replay Summary</h3>"
        f"<p>Average Domain Match Ratio: <strong>{html.escape(str(historical_replay_summary.get('average_domain_match_ratio', 'n/a')))}</strong></p>"
        f"<p>Status Match Count: <strong>{html.escape(str(historical_replay_summary.get('status_match_count', 'n/a')))}</strong></p>"
        f"<p>Average Replay Evidence Score: <strong>{html.escape(str(historical_replay_summary.get('average_replay_evidence_score', 'n/a')))}</strong></p>"
        f"<p>Average Replay Source Coverage Ratio: <strong>{html.escape(str(historical_replay_summary.get('average_replay_source_coverage_ratio', 'n/a')))}</strong></p>"
        f"<p>Average Replay Provenance Completeness Ratio: <strong>{html.escape(str(historical_replay_summary.get('average_replay_provenance_completeness_ratio', 'n/a')))}</strong></p>"
        f"<p>Replay Input Record Total: <strong>{html.escape(str(historical_replay_summary.get('replay_input_record_total', 'n/a')))}</strong></p>"
        f"<p>Archival Data Files: <strong>{html.escape(str(historical_replay_summary.get('archival_data_file_count', 'n/a')))}</strong></p>"
        "<table><thead><tr><th>Replay Verdict</th><th>Count</th></tr></thead>"
        f"<tbody>{historical_replay_verdict_rows}</tbody></table>"
        "<table><thead><tr><th>Replay Basis</th><th>Count</th></tr></thead>"
        f"<tbody>{historical_replay_basis_rows}</tbody></table>"
        "<h4>Replay Evidence Tiers</h4>"
        "<table><thead><tr><th>Evidence Tier</th><th>Count</th></tr></thead>"
        f"<tbody>{historical_replay_evidence_tier_rows}</tbody></table>"
        "<h4>Replay Source Coverage</h4>"
        "<table><thead><tr><th>Source</th><th>Case Count</th></tr></thead>"
        f"<tbody>{historical_replay_source_coverage_rows}</tbody></table>"
        "<h4>Replay Attention Summary</h4>"
        "<table><thead><tr><th>Attention Level</th><th>Count</th></tr></thead>"
        f"<tbody>{replay_attention_level_rows}</tbody></table>"
        "<table><thead><tr><th>Reason</th><th>Count</th></tr></thead>"
        f"<tbody>{replay_attention_reason_rows}</tbody></table>"
        "<table><thead><tr><th>Follow-up Owner</th><th>Count</th></tr></thead>"
        f"<tbody>{replay_attention_owner_rows}</tbody></table>"
        "<h5>Attention by Country</h5>"
        "<table><thead><tr><th>Country</th><th>Attention Cases</th><th>Highest Attention Level</th><th>Case IDs</th></tr></thead>"
        f"<tbody>{replay_attention_country_rows}</tbody></table>"
        "<h4>Replay Attention Watchlist</h4>"
        f"<p>Attention Cases: <strong>{html.escape(str(historical_replay_summary.get('attention_case_count', 0)))}</strong></p>"
        "<table><thead><tr><th>Country</th><th>Case ID</th><th>Attention Level</th><th>Reason</th><th>Follow-up Owner</th><th>Replay Verdict</th><th>Replay Evidence Tier</th><th>Gap Signals</th><th>Suggested Next Action</th></tr></thead>"
        f"<tbody>{replay_attention_rows}</tbody></table>"
        "<h3>Historical Replay Reviews</h3>"
        "<table><thead><tr><th>Country</th><th>Case ID</th><th>Replay Verdict</th><th>Replay Basis</th><th>Replay Evidence Tier</th><th>Replay Evidence Score</th><th>Replay Sources</th><th>Archival Data Files</th><th>Expected Status</th><th>Replayed Status</th><th>Domain Match Ratio</th><th>Replay Input Records</th></tr></thead>"
        f"<tbody>{historical_replay_rows}</tbody></table>"
        "<h3>Changed Versions</h3>"
        f"<ul>{changed_versions}</ul>"
        f"<h3>Reprocessing Comparison</h3>{_json_block(reprocessing)}"
    )
    return _page("Validation / Backtest View", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _traceability_dependency_rows(lineage_records: list[dict[str, Any]]) -> str:
    clusters: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in lineage_records:
        feature_id = str(record.get('feature_id', ''))
        domain_status_id = str(record.get('domain_status_id', ''))
        snapshot_id = str(record.get('snapshot_id', ''))
        cluster_key = (feature_id, domain_status_id, snapshot_id)
        entry = clusters.setdefault(
            cluster_key,
            {
                'feature_id': feature_id,
                'domain_status_id': domain_status_id,
                'snapshot_id': snapshot_id,
                'source_ids': set(),
                'report_ids': set(),
            },
        )
        entry['source_ids'].add(str(record.get('source_id', '')))
        if record.get('report_id'):
            entry['report_ids'].add(str(record.get('report_id')))
    rows = []
    for cluster in clusters.values():
        source_ids = sorted(source_id for source_id in cluster['source_ids'] if source_id)
        if len(source_ids) < 2:
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(cluster['feature_id'])}</td>"
            f"<td>{html.escape(cluster['domain_status_id'])}</td>"
            f"<td>{html.escape(cluster['snapshot_id'])}</td>"
            f"<td>{html.escape(', '.join(source_ids))}</td>"
            f"<td>{html.escape(', '.join(sorted(cluster['report_ids'])) or 'n/a')}</td>"
            f"<td>{html.escape('replication_or_shared_dependency_candidate')}</td>"
            "</tr>"
        )
    return ''.join(rows) or "<tr><td colspan='6'>No dependency cluster candidates in current lineage artifact.</td></tr>"



def _traceability_origin_rows(lineage_records: list[dict[str, Any]]) -> str:
    by_source: dict[str, dict[str, Any]] = {}
    for record in lineage_records:
        source_id = str(record.get('source_id', ''))
        entry = by_source.setdefault(
            source_id,
            {
                'raw_record_ids': set(),
                'feature_ids': set(),
                'report_ids': set(),
            },
        )
        entry['raw_record_ids'].add(str(record.get('raw_record_id', '')))
        entry['feature_ids'].add(str(record.get('feature_id', '')))
        if record.get('report_id'):
            entry['report_ids'].add(str(record.get('report_id')))
    rows = []
    for source_id, entry in sorted(by_source.items()):
        rows.append(
            "<tr>"
            f"<td>{html.escape(source_id)}</td>"
            f"<td>{len([item for item in entry['raw_record_ids'] if item])}</td>"
            f"<td>{len([item for item in entry['feature_ids'] if item])}</td>"
            f"<td>{html.escape(', '.join(sorted(item for item in entry['report_ids'] if item)) or 'n/a')}</td>"
            f"<td>{html.escape('not yet inferable from current lineage artifact')}</td>"
            f"<td>{html.escape('current artifact lacks earliest-seen / propagation timestamps needed for origin inference')}</td>"
            "</tr>"
        )
    return ''.join(rows) or "<tr><td colspan='6'>No source-origin groundwork available.</td></tr>"



def _render_traceability(traceability_view_model: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    lineage_records = [record for record in traceability_view_model.get('lineage_records', []) if isinstance(record, dict)]
    rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(record.get('source_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('raw_record_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('normalized_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('feature_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('domain_status_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('multi_domain_status_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('snapshot_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('report_id', '')))}</td>"
        "</tr>"
        for record in lineage_records
    )
    dependency_rows = _traceability_dependency_rows(lineage_records)
    origin_rows = _traceability_origin_rows(lineage_records)
    body = (
        "<h2>Traceability / Lineage View</h2>"
        "<table><thead><tr><th>Source</th><th>Raw</th><th>Normalized</th><th>Feature</th><th>Domain Status</th><th>Multi-Domain Status</th><th>Snapshot</th><th>Report</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        "<h3>Source Dependency Groundwork</h3>"
        "<h4>Dependency Cluster Candidates</h4>"
        "<table><thead><tr><th>Feature</th><th>Domain Status</th><th>Snapshot</th><th>Sources</th><th>Reports</th><th>Coupling Signal</th></tr></thead>"
        f"<tbody>{dependency_rows}</tbody></table>"
        "<h3>Source-Origin Groundwork</h3>"
        "<p>This slice surfaces what the current lineage artifact can already support while explicitly marking origin inference as unresolved where no first-seen / propagation timestamps exist.</p>"
        "<table><thead><tr><th>Source</th><th>Raw Records</th><th>Features</th><th>Reports</th><th>Origin Inference Status</th><th>Origin Uncertainty</th></tr></thead>"
        f"<tbody>{origin_rows}</tbody></table>"
    )
    return _page("Traceability / Lineage View", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_annotations(annotations_view_model: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    scope_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(scope))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in annotation_ids))}</td>"
        "</tr>"
        for scope, annotation_ids in sorted(annotations_view_model.get('by_scope', {}).items())
    )
    linked_item_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(linked_item))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in annotation_ids))}</td>"
        "</tr>"
        for linked_item, annotation_ids in sorted(annotations_view_model.get('by_linked_item', {}).items())
    )
    workflow_seed = _annotation_workflow_seed(annotations_view_model)
    workflow_script = """
<script>
const annotationSeed = JSON.parse((document.getElementById('annotation-seed-data')?.textContent || '{}'));
const annotationStoreKey = 'siasa_annotation_workflow_v1';
const annotationHistoryStoreKey = 'siasa_annotation_workflow_history_v1';
function readStoredAnnotations(){ try { return JSON.parse(window.localStorage.getItem(annotationStoreKey) || '[]'); } catch (error) { return []; } }
function writeStoredAnnotations(items){ window.localStorage.setItem(annotationStoreKey, JSON.stringify(items)); }
function readStoredHistory(){ try { return JSON.parse(window.localStorage.getItem(annotationHistoryStoreKey) || '[]'); } catch (error) { return []; } }
function writeStoredHistory(items){ window.localStorage.setItem(annotationHistoryStoreKey, JSON.stringify(items)); }
function annotationLinkedItems(annotation){ return Array.isArray(annotation.linked_items) ? annotation.linked_items : []; }
function annotationDraftSource(annotation){ return String(annotation._draft_source || 'artifact'); }
function escapeAnnotationHtml(value){
  return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function mergedAnnotationsById(){
  const artifactItems = Array.isArray(annotationSeed.annotations) ? annotationSeed.annotations : [];
  const draftItems = readStoredAnnotations();
  const merged = new Map(artifactItems.map((item) => [String(item.annotation_id), item]));
  draftItems.forEach((item) => merged.set(String(item.annotation_id), item));
  return merged;
}
function currentEditorAnnotation(){
  return {
    annotation_id: (document.getElementById('annotation-id-input').value || '').trim(),
    created_at: (document.getElementById('annotation-created-at-input').value || '').trim(),
    author: (document.getElementById('annotation-author-input').value || '').trim(),
    scope: document.getElementById('annotation-scope-input').value,
    annotation_type: document.getElementById('annotation-type-input').value,
    severity_assessment: document.getElementById('annotation-severity-input').value,
    confidence_assessment: document.getElementById('annotation-confidence-input').value,
    text: (document.getElementById('annotation-text-input').value || '').trim(),
    tags: (document.getElementById('annotation-tags-input').value || '').split(',').map((item) => item.trim()).filter(Boolean),
    linked_items: (document.getElementById('annotation-linked-items-input').value || '').split(',').map((item) => item.trim()).filter(Boolean),
    review_status: document.getElementById('annotation-review-status-input').value,
    _draft_source: 'local_draft',
  };
}
function generatedDraftId(){ return `ANN-DRAFT-${Date.now()}`; }
function setWorkflowStatus(message){ document.getElementById('annotation-workflow-status').textContent = message; }
function loadAnnotationIntoEditor(annotationId){
  const all = Array.from(mergedAnnotationsById().values());
  const selected = all.find((item) => String(item.annotation_id) === String(annotationId));
  if (!selected) { return; }
  document.getElementById('annotation-id-input').value = selected.annotation_id || '';
  document.getElementById('annotation-created-at-input').value = selected.created_at || '';
  document.getElementById('annotation-author-input').value = selected.author || '';
  document.getElementById('annotation-scope-input').value = selected.scope || 'country';
  document.getElementById('annotation-type-input').value = selected.annotation_type || 'context_note';
  document.getElementById('annotation-severity-input').value = selected.severity_assessment || 'uncertain';
  document.getElementById('annotation-confidence-input').value = selected.confidence_assessment || 'medium';
  document.getElementById('annotation-review-status-input').value = selected.review_status || 'draft';
  document.getElementById('annotation-linked-items-input').value = annotationLinkedItems(selected).join(', ');
  document.getElementById('annotation-tags-input').value = (Array.isArray(selected.tags) ? selected.tags : []).join(', ');
  document.getElementById('annotation-text-input').value = selected.text || '';
  setWorkflowStatus(`Loaded annotation ${selected.annotation_id} into editor.`);
}
function prefillAnnotationFromQuery(){
  const params = new URLSearchParams(window.location.search);
  const linkedItem = params.get('linked_item') || '';
  const scope = params.get('scope') || '';
  const annotationType = params.get('annotation_type') || '';
  if (scope) { document.getElementById('annotation-scope-input').value = scope; }
  if (annotationType) { document.getElementById('annotation-type-input').value = annotationType; }
  if (linkedItem) {
    document.getElementById('annotation-linked-items-input').value = linkedItem;
    setWorkflowStatus(`Prefilled workflow for ${linkedItem}.`);
  }
}
function renderAnnotationWorkflow(){
  const merged = Array.from(mergedAnnotationsById().values());
  const scopeFilter = document.getElementById('annotation-scope-filter').value;
  const reviewFilter = document.getElementById('annotation-review-filter').value;
  const linkedItemNeedle = (document.getElementById('annotation-linked-item-filter').value || '').trim().toLowerCase();
  const filtered = merged.filter((annotation) => {
    const scopeOk = scopeFilter === 'all' || String(annotation.scope || '') === scopeFilter;
    const reviewOk = reviewFilter === 'all' || String(annotation.review_status || '') === reviewFilter;
    const linkedItems = annotationLinkedItems(annotation).join(', ').toLowerCase();
    const linkedOk = !linkedItemNeedle || linkedItems.includes(linkedItemNeedle) || String(annotation.annotation_id || '').toLowerCase().includes(linkedItemNeedle);
    return scopeOk && reviewOk && linkedOk;
  });
  document.getElementById('annotation-workflow-table-body').innerHTML = filtered.map((annotation) => `
    <tr>
      <td>${escapeAnnotationHtml(annotation.annotation_id || '')}</td>
      <td>${escapeAnnotationHtml(annotation.scope || '')}</td>
      <td>${escapeAnnotationHtml(annotation.annotation_type || '')}</td>
      <td>${escapeAnnotationHtml(annotation.review_status || '')}</td>
      <td>${escapeAnnotationHtml(annotation.author || '')}</td>
      <td>${escapeAnnotationHtml(annotationLinkedItems(annotation).join(', '))}</td>
      <td>${escapeAnnotationHtml(annotationDraftSource(annotation))}</td>
      <td><button type="button" class="annotation-edit-button" data-annotation-id="${escapeAnnotationHtml(annotation.annotation_id || '')}">Edit</button></td>
    </tr>`).join('') || '<tr><td colspan="8">No annotations match the current filters.</td></tr>';
  document.querySelectorAll('.annotation-edit-button').forEach((button) => button.addEventListener('click', () => loadAnnotationIntoEditor(button.getAttribute('data-annotation-id') || '')));
  const history = readStoredHistory();
  document.getElementById('annotation-history-table-body').innerHTML = history.map((entry) => `
    <tr>
      <td>${escapeAnnotationHtml(entry.saved_at || '')}</td>
      <td>${escapeAnnotationHtml(entry.annotation_id || '')}</td>
      <td>${escapeAnnotationHtml(entry.action || '')}</td>
      <td>${escapeAnnotationHtml((entry.linked_items || []).join(', '))}</td>
    </tr>`).join('') || '<tr><td colspan="4">No draft history recorded.</td></tr>';
  document.getElementById('annotation-draft-export').textContent = JSON.stringify(readStoredAnnotations(), null, 2);
}
document.getElementById('annotation-editor-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const annotation = currentEditorAnnotation();
  if (!annotation.annotation_id) { annotation.annotation_id = generatedDraftId(); }
  if (!annotation.created_at) { annotation.created_at = new Date().toISOString(); }
  if (!annotation.author) { annotation.author = 'analyst'; }
  const drafts = readStoredAnnotations();
  const existingIndex = drafts.findIndex((item) => String(item.annotation_id) === String(annotation.annotation_id));
  const action = existingIndex >= 0 ? 'updated' : 'created';
  if (existingIndex >= 0) { drafts[existingIndex] = annotation; } else { drafts.push(annotation); }
  writeStoredAnnotations(drafts);
  const history = readStoredHistory();
  history.unshift({ saved_at: new Date().toISOString(), annotation_id: annotation.annotation_id, action: action, linked_items: annotation.linked_items });
  writeStoredHistory(history.slice(0, 25));
  document.getElementById('annotation-id-input').value = annotation.annotation_id;
  document.getElementById('annotation-created-at-input').value = annotation.created_at;
  setWorkflowStatus(`Draft annotation ${annotation.annotation_id} ${action}.`);
  renderAnnotationWorkflow();
});
document.getElementById('annotation-reset-editor').addEventListener('click', () => {
  document.getElementById('annotation-editor-form').reset();
  document.getElementById('annotation-id-input').value = '';
  document.getElementById('annotation-created-at-input').value = '';
  prefillAnnotationFromQuery();
  setWorkflowStatus('Annotation editor reset.');
});
document.getElementById('annotation-export-drafts').addEventListener('click', () => {
  const exportText = JSON.stringify(readStoredAnnotations(), null, 2);
  document.getElementById('annotation-draft-export').textContent = exportText;
  const blob = new Blob([exportText], { type: 'application/json' });
  const exportLink = document.createElement('a');
  exportLink.href = URL.createObjectURL(blob);
  exportLink.download = 'annotation_drafts.json';
  exportLink.click();
  URL.revokeObjectURL(exportLink.href);
  setWorkflowStatus('Draft annotations exported as JSON.');
});
document.getElementById('annotation-scope-filter').addEventListener('change', renderAnnotationWorkflow);
document.getElementById('annotation-review-filter').addEventListener('change', renderAnnotationWorkflow);
document.getElementById('annotation-linked-item-filter').addEventListener('input', renderAnnotationWorkflow);
prefillAnnotationFromQuery();
renderAnnotationWorkflow();
</script>
"""
    body = ''.join(
        [
            "<h2>Analyst Annotations View</h2>",
            f"<p>Total annotations: <strong>{html.escape(str(len(annotations_view_model.get('annotations', []))))}</strong></p>",
            "<h3>Create / Edit Annotation Workflow</h3>",
            "<p>This static GUI keeps analyst draft annotations in the browser for create/edit/filter/history workflow support. Export the draft JSON for governed persistence into repo-backed artifacts.</p>",
            "<div id='annotation-workflow-status'></div>",
            "<h4>Workflow Filters</h4>",
            "<label for='annotation-scope-filter'>Scope Filter</label> ",
            "<select id='annotation-scope-filter'><option value='all'>All scopes</option><option value='country'>country</option><option value='domain'>domain</option><option value='signal'>signal</option><option value='event'>event</option><option value='snapshot'>snapshot</option></select> ",
            "<label for='annotation-review-filter'>Review Filter</label> ",
            "<select id='annotation-review-filter'><option value='all'>All review states</option><option value='unreviewed'>unreviewed</option><option value='draft'>draft</option><option value='reviewed'>reviewed</option><option value='accepted'>accepted</option><option value='rejected'>rejected</option></select> ",
            "<label for='annotation-linked-item-filter'>Linked Item Filter</label> ",
            "<input id='annotation-linked-item-filter' type='text' placeholder='UKR / UKR:A / SNAP-...' />",
            "<h4>Annotation Registry</h4>",
            "<table id='annotation-workflow-table'><thead><tr><th>ID</th><th>Scope</th><th>Type</th><th>Review</th><th>Author</th><th>Linked Items</th><th>Draft Source</th><th>Action</th></tr></thead><tbody id='annotation-workflow-table-body'></tbody></table>",
            "<h4>Draft Editor</h4>",
            "<form id='annotation-editor-form'>",
            "<p><label for='annotation-id-input'>Annotation ID</label><br><input id='annotation-id-input' type='text' placeholder='ANN-DRAFT-...' /></p>",
            "<p><label for='annotation-created-at-input'>Created At</label><br><input id='annotation-created-at-input' type='text' placeholder='2026-05-16T06:45:00Z' /></p>",
            "<p><label for='annotation-author-input'>Author</label><br><input id='annotation-author-input' type='text' placeholder='analyst' /></p>",
            "<p><label for='annotation-scope-input'>Scope</label><br><select id='annotation-scope-input'><option value='country'>country</option><option value='domain'>domain</option><option value='signal'>signal</option><option value='event'>event</option><option value='snapshot'>snapshot</option></select></p>",
            "<p><label for='annotation-type-input'>Annotation Type</label><br><select id='annotation-type-input'><option value='context_note'>context_note</option><option value='false_positive_note'>false_positive_note</option><option value='source_quality_note'>source_quality_note</option><option value='lineage_note'>lineage_note</option><option value='review_note'>review_note</option></select></p>",
            "<p><label for='annotation-severity-input'>Severity Assessment</label><br><select id='annotation-severity-input'><option value='not_security_relevant'>not_security_relevant</option><option value='relevant'>relevant</option><option value='uncertain'>uncertain</option></select></p>",
            "<p><label for='annotation-confidence-input'>Confidence Assessment</label><br><select id='annotation-confidence-input'><option value='low'>low</option><option value='medium'>medium</option><option value='high'>high</option></select></p>",
            "<p><label for='annotation-review-status-input'>Review Status</label><br><select id='annotation-review-status-input'><option value='unreviewed'>unreviewed</option><option value='draft'>draft</option><option value='reviewed'>reviewed</option><option value='accepted'>accepted</option><option value='rejected'>rejected</option></select></p>",
            "<p><label for='annotation-linked-items-input'>Linked Items (comma separated)</label><br><input id='annotation-linked-items-input' type='text' placeholder='UKR, UKR:A, SNAP-RUN-...' /></p>",
            "<p><label for='annotation-tags-input'>Tags (comma separated)</label><br><input id='annotation-tags-input' type='text' placeholder='source_dependency, review' /></p>",
            "<p><label for='annotation-text-input'>Annotation Text</label><br><textarea id='annotation-text-input' rows='6' cols='80' placeholder='Analyst note...'></textarea></p>",
            "<p><button id='annotation-save-draft' type='submit'>Save Draft Annotation</button> <button id='annotation-reset-editor' type='button'>Reset Editor</button> <button id='annotation-export-drafts' type='button'>Export Draft Annotations</button></p>",
            "</form>",
            "<h4>Draft Export</h4><pre id='annotation-draft-export'>[]</pre>",
            "<h4>Draft History</h4>",
            "<table id='annotation-history-table'><thead><tr><th>Saved At</th><th>Annotation ID</th><th>Action</th><th>Linked Items</th></tr></thead><tbody id='annotation-history-table-body'></tbody></table>",
            f"<h3>Annotation Details</h3>{_annotation_details_html([str(item.get('annotation_id')) for item in annotations_view_model.get('annotations', [])], annotations_view_model)}",
            "<h3>By Scope</h3>",
            "<table><thead><tr><th>Scope</th><th>Annotation IDs</th></tr></thead>",
            f"<tbody>{scope_rows}</tbody></table>",
            "<h3>By Linked Item</h3>",
            "<table><thead><tr><th>Linked Item</th><th>Annotation IDs</th></tr></thead>",
            f"<tbody>{linked_item_rows}</tbody></table>",
            f"<script id='annotation-seed-data' type='application/json'>{workflow_seed}</script>",
            workflow_script,
        ]
    )
    return _page("Analyst Annotations View", body, nav_prefix=nav_prefix, available_pages=available_pages)


def build_local_mvp_site(
    output_dir: Path,
    world_map_read_model: dict[str, Any],
    country_profile_read_models: dict[str, dict[str, Any]],
    domain_detail_read_models: dict[tuple[str, str], dict[str, Any]],
    source_coverage_read_model: dict[str, Any],
    report_catalog: dict[str, dict[str, Any]],
    system_status_read_model: dict[str, Any],
    validation_view_model: dict[str, Any] | None = None,
    traceability_view_model: dict[str, Any] | None = None,
    repo_closure_view_model: dict[str, Any] | None = None,
    annotations_view_model: dict[str, Any] | None = None,
    readiness_view_model: dict[str, Any] | None = None,
) -> SiteBuildResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    countries_dir = output_dir / 'countries'
    domains_dir = output_dir / 'domains'
    countries_dir.mkdir(exist_ok=True)
    domains_dir.mkdir(exist_ok=True)

    generated_files: list[Path] = []
    available_pages = {
        'index.html',
        'coverage.html',
        'reports.html',
        'runs.html',
        'trends.html',
        'events.html',
        'comparison.html',
        'readiness.html',
    }
    if validation_view_model is not None:
        available_pages.add('validation.html')
    if traceability_view_model is not None:
        available_pages.add('traceability.html')
    if annotations_view_model is not None:
        available_pages.add('annotations.html')

    index_file = output_dir / 'index.html'
    index_file.write_text(
        _render_index(
            world_map_read_model,
            available_country_ids=set(country_profile_read_models),
            country_profile_read_models=country_profile_read_models,
            system_status_read_model=system_status_read_model,
            nav_prefix='',
            available_pages=available_pages,
        )
    )
    generated_files.append(index_file)

    available_domain_targets_by_country: dict[str, dict[str, str]] = {}
    for (country_id, domain) in domain_detail_read_models:
        available_domain_targets_by_country.setdefault(country_id, {})[domain] = f"../domains/{country_id}-{domain}.html"

    for country_id, read_model in country_profile_read_models.items():
        country_file = countries_dir / f'{country_id}.html'
        country_file.write_text(
            _render_country(
                read_model,
                annotations_view_model,
                available_domain_targets=available_domain_targets_by_country.get(country_id, {}),
                nav_prefix='../',
                available_pages=available_pages,
            )
        )
        generated_files.append(country_file)

    for (country_id, domain), read_model in domain_detail_read_models.items():
        domain_file = domains_dir / f'{country_id}-{domain}.html'
        domain_file.write_text(
            _render_domain_detail(
                read_model,
                annotations_view_model,
                nav_prefix='../',
                available_pages=available_pages,
            )
        )
        generated_files.append(domain_file)

    coverage_file = output_dir / 'coverage.html'
    coverage_file.write_text(
        _render_source_coverage(
            source_coverage_read_model,
            system_status_read_model=system_status_read_model,
            nav_prefix='',
            available_pages=available_pages,
        )
    )
    generated_files.append(coverage_file)

    prepared_report_catalog, copied_export_files = _prepare_report_catalog(report_catalog, output_dir)
    generated_files.extend(copied_export_files)
    reports_file = output_dir / 'reports.html'
    reports_file.write_text(_render_reports(prepared_report_catalog, nav_prefix='', available_pages=available_pages))
    generated_files.append(reports_file)

    runs_file = output_dir / 'runs.html'
    runs_file.write_text(_render_runs(system_status_read_model, repo_closure_view_model, nav_prefix='', available_pages=available_pages))
    generated_files.append(runs_file)

    trends_file = output_dir / 'trends.html'
    trends_file.write_text(_render_trends(country_profile_read_models, nav_prefix='', available_pages=available_pages))
    generated_files.append(trends_file)

    events_file = output_dir / 'events.html'
    events_file.write_text(_render_events(country_profile_read_models, nav_prefix='', available_pages=available_pages))
    generated_files.append(events_file)

    comparison_file = output_dir / 'comparison.html'
    comparison_file.write_text(_render_comparison(country_profile_read_models, nav_prefix='', available_pages=available_pages))
    generated_files.append(comparison_file)

    if validation_view_model is not None:
        validation_file = output_dir / 'validation.html'
        validation_file.write_text(_render_validation(validation_view_model, nav_prefix='', available_pages=available_pages))
        generated_files.append(validation_file)

    if traceability_view_model is not None:
        traceability_file = output_dir / 'traceability.html'
        traceability_file.write_text(_render_traceability(traceability_view_model, nav_prefix='', available_pages=available_pages))
        generated_files.append(traceability_file)

    if annotations_view_model is not None:
        annotations_file = output_dir / 'annotations.html'
        annotations_file.write_text(_render_annotations(annotations_view_model, nav_prefix='', available_pages=available_pages))
        generated_files.append(annotations_file)

    if readiness_view_model is None:
        readiness_view_model = build_readiness_view_model(
            country_profile_read_models=country_profile_read_models,
            domain_detail_read_models=domain_detail_read_models,
            report_catalog=prepared_report_catalog,
            system_status_read_model=system_status_read_model,
            source_coverage_read_model=source_coverage_read_model,
            validation_view_model=validation_view_model,
            traceability_view_model=traceability_view_model,
            annotations_view_model=annotations_view_model,
            repo_closure_view_model=repo_closure_view_model,
            available_pages=available_pages,
        )
    readiness_file = output_dir / 'readiness.html'
    readiness_file.write_text(_render_readiness(readiness_view_model, nav_prefix='', available_pages=available_pages))
    generated_files.append(readiness_file)
    readiness_json_file = output_dir / 'readiness.json'
    readiness_json_file.write_text(json.dumps(readiness_view_model, indent=2, sort_keys=True))
    generated_files.append(readiness_json_file)

    return SiteBuildResult(output_dir=output_dir, generated_files=generated_files)


def _demo_payload() -> dict[str, Any]:
    return {
        'world_map_read_model': {
            'baseline_mode': 'Combined 30/90/365',
            'active_domains': ['A', 'B', 'D'],
            'countries': [
                {'country_id': 'UKR', 'status': 'S3', 'active_domains': ['A', 'B', 'D'], 'drill_down_target': '/countries/UKR'},
                {'country_id': 'POL', 'status': 'S1', 'active_domains': ['A', 'D'], 'drill_down_target': '/countries/POL'},
            ],
        },
        'country_profile_read_models': {
            'UKR': {
                'country_id': 'UKR',
                'multi_domain_status': 'S3',
                'domain_states': {'A': 'D3', 'B': 'D2', 'D': 'D1'},
                'trends': {'yearly': ['2025-11', '2025-12', '2026-01']},
                'drivers': ['A_news_volume'],
                'linked_events': ['EVT-001'],
                'coverage': 0.84,
                'confidence': 0.73,
                'counter_indicators': ['D_macro_stability'],
                'uncertainty': ['partial_success'],
                'annotations': ['ANN-001'],
            }
        },
        'domain_detail_read_models': {
            ('UKR', 'A'): {
                'country_id': 'UKR',
                'domain': 'A',
                'time_series': [{'timestamp': '2026-05-11', 'value': 0.67}],
                'baseline_comparison': {'current_window': 0.67, 'baseline_30d': 0.31, 'delta_to_baseline': 0.36},
                'feature_values': [{'feature_id': 'A_article_count', 'value': 12.0, 'coverage': 0.9}],
                'source_context': [{'source_id': 'SRC-A', 'freshness_hours': 6, 'history_horizon': '3y', 'status': 'success'}],
                'anomaly_state': 'D3',
                'uncertainty': ['source_bias_possible'],
                'annotations': ['ANN-002'],
            }
        },
        'source_coverage_read_model': {
            'sources': [
                {'source_id': 'SRC-A', 'status': 'success', 'history_horizon': '3y', 'freshness_hours': 6, 'confidence': 0.9},
                {'source_id': 'ACLED', 'status': 'prepared_adapter', 'history_horizon': 'n/a', 'freshness_hours': None, 'confidence': None},
            ],
            'failed_sources': ['SRC-B'],
            'missing_sources': ['SRC-C'],
        },
        'report_catalog': {
            'daily_snapshot': {'format': 'Markdown + JSON', 'report_id': 'REP-DAILY-RUN-200', 'uncertainty': ['partial_success']},
            'country_profile': {'format': 'Markdown + JSON', 'report_id': 'REP-COUNTRY-UKR', 'country_id': 'UKR'},
            'coverage_report': {'format': 'Markdown + JSON + CSV', 'report_id': 'REP-COVERAGE-001'},
        },
        'system_status_read_model': {
            'run_id': 'RUN-200',
            'run_status': 'partial_success',
            'active_domains': ['A', 'B', 'D'],
            'coverage': {'countries_total': 30, 'countries_with_updates': 27},
            'failed_sources': ['SRC-B'],
            'available_reports': ['REP-DAILY-RUN-200', 'REP-COUNTRY-UKR'],
            'snapshot_id': 'SNAP-RUN-200-v1',
            'reprocessing_status': 'idle',
            'last_run': '2026-05-11T18:00:00Z',
        },
        'validation_view_model': {
            'case_id': 'VAL-UKR-2022-001',
            'country_id': 'UKR',
            'case_name': 'Escalation reference case',
            'time_range': {'start': '2022-02-01', 'end': '2022-03-01'},
            'expected_domains': ['A', 'B', 'D'],
            'observed_domains': ['A', 'B'],
            'domain_match_ratio': 2 / 3,
            'status_match': True,
            'expected_pattern': 'Aligned information, event, and economic stress escalation.',
            'validation_goal': 'Check multi-domain alignment detection.',
            'reference_sources': ['SRC-A', 'SRC-B'],
            'validation_metrics': ['Domain Match', 'Status Match'],
            'known_limitations': ['historical coverage incomplete'],
            'reprocessing_comparison': {'prior_snapshot_id': 'SNAP-RUN-001-v1', 'new_snapshot_id': 'SNAP-RUN-001-v2', 'changed_versions': ['rule_version']},
        },
        'annotations_view_model': {
            'annotations': [
                {
                    'annotation_id': 'ANN-001',
                    'created_at': '2026-05-11T18:05:00Z',
                    'author': 'analyst',
                    'scope': 'country',
                    'annotation_type': 'context_note',
                    'severity_assessment': 'relevant',
                    'confidence_assessment': 'medium',
                    'text': 'Replicated agency report likely inflated country-level signal volume.',
                    'tags': ['source_dependency'],
                    'linked_items': ['UKR'],
                    'review_status': 'draft',
                },
                {
                    'annotation_id': 'ANN-002',
                    'created_at': '2026-05-11T18:06:00Z',
                    'author': 'analyst',
                    'scope': 'domain',
                    'annotation_type': 'lineage_note',
                    'severity_assessment': 'uncertain',
                    'confidence_assessment': 'high',
                    'text': 'Domain A spike is traceable to two closely coupled source clusters.',
                    'tags': ['lineage'],
                    'linked_items': ['UKR:A', 'A_article_count'],
                    'review_status': 'reviewed',
                },
            ],
            'by_scope': {'country': ['ANN-001'], 'domain': ['ANN-002']},
            'by_linked_item': {'UKR': ['ANN-001'], 'UKR:A': ['ANN-002'], 'A_article_count': ['ANN-002']},
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Build a local SIASA MVP GUI site.')
    parser.add_argument('--output-dir', default='build/local_gui', help='Target directory for generated HTML files.')
    parser.add_argument(
        '--artifacts-dir',
        default=None,
        help='Optional directory containing persisted snapshot, report, and read-model JSON artifacts.',
    )
    args = parser.parse_args(argv)

    if args.artifacts_dir:
        payload = load_site_payload_from_artifacts(Path(args.artifacts_dir))
    else:
        payload = _demo_payload()
    result = build_local_mvp_site(output_dir=Path(args.output_dir), **payload)
    print(f'Generated SIASA local GUI at {result.output_dir / "index.html"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
