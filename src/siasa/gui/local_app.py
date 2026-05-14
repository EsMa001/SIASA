from __future__ import annotations

import argparse
import html
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from siasa.catalog import load_country_set
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



def _render_world_map_visualization(world_map_read_model: dict[str, Any], available_country_ids: set[str]) -> str:
    metadata_lookup = _country_metadata_lookup()
    region_offsets: dict[str, int] = {}
    markers: list[str] = []
    labels: list[str] = []
    legend_rows: list[str] = []

    for country in world_map_read_model.get('countries', []):
        country_id = str(country.get('country_id', 'UNKNOWN'))
        status = str(country.get('status', 'n/a'))
        metadata = metadata_lookup.get(country_id, {})
        region = str(metadata.get('region', 'Other / Unknown'))
        anchor_x, anchor_y = _region_anchor(region)
        offset_index = region_offsets.get(region, 0)
        region_offsets[region] = offset_index + 1
        x = anchor_x + (offset_index % 4) * 18
        y = anchor_y + (offset_index // 4) * 18
        color = _status_color(status)
        href = f"countries/{country_id}.html" if country_id in available_country_ids else None
        marker = (
            f"<a href='{html.escape(href)}'><circle cx='{x:.1f}' cy='{y:.1f}' r='7' fill='{color}' stroke='#1f2937' stroke-width='1'>"
            f"<title>{html.escape(country_id)} — {html.escape(status)} — {html.escape(region)}</title></circle></a>"
            if href
            else f"<circle cx='{x:.1f}' cy='{y:.1f}' r='7' fill='{color}' stroke='#1f2937' stroke-width='1'>"
                 f"<title>{html.escape(country_id)} — {html.escape(status)} — {html.escape(region)}</title></circle>"
        )
        markers.append(marker)
        labels.append(f"<text x='{x + 10:.1f}' y='{y + 4:.1f}' font-size='10'>{html.escape(country_id)}</text>")
        legend_rows.append(
            "<tr>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td>{html.escape(metadata.get('country_name', country_id))}</td>"
            f"<td>{html.escape(region)}</td>"
            f"<td>{html.escape(str(metadata.get('priority', 'n/a')))}</td>"
            f"<td><span class='status'>{html.escape(status)}</span></td>"
            "</tr>"
        )

    return (
        "<h3>Map Visualization</h3>"
        "<p>Region-anchored anomaly markers based on governed MVP country metadata.</p>"
        "<svg viewBox='0 0 340 210' width='340' height='210' role='img' aria-label='World anomaly map'>"
        "<rect x='5' y='5' width='330' height='200' rx='8' fill='#eef6ff' stroke='#cbd5e1' />"
        "<text x='25' y='35' font-size='12'>North America</text>"
        "<text x='165' y='35' font-size='12'>Europe</text>"
        "<text x='245' y='35' font-size='12'>Asia</text>"
        "<text x='165' y='150' font-size='12'>Africa / Middle East</text>"
        f"{''.join(markers)}{''.join(labels)}"
        "</svg>"
        "<table><thead><tr><th>Country</th><th>Name</th><th>Region</th><th>Priority</th><th>Status</th></tr></thead>"
        f"<tbody>{''.join(legend_rows)}</tbody></table>"
    )



def _annotation_index(annotations_view_model: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if annotations_view_model is None:
        return {}
    return {
        str(annotation.get('annotation_id')): annotation
        for annotation in annotations_view_model.get('annotations', [])
    }


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
    }


def _render_index(
    world_map_read_model: dict[str, Any],
    available_country_ids: set[str] | None = None,
    system_status_read_model: dict[str, Any] | None = None,
    *,
    nav_prefix: str = '',
    available_pages: set[str] | None = None,
) -> str:
    rows = []
    available_country_ids = available_country_ids or set()
    for country in world_map_read_model.get("countries", []):
        country_id = str(country["country_id"])
        status = str(country["status"])
        has_country_page = country_id in available_country_ids
        country_cell = (
            f"<a href='countries/{html.escape(country_id)}.html'>{html.escape(country_id)}</a>"
            if has_country_page
            else html.escape(country_id)
        )
        drill_down_cell = f"countries/{html.escape(country_id)}.html" if has_country_page else "not available"
        support_status = "supported" if has_country_page else "not available"
        rows.append(
            "<tr>"
            f"<td>{country_cell}</td>"
            f"<td>{html.escape(support_status)}</td>"
            f"<td class='status'>{html.escape(status)}</td>"
            f"<td>{html.escape(', '.join(country.get('active_domains', [])))}</td>"
            f"<td>{drill_down_cell}</td>"
            "</tr>"
        )

    system_status_read_model = system_status_read_model or {}
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
        f"{_render_world_map_visualization(world_map_read_model, available_country_ids)}"
        "<h2>Global Overview</h2>"
        "<table><thead><tr><th>Country</th><th>Support Status</th><th>Multi-Domain Status</th><th>Active Domains</th><th>Drill-down</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
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
    body = (
        "<h2>Country Profile</h2>"
        f"<p>Country: <strong>{html.escape(str(country_profile.get('country_id', 'UNKNOWN')))}</strong></p>"
        f"<p>Multi-domain status: <span class='status'>{html.escape(str(country_profile.get('multi_domain_status', 'n/a')))}</span></p>"
        f"<p>Coverage: {html.escape(str(country_profile.get('coverage', 'n/a')))} | Confidence: {html.escape(str(country_profile.get('confidence', 'n/a')))}</p>"
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
    body = (
        "<h2>Domain Detail</h2>"
        f"<p>Country: <strong>{html.escape(str(domain_detail.get('country_id', 'UNKNOWN')))}</strong></p>"
        f"<p>Domain: <strong>{html.escape(str(domain_detail.get('domain', 'UNKNOWN')))}</strong></p>"
        f"<p>Anomaly state: <span class='status'>{html.escape(str(domain_detail.get('anomaly_state', 'n/a')))}</span></p>"
        f"<h3>Time Series Chart</h3>{_render_line_chart(time_series, label_key='timestamp', chart_label='Domain time series') }"
        f"<h3>Time Series</h3>{_json_block(time_series)}"
        f"<h3>Baseline Comparison</h3>{_json_block(domain_detail.get('baseline_comparison', {}))}"
        f"<h3>Feature Values</h3>{_json_block(domain_detail.get('feature_values', []))}"
        f"<h3>Source Context</h3>{_json_block(domain_detail.get('source_context', []))}"
        f"<h3>Uncertainty</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in domain_detail.get('uncertainty', []))}</ul>"
        f"<h3>Annotation IDs</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in annotation_ids)}</ul>"
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
        f"<td>{html.escape(str(source.get('source_id', '')))}</td>"
        f"<td>{html.escape(str(source.get('status', '')))}</td>"
        f"<td>{html.escape(str(source.get('history_horizon', '')))}</td>"
        f"<td>{html.escape(str(source.get('freshness_hours', '')))}</td>"
        f"<td>{html.escape(str(source.get('confidence', '')))}</td>"
        "</tr>"
        for source in source_coverage_read_model.get('sources', [])
    )
    system_status_read_model = system_status_read_model or {}
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
        "<table><thead><tr><th>Source</th><th>Status</th><th>History Horizon</th><th>Freshness (h)</th><th>Confidence</th></tr></thead>"
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
    rows = ''.join(
        "<tr>"
        f"<td>{html.escape(report_type)}</td>"
        f"<td>{html.escape(str(report_info.get('report_id', '')))}</td>"
        f"<td>{html.escape(str(report_info.get('format', '')))}</td>"
        f"<td>{''.join(f'<div><a href=\"{html.escape(str(export_file.get("href", export_file.get("relative_path", ""))))}\">{html.escape(str(export_file.get("label", export_file.get("format", "download"))))}</a></div>' for export_file in report_info.get('export_files', [])) or '-'}</td>"
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


def _deduplicated_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _build_readiness_view_model(
    *,
    country_profile_read_models: dict[str, dict[str, Any]],
    domain_detail_read_models: dict[tuple[str, str], dict[str, Any]],
    report_catalog: dict[str, dict[str, Any]],
    system_status_read_model: dict[str, Any],
    source_coverage_read_model: dict[str, Any],
    validation_view_model: dict[str, Any] | None,
    traceability_view_model: dict[str, Any] | None,
    annotations_view_model: dict[str, Any] | None,
    repo_closure_view_model: dict[str, Any] | None,
    available_pages: set[str],
) -> dict[str, Any]:
    demo_checks = [
        {"label": "Home", "ready": "index.html" in available_pages},
        {"label": "Country Profile", "ready": bool(country_profile_read_models)},
        {"label": "Domain Detail", "ready": bool(domain_detail_read_models)},
        {"label": "Source / Coverage", "ready": "coverage.html" in available_pages},
        {"label": "Report / Export", "ready": "reports.html" in available_pages},
        {"label": "Validation / Backtest", "ready": validation_view_model is not None},
    ]
    evidence_checks = [
        {"label": "Traceability / Lineage", "ready": traceability_view_model is not None},
        {"label": "Analyst Annotations", "ready": annotations_view_model is not None},
        {"label": "Repo Closure Summary", "ready": repo_closure_view_model is not None},
        {"label": "Available Reports", "ready": bool(report_catalog)},
    ]
    demo_verdict = "ready" if all(check["ready"] for check in demo_checks) else "blocked"
    known_gaps = _deduplicated_strings(
        [str(item) for item in system_status_read_model.get("data_gaps", [])]
        + [f"failed_source:{item}" for item in system_status_read_model.get("failed_sources", [])]
        + [f"missing_source:{item}" for item in source_coverage_read_model.get("missing_sources", [])]
        + (["missing_validation_artifact"] if validation_view_model is None else [])
        + (["missing_traceability_artifact"] if traceability_view_model is None else [])
        + (["missing_repo_closure_artifact"] if repo_closure_view_model is None else [])
        + (["missing_annotations_artifact"] if annotations_view_model is None else [])
    )
    release_verdict = "blocked_by_known_gaps" if known_gaps else ("ready" if demo_verdict == "ready" else "blocked")
    return {
        "run_id": system_status_read_model.get("run_id"),
        "snapshot_id": system_status_read_model.get("snapshot_id"),
        "demo_verdict": demo_verdict,
        "release_verdict": release_verdict,
        "demo_checks": demo_checks,
        "evidence_checks": evidence_checks,
        "known_gaps": known_gaps,
        "report_count": len(report_catalog),
        "country_profile_count": len(country_profile_read_models),
        "domain_detail_count": len(domain_detail_read_models),
    }


def _render_readiness(readiness_view_model: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
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
        "<h3>Known Gaps Before Release</h3>"
        f"<ul>{known_gap_items}</ul>"
    )
    return _page("Demo / Release Readiness", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_trends(country_profile_read_models: dict[str, dict[str, Any]], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    rows = []
    for country_id, profile in sorted(country_profile_read_models.items()):
        yearly = profile.get('trends', {}).get('yearly', [])
        rows.append(
            "<tr>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td><h4>Trend Chart</h4>{_render_line_chart(yearly, label_key='label', chart_label=f'{country_id} yearly trend')}</td>"
            f"<td>{html.escape(str(profile.get('multi_domain_status', 'n/a')))}</td>"
            "</tr>"
        )
    body = (
        "<h2>Yearly Trend Page</h2>"
        "<table><thead><tr><th>Country</th><th>Yearly Trend</th><th>Current Multi-Domain Status</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    return _page("Yearly Trend Page", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_events(country_profile_read_models: dict[str, dict[str, Any]], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    rows = []
    for country_id, profile in sorted(country_profile_read_models.items()):
        for event_id in profile.get('linked_events', []):
            rows.append(
                "<tr>"
                f"<td>{html.escape(country_id)}</td>"
                f"<td>{html.escape(str(event_id))}</td>"
                f"<td>{html.escape(str(profile.get('multi_domain_status', 'n/a')))}</td>"
                "</tr>"
            )
    body = (
        "<h2>Current Events Page</h2>"
        "<table><thead><tr><th>Country</th><th>Event</th><th>Context Status</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    return _page("Current Events Page", body, nav_prefix=nav_prefix, available_pages=available_pages)


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
        "<h3>Changed Versions</h3>"
        f"<ul>{changed_versions}</ul>"
        f"<h3>Reprocessing Comparison</h3>{_json_block(reprocessing)}"
    )
    return _page("Validation / Backtest View", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_traceability(traceability_view_model: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
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
        for record in traceability_view_model.get('lineage_records', [])
    )
    body = (
        "<h2>Traceability / Lineage View</h2>"
        "<table><thead><tr><th>Source</th><th>Raw</th><th>Normalized</th><th>Feature</th><th>Domain Status</th><th>Multi-Domain Status</th><th>Snapshot</th><th>Report</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
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
    body = (
        "<h2>Analyst Annotations View</h2>"
        f"<p>Total annotations: <strong>{html.escape(str(len(annotations_view_model.get('annotations', []))))}</strong></p>"
        f"<h3>Annotation Details</h3>{_annotation_details_html([str(item.get('annotation_id')) for item in annotations_view_model.get('annotations', [])], annotations_view_model)}"
        "<h3>By Scope</h3>"
        "<table><thead><tr><th>Scope</th><th>Annotation IDs</th></tr></thead>"
        f"<tbody>{scope_rows}</tbody></table>"
        "<h3>By Linked Item</h3>"
        "<table><thead><tr><th>Linked Item</th><th>Annotation IDs</th></tr></thead>"
        f"<tbody>{linked_item_rows}</tbody></table>"
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

    readiness_view_model = _build_readiness_view_model(
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
