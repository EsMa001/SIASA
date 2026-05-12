from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SitePayload = dict[str, Any]


@dataclass(frozen=True)
class SiteBuildResult:
    output_dir: Path
    generated_files: list[Path]


def _page(title: str, body: str) -> str:
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
        "<nav>"
        "<a href='../index.html'>Home</a>"
        "<a href='../coverage.html'>Source / Coverage</a>"
        "<a href='../trends.html'>Yearly Trend Page</a>"
        "<a href='../events.html'>Current Events Page</a>"
        "<a href='../reports.html'>Report / Export View</a>"
        "<a href='../runs.html'>System Status / Runs</a>"
        "</nav>"
        f"<h1>{html.escape(title)}</h1>"
        f"{body}"
        "</body></html>"
    )


def _json_block(data: Any) -> str:
    return f"<pre>{html.escape(json.dumps(data, indent=2, sort_keys=True))}</pre>"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


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

    return {
        'world_map_read_model': world_map_read_model,
        'country_profile_read_models': country_profile_read_models,
        'domain_detail_read_models': domain_detail_read_models,
        'source_coverage_read_model': source_coverage_read_model,
        'report_catalog': report_catalog,
        'system_status_read_model': system_status_read_model,
    }


def _render_index(world_map_read_model: dict[str, Any]) -> str:
    rows = []
    for country in world_map_read_model.get("countries", []):
        country_id = str(country["country_id"])
        status = str(country["status"])
        rows.append(
            "<tr>"
            f"<td><a href='countries/{html.escape(country_id)}.html'>{html.escape(country_id)}</a></td>"
            f"<td class='status'>{html.escape(status)}</td>"
            f"<td>{html.escape(', '.join(country.get('active_domains', [])))}</td>"
            f"<td>countries/{html.escape(country_id)}.html</td>"
            "</tr>"
        )
    body = (
        "<h2>World Anomaly Map</h2>"
        f"<p>Baseline mode: <strong>{html.escape(str(world_map_read_model.get('baseline_mode', 'unknown')))}</strong></p>"
        f"<p>Active domains: {html.escape(', '.join(world_map_read_model.get('active_domains', [])))}</p>"
        "<h2>Global Overview</h2>"
        "<table><thead><tr><th>Country</th><th>Multi-Domain Status</th><th>Active Domains</th><th>Drill-down</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    return _page("World Anomaly Map / Global Overview", body)


def _render_country(country_profile: dict[str, Any]) -> str:
    domain_rows = ''.join(
        f"<tr><td>{html.escape(domain)}</td><td>{html.escape(status)}</td></tr>"
        for domain, status in country_profile.get('domain_states', {}).items()
    )
    body = (
        "<h2>Country Profile</h2>"
        f"<p>Country: <strong>{html.escape(str(country_profile.get('country_id', 'UNKNOWN')))}</strong></p>"
        f"<p>Multi-domain status: <span class='status'>{html.escape(str(country_profile.get('multi_domain_status', 'n/a')))}</span></p>"
        f"<p>Coverage: {html.escape(str(country_profile.get('coverage', 'n/a')))} | Confidence: {html.escape(str(country_profile.get('confidence', 'n/a')))}</p>"
        "<h3>Domain States</h3>"
        f"<table><thead><tr><th>Domain</th><th>Status</th></tr></thead><tbody>{domain_rows}</tbody></table>"
        f"<h3>Drivers</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('drivers', []))}</ul>"
        f"<h3>Counter Indicators</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('counter_indicators', []))}</ul>"
        f"<h3>Linked Events</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('linked_events', []))}</ul>"
        f"<h3>Uncertainty</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('uncertainty', []))}</ul>"
        f"<h3>Annotations</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('annotations', []))}</ul>"
        f"<h3>Trends</h3>{_json_block(country_profile.get('trends', {}))}"
    )
    return _page(f"Country Profile - {country_profile.get('country_id', 'UNKNOWN')}", body)


def _render_domain_detail(domain_detail: dict[str, Any]) -> str:
    body = (
        "<h2>Domain Detail</h2>"
        f"<p>Country: <strong>{html.escape(str(domain_detail.get('country_id', 'UNKNOWN')))}</strong></p>"
        f"<p>Domain: <strong>{html.escape(str(domain_detail.get('domain', 'UNKNOWN')))}</strong></p>"
        f"<p>Anomaly state: <span class='status'>{html.escape(str(domain_detail.get('anomaly_state', 'n/a')))}</span></p>"
        f"<h3>Time Series</h3>{_json_block(domain_detail.get('time_series', []))}"
        f"<h3>Baseline Comparison</h3>{_json_block(domain_detail.get('baseline_comparison', {}))}"
        f"<h3>Feature Values</h3>{_json_block(domain_detail.get('feature_values', []))}"
        f"<h3>Source Context</h3>{_json_block(domain_detail.get('source_context', []))}"
        f"<h3>Uncertainty</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in domain_detail.get('uncertainty', []))}</ul>"
    )
    return _page(
        f"Domain Detail - {domain_detail.get('country_id', 'UNKNOWN')} / {domain_detail.get('domain', 'UNKNOWN')}",
        body,
    )


def _render_source_coverage(source_coverage_read_model: dict[str, Any]) -> str:
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
    body = (
        "<h2>Source / Coverage View</h2>"
        "<table><thead><tr><th>Source</th><th>Status</th><th>History Horizon</th><th>Freshness (h)</th><th>Confidence</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        f"<h3>Failed Sources</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in source_coverage_read_model.get('failed_sources', []))}</ul>"
        f"<h3>Missing Sources</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in source_coverage_read_model.get('missing_sources', []))}</ul>"
    )
    return _page("Source / Coverage View", body)


def _render_reports(report_catalog: dict[str, Any]) -> str:
    rows = ''.join(
        "<tr>"
        f"<td>{html.escape(report_type)}</td>"
        f"<td>{html.escape(str(report_info.get('report_id', '')))}</td>"
        f"<td>{html.escape(str(report_info.get('format', '')))}</td>"
        f"<td>{html.escape(json.dumps(report_info, sort_keys=True))}</td>"
        "</tr>"
        for report_type, report_info in sorted(report_catalog.items())
    )
    body = (
        "<h2>Report / Export View</h2>"
        "<table><thead><tr><th>Type</th><th>Report ID</th><th>Format</th><th>Metadata</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )
    return _page("Report / Export View", body)


def _render_runs(system_status_read_model: dict[str, Any]) -> str:
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
    )
    return _page("System Status / Runs", body)


def _render_trends(country_profile_read_models: dict[str, dict[str, Any]]) -> str:
    rows = []
    for country_id, profile in sorted(country_profile_read_models.items()):
        yearly = profile.get('trends', {}).get('yearly', [])
        rows.append(
            "<tr>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td>{html.escape(', '.join(str(item) for item in yearly))}</td>"
            f"<td>{html.escape(str(profile.get('multi_domain_status', 'n/a')))}</td>"
            "</tr>"
        )
    body = (
        "<h2>Yearly Trend Page</h2>"
        "<table><thead><tr><th>Country</th><th>Yearly Trend</th><th>Current Multi-Domain Status</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    return _page("Yearly Trend Page", body)


def _render_events(country_profile_read_models: dict[str, dict[str, Any]]) -> str:
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
    return _page("Current Events Page", body)


def build_local_mvp_site(
    output_dir: Path,
    world_map_read_model: dict[str, Any],
    country_profile_read_models: dict[str, dict[str, Any]],
    domain_detail_read_models: dict[tuple[str, str], dict[str, Any]],
    source_coverage_read_model: dict[str, Any],
    report_catalog: dict[str, dict[str, Any]],
    system_status_read_model: dict[str, Any],
) -> SiteBuildResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    countries_dir = output_dir / 'countries'
    domains_dir = output_dir / 'domains'
    countries_dir.mkdir(exist_ok=True)
    domains_dir.mkdir(exist_ok=True)

    generated_files: list[Path] = []

    index_file = output_dir / 'index.html'
    index_file.write_text(_render_index(world_map_read_model))
    generated_files.append(index_file)

    for country_id, read_model in country_profile_read_models.items():
        country_file = countries_dir / f'{country_id}.html'
        country_file.write_text(_render_country(read_model))
        generated_files.append(country_file)

    for (country_id, domain), read_model in domain_detail_read_models.items():
        domain_file = domains_dir / f'{country_id}-{domain}.html'
        domain_file.write_text(_render_domain_detail(read_model))
        generated_files.append(domain_file)

    coverage_file = output_dir / 'coverage.html'
    coverage_file.write_text(_render_source_coverage(source_coverage_read_model))
    generated_files.append(coverage_file)

    reports_file = output_dir / 'reports.html'
    reports_file.write_text(_render_reports(report_catalog))
    generated_files.append(reports_file)

    runs_file = output_dir / 'runs.html'
    runs_file.write_text(_render_runs(system_status_read_model))
    generated_files.append(runs_file)

    trends_file = output_dir / 'trends.html'
    trends_file.write_text(_render_trends(country_profile_read_models))
    generated_files.append(trends_file)

    events_file = output_dir / 'events.html'
    events_file.write_text(_render_events(country_profile_read_models))
    generated_files.append(events_file)

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
