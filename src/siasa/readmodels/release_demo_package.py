from __future__ import annotations

import html
from datetime import UTC, datetime
from typing import Any


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    return [dict(item) for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _greenish(verdict: str) -> bool:
    return verdict.lower() in {'ready', 'pass', 'ok', 'green', 'go'}


def _page_label(page_name: str) -> str:
    return {
        'coverage.html': 'Coverage',
        'validation.html': 'Validation',
        'readiness.html': 'Readiness',
        'traceability.html': 'Traceability',
        'reports.html': 'Reports',
        'index.html': 'Overview',
        'events.html': 'Events',
        'comparison.html': 'Comparison',
    }.get(page_name, page_name.replace('.html', '').replace('_', ' ').title())


def build_release_demo_package_view_model(
    *,
    readiness_view_model: dict[str, Any],
    release_gate_view_model: dict[str, Any] | None = None,
    operator_release_summary_view_model: dict[str, Any] | None = None,
    operator_blocker_causality_view_model: dict[str, Any] | None = None,
    operator_operability_cluster_view_model: dict[str, Any] | None = None,
    operator_stale_remediation_action_plan_view_model: dict[str, Any] | None = None,
    system_status_read_model: dict[str, Any] | None = None,
    validation_view_model: dict[str, Any] | None = None,
    traceability_view_model: dict[str, Any] | None = None,
    repo_closure_view_model: dict[str, Any] | None = None,
    analyst_briefing_view_model: dict[str, Any] | None = None,
    available_pages: set[str] | None = None,
) -> dict[str, Any]:
    release_gate_view_model = release_gate_view_model or {}
    operator_release_summary_view_model = operator_release_summary_view_model or {}
    operator_blocker_causality_view_model = operator_blocker_causality_view_model or {}
    operator_operability_cluster_view_model = operator_operability_cluster_view_model or {}
    operator_stale_remediation_action_plan_view_model = operator_stale_remediation_action_plan_view_model or {}
    system_status_read_model = system_status_read_model or {}
    validation_view_model = validation_view_model or {}
    traceability_view_model = traceability_view_model or {}
    repo_closure_view_model = repo_closure_view_model or {}
    analyst_briefing_view_model = analyst_briefing_view_model or {}
    available_pages = set(available_pages or set())

    release_verdict = str(readiness_view_model.get('release_verdict', 'unknown'))
    demo_verdict = str(readiness_view_model.get('demo_verdict', 'unknown'))
    gate_verdict = str(release_gate_view_model.get('gate_verdict', 'unknown'))
    release_green = _greenish(release_verdict) and _greenish(gate_verdict)

    if analyst_briefing_view_model.get('items'):
        source_items = _as_dict_list(analyst_briefing_view_model.get('items'))
    else:
        source_items = []
        visibility = system_status_read_model.get('country_coverage_visibility', {}) if isinstance(system_status_read_model, dict) else {}
        country_gap_rows = [row for row in visibility.get('country_gap_rows', []) if isinstance(row, dict)] if isinstance(visibility, dict) else []
        stale_priority_watchlist = [row for row in visibility.get('stale_priority_watchlist', []) if isinstance(row, dict)] if isinstance(visibility, dict) else []
        traceability_summary = traceability_view_model.get('summary', {}) if isinstance(traceability_view_model, dict) else {}
        if release_verdict.lower() not in {'ready', 'pass', 'ok', 'green'} or gate_verdict.lower() not in {'go', 'ready', 'pass', 'ok', 'green'}:
            source_items.append(
                {
                    'category': 'release_blocker',
                    'title': f"Release blocker: {operator_blocker_causality_view_model.get('primary_root_cause_gate_id', 'unknown') or 'unknown'}",
                    'why_it_matters': f"Release verdict is {release_verdict} and gate verdict is {gate_verdict}.",
                    'recommended_next_check': str(
                        operator_blocker_causality_view_model.get('operator_next_action')
                        or operator_release_summary_view_model.get('operator_next_action')
                        or 'Inspect release blockers.'
                    ),
                    'evidence_source': 'release_evidence_assessment.json',
                    'target_page': 'readiness.html',
                }
            )
        if country_gap_rows:
            top_gap = country_gap_rows[0]
            source_items.append(
                {
                    'category': 'country_gap',
                    'title': f"Country gap: {top_gap.get('country_id', 'UNKNOWN')} missing {', '.join(str(domain) for domain in top_gap.get('missing_domains', [])) or 'unknown domains'}",
                    'why_it_matters': f"Country coverage is incomplete for {top_gap.get('country_id', 'UNKNOWN')}.",
                    'recommended_next_check': 'Inspect coverage.html and the country/domain gap details.',
                    'evidence_source': 'system_status.json country_coverage_visibility.country_gap_rows',
                    'target_page': 'coverage.html',
                }
            )
        validation_summary = validation_view_model.get('historical_replay_summary', {}) if isinstance(validation_view_model, dict) else {}
        attention_cases = [item for item in validation_summary.get('attention_cases', []) if isinstance(item, dict)] if isinstance(validation_summary, dict) else []
        if attention_cases:
            top_case = attention_cases[0]
            source_items.append(
                {
                    'category': 'validation_attention',
                    'title': f"Validation attention: {top_case.get('case_id', 'unknown')}",
                    'why_it_matters': f"{top_case.get('country_id', 'unknown')} needs review because {top_case.get('attention_reason', 'validation_attention')}.",
                    'recommended_next_check': str(top_case.get('suggested_next_action', 'Review validation evidence.')),
                    'evidence_source': 'validation_backtest.json historical_replay_summary.attention_cases',
                    'target_page': 'validation.html',
                }
            )
        traceability_missing_mappings = int(traceability_summary.get('missing_requirement_mapping_count', 0) or 0)
        traceability_orphans = int(traceability_summary.get('orphan_mapped_requirement_count', 0) or 0)
        traceability_unhealthy_slices = int(traceability_summary.get('unhealthy_slice_count', 0) or 0)
        traceability_closure_at_risk = int(traceability_summary.get('closure_at_risk', 0) or 0)
        if traceability_missing_mappings or traceability_orphans or traceability_unhealthy_slices or traceability_closure_at_risk:
            source_items.append(
                {
                    'category': 'traceability_risk',
                    'title': 'Traceability risk: ' + ', '.join(
                        part for part in [
                            f"{traceability_missing_mappings} missing mappings" if traceability_missing_mappings else '',
                            f"{traceability_unhealthy_slices} unhealthy slices" if traceability_unhealthy_slices else '',
                            f"{traceability_closure_at_risk} at-risk closures" if traceability_closure_at_risk else '',
                            f"{traceability_orphans} orphan mappings" if traceability_orphans else '',
                        ]
                        if part
                    ),
                    'why_it_matters': (
                        'Traceability integrity still has '
                        f'{traceability_missing_mappings} missing mappings, {traceability_unhealthy_slices} unhealthy slices, '
                        f'and {traceability_closure_at_risk} closure-at-risk items.'
                    ),
                    'recommended_next_check': 'Inspect traceability.html and repo closure slice details.',
                    'evidence_source': 'traceability_lineage.json + repo_closure.json',
                    'target_page': 'traceability.html',
                }
            )
        operator_operability_status = str(operator_operability_cluster_view_model.get('cluster_status', 'unknown')).lower()
        operator_operability_failed = int(operator_operability_cluster_view_model.get('failed_gate_count', 0) or 0)
        if operator_operability_cluster_view_model and (operator_operability_status not in {'healthy', 'green', 'ok', 'pass'} or operator_operability_failed > 0):
            source_items.append(
                {
                    'category': 'operability_cluster',
                    'title': f"Operability cluster: {operator_operability_status}",
                    'why_it_matters': f"Stakeholder flows and browser gates are not fully green: {operator_operability_failed} failed gates reported.",
                    'recommended_next_check': str(operator_operability_cluster_view_model.get('operator_next_action') or 'Review readiness and operability cluster details.'),
                    'evidence_source': 'release_evidence_assessment.json operator_operability_cluster',
                    'target_page': 'readiness.html',
                }
            )
        if stale_priority_watchlist:
            top_stale = stale_priority_watchlist[0]
            source_items.append(
                {
                    'category': 'stale_priority',
                    'title': f"Stale priority: {top_stale.get('country_id', 'UNKNOWN')}",
                    'why_it_matters': f"Priority {top_stale.get('priority', 'n/a')} country has {top_stale.get('freshness_hours', 'n/a')} stale hours.",
                    'recommended_next_check': 'Inspect stale coverage priority queue and remediation watchlist.',
                    'evidence_source': 'system_status.json country_coverage_visibility.stale_priority_watchlist',
                    'target_page': 'coverage.html',
                }
            )
        if operator_stale_remediation_action_plan_view_model:
            action_count = int(operator_stale_remediation_action_plan_view_model.get('action_count', 0) or 0)
            next_action_id = str(operator_stale_remediation_action_plan_view_model.get('next_action_id', 'n/a'))
            if action_count > 0:
                source_items.append(
                    {
                        'category': 'stale_remediation_action_plan',
                        'title': f'Stale remediation action plan: {next_action_id}',
                        'why_it_matters': f'Stale-remediation planning still has {action_count} actionable steps queued.',
                        'recommended_next_check': str(operator_stale_remediation_action_plan_view_model.get('operator_next_action') or 'Review stale remediation action plan.'),
                        'evidence_source': 'release_failure_drill_report.json operator_stale_remediation_action_plan',
                        'target_page': 'readiness.html',
                    }
                )

    source_items = source_items[:4]
    if not source_items:
        source_items = [
            {
                'category': 'release_ready',
                'title': 'Release package ready for review',
                'why_it_matters': 'The current release and demo surfaces are green enough to walk the stakeholder flow.',
                'recommended_next_check': 'Use the demo sequence below as the release walkthrough.',
                'evidence_source': 'readiness.json + release_gate.json',
                'target_page': 'readiness.html',
            }
        ]
    for rank, item in enumerate(source_items, start=1):
        item['rank'] = rank

    priority_rows = ''.join(
        '<tr>'
        f"<td>{html.escape(str(item.get('rank', '')))}</td>"
        f"<td>{html.escape(str(item.get('category', '')))}</td>"
        f"<td>{html.escape(str(item.get('title', '')))}</td>"
        f"<td>{html.escape(str(item.get('why_it_matters', '')))}</td>"
        f"<td>{html.escape(str(item.get('recommended_next_check', '')))}</td>"
        f"<td>{html.escape(str(item.get('target_page', '')))}</td>"
        '</tr>'
        for item in source_items
    )
    demo_sequence = [
        ('readiness.html', 'Confirm the release and demo verdicts.', 'release & demo gate'),
        ('coverage.html', 'Inspect country coverage and stale priority watchlists.', 'coverage & freshness'),
        ('validation.html', 'Review validation attention cases and replay deltas.', 'validation evidence'),
        ('traceability.html', 'Check lineage, closure, and requirement mapping health.', 'traceability & closure'),
        ('reports.html', 'Open the latest evidence reports and run artifacts.', 'report catalog'),
    ]
    demo_rows = ''.join(
        '<tr>'
        f"<td>{html.escape(_page_label(page))}</td>"
        f"<td>{html.escape(page)}</td>"
        f"<td>{html.escape(description)}</td>"
        f"<td>{html.escape(status)}</td>"
        f"<td>{html.escape('yes' if page in available_pages else 'no')}</td>"
        '</tr>'
        for page, description, status in demo_sequence
    )
    evidence_items = [
        ('Release verdict', release_verdict),
        ('Gate verdict', gate_verdict),
        ('Demo verdict', demo_verdict),
        ('Primary focus', source_items[0].get('title', 'n/a')),
        ('Source pages', ', '.join(sorted(page for page in {item.get('target_page', '') for item in source_items} if page))),
        ('Available pages', str(len(available_pages))),
    ]
    review_sequence = [
        {
            'step_id': 'C3-01',
            'phase': 'Gate posture',
            'page_label': _page_label('readiness.html'),
            'page_name': 'readiness.html',
            'objective': 'Confirm whether the package is reviewable at all before diving into details.',
            'reviewer_question': 'Are release verdict, demo verdict, and gate verdict aligned enough to continue the walkthrough?',
            'expected_signal': f"release={release_verdict}, demo={demo_verdict}, gate={gate_verdict}",
            'available': 'readiness.html' in available_pages,
            'href': 'readiness.html' if 'readiness.html' in available_pages else '',
        },
        {
            'step_id': 'C3-02',
            'phase': 'Primary focus',
            'page_label': _page_label(source_items[0].get('target_page', 'readiness.html')),
            'page_name': str(source_items[0].get('target_page', 'readiness.html')),
            'objective': 'Inspect the highest-priority current review item first.',
            'reviewer_question': str(source_items[0].get('recommended_next_check', 'Inspect the primary review item.')),
            'expected_signal': str(source_items[0].get('title', 'n/a')),
            'available': str(source_items[0].get('target_page', '')) in available_pages,
            'href': str(source_items[0].get('target_page', '')) if str(source_items[0].get('target_page', '')) in available_pages else '',
        },
        {
            'step_id': 'C3-03',
            'phase': 'Coverage posture',
            'page_label': _page_label('coverage.html'),
            'page_name': 'coverage.html',
            'objective': 'Check whether geographic/source coverage gaps undermine stakeholder confidence.',
            'reviewer_question': 'Do coverage gaps or stale-priority queues change the interpretation of the current package?',
            'expected_signal': 'country gaps and stale-priority cues are explicit and bounded',
            'available': 'coverage.html' in available_pages,
            'href': 'coverage.html' if 'coverage.html' in available_pages else '',
        },
        {
            'step_id': 'C3-04',
            'phase': 'Validation posture',
            'page_label': _page_label('validation.html'),
            'page_name': 'validation.html',
            'objective': 'Verify whether replay-attention evidence supports or weakens the current storyline.',
            'reviewer_question': 'Which replay-attention slice most directly challenges the current package conclusion?',
            'expected_signal': 'attention cases, verdict mix, and replay evidence tier stay visible',
            'available': 'validation.html' in available_pages,
            'href': 'validation.html' if 'validation.html' in available_pages else '',
        },
        {
            'step_id': 'C3-05',
            'phase': 'Traceability posture',
            'page_label': _page_label('traceability.html'),
            'page_name': 'traceability.html',
            'objective': 'Confirm that the stakeholder narrative is still anchored in traceable governed evidence.',
            'reviewer_question': 'Are there traceability or closure-at-risk signals that would block sign-off?',
            'expected_signal': 'lineage, repo closure, and mapping-health evidence are reviewable',
            'available': 'traceability.html' in available_pages,
            'href': 'traceability.html' if 'traceability.html' in available_pages else '',
        },
        {
            'step_id': 'C3-06',
            'phase': 'Artifact handoff',
            'page_label': _page_label('reports.html'),
            'page_name': 'reports.html',
            'objective': 'Finish with concrete downloadable evidence for follow-up and audit handoff.',
            'reviewer_question': 'Is the report/export bundle sufficient for offline follow-up and decision logging?',
            'expected_signal': 'latest report catalog and exports are reachable',
            'available': 'reports.html' in available_pages,
            'href': 'reports.html' if 'reports.html' in available_pages else '',
        },
    ]
    evidence_rows = ''.join(
        '<tr>'
        f"<td>{html.escape(label)}</td>"
        f"<td>{html.escape(str(value))}</td>"
        '</tr>'
        for label, value in evidence_items
    )
    package_status = 'ready' if release_green and not any(item.get('category') == 'release_blocker' for item in source_items) else ('attention' if source_items else 'ready')
    if any(item.get('category') == 'release_blocker' for item in source_items) or not release_green:
        package_status = 'blocked'

    return {
        'generated_at_utc': datetime.now(UTC).isoformat(),
        'package_name': 'Release / Demo Package',
        'package_status': package_status,
        'release_verdict': release_verdict,
        'demo_verdict': demo_verdict,
        'gate_verdict': gate_verdict,
        'release_green': release_green,
        'priority_item_count': len(source_items),
        'primary_item_title': source_items[0].get('title', 'n/a'),
        'primary_item_category': source_items[0].get('category', 'n/a'),
        'primary_item_target_page': source_items[0].get('target_page', 'n/a'),
        'primary_item_next_check': source_items[0].get('recommended_next_check', 'n/a'),
        'primary_item_evidence_source': source_items[0].get('evidence_source', 'n/a'),
        'priority_items': source_items,
        'demo_sequence': [
            {
                'page_label': _page_label(page),
                'page_name': page,
                'description': description,
                'status_label': status,
                'available': page in available_pages,
            }
            for page, description, status in demo_sequence
        ],
        'review_sequence': review_sequence,
        'evidence_items': [{'label': label, 'value': value} for label, value in evidence_items],
        'priority_target_pages': sorted({str(item.get('target_page', '')) for item in source_items if item.get('target_page')}),
        'source_item_pages': sorted({str(item.get('target_page', '')) for item in source_items if item.get('target_page')}),
        'readiness_view_model': {
            'demo_verdict': readiness_view_model.get('demo_verdict'),
            'release_verdict': readiness_view_model.get('release_verdict'),
            'release_readiness_percent': readiness_view_model.get('release_readiness_percent'),
        },
    }


def render_release_demo_package_body(view_model: dict[str, Any]) -> str:
    priority_items = _as_dict_list(view_model.get('priority_items'))
    if not priority_items:
        priority_items = [{
            'rank': 1,
            'category': 'release_ready',
            'title': 'Release package ready for review',
            'why_it_matters': 'No blocking evidence remains in the current package.',
            'recommended_next_check': 'Proceed with the demo sequence.',
            'target_page': 'readiness.html',
            'evidence_source': 'readiness.json',
        }]
    priority_rows = ''.join(
        '<tr>'
        f"<td>{html.escape(str(item.get('rank', '')))}</td>"
        f"<td>{html.escape(str(item.get('category', '')))}</td>"
        f"<td>{html.escape(str(item.get('title', '')))}</td>"
        f"<td>{html.escape(str(item.get('why_it_matters', '')))}</td>"
        f"<td>{html.escape(str(item.get('recommended_next_check', '')))}</td>"
        f"<td>{html.escape(str(item.get('target_page', '')))}</td>"
        f"<td>{html.escape(str(item.get('evidence_source', '')))}</td>"
        '</tr>'
        for item in priority_items
    )
    demo_rows = ''.join(
        '<tr>'
        f"<td>{html.escape(str(item.get('page_label', '')))}</td>"
        f"<td>{html.escape(str(item.get('page_name', '')))}</td>"
        f"<td>{html.escape(str(item.get('description', '')))}</td>"
        f"<td>{html.escape(str(item.get('status_label', '')))}</td>"
        f"<td>{html.escape('yes' if bool(item.get('available')) else 'no')}</td>"
        '</tr>'
        for item in _as_dict_list(view_model.get('demo_sequence'))
    ) or "<tr><td colspan='5'>No demo sequence available.</td></tr>"
    review_rows = ''.join(
        '<tr>'
        f"<td>{html.escape(str(item.get('step_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('phase', '')))}</td>"
        f"<td>{html.escape(str(item.get('page_label', '')))}</td>"
        f"<td>{html.escape(str(item.get('objective', '')))}</td>"
        f"<td>{html.escape(str(item.get('reviewer_question', '')))}</td>"
        f"<td>{html.escape(str(item.get('expected_signal', '')))}</td>"
        f"<td>{html.escape('yes' if bool(item.get('available')) else 'no')}</td>"
        '</tr>'
        for item in _as_dict_list(view_model.get('review_sequence'))
    ) or "<tr><td colspan='7'>No guided review sequence available.</td></tr>"
    evidence_rows = ''.join(
        '<tr>'
        f"<td>{html.escape(str(item.get('label', '')))}</td>"
        f"<td>{html.escape(str(item.get('value', '')))}</td>"
        '</tr>'
        for item in _as_dict_list(view_model.get('evidence_items'))
    )
    status = html.escape(str(view_model.get('package_status', 'unknown')))
    release_verdict = html.escape(str(view_model.get('release_verdict', 'unknown')))
    demo_verdict = html.escape(str(view_model.get('demo_verdict', 'unknown')))
    gate_verdict = html.escape(str(view_model.get('gate_verdict', 'unknown')))
    primary_focus = html.escape(str(view_model.get('primary_item_title', 'n/a')))
    primary_next_check = html.escape(str(view_model.get('primary_item_next_check', 'n/a')))
    primary_target_page = html.escape(str(view_model.get('primary_item_target_page', 'n/a')))
    package_name = html.escape(str(view_model.get('package_name', 'Release / Demo Package')))
    generated_at = html.escape(str(view_model.get('generated_at_utc', 'n/a')))

    return (
        "<section class='panel'>"
        f"<div class='panel-header'>{package_name}</div>"
        f"<p><strong>Package status:</strong> {status} · <strong>Release verdict:</strong> {release_verdict} · <strong>Demo verdict:</strong> {demo_verdict} · <strong>Gate verdict:</strong> {gate_verdict}</p>"
        f"<p><strong>Primary focus:</strong> {primary_focus}</p>"
        f"<p><strong>Next check:</strong> {primary_next_check}</p>"
        f"<p><strong>Primary target page:</strong> {primary_target_page}</p>"
        f"<p><strong>Generated:</strong> {generated_at}</p>"
        "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Prioritized items</div>"
        "<div class='table-wrap'><table><thead><tr><th>Rank</th><th>Category</th><th>Title</th><th>Why it matters</th><th>Next check</th><th>Target page</th><th>Evidence source</th></tr></thead><tbody>"
        f"{priority_rows or '<tr><td colspan=\'7\'>No prioritized items available.</td></tr>'}"
        "</tbody></table></div>"
        "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Demo sequence</div>"
        "<div class='table-wrap'><table><thead><tr><th>Page</th><th>Route</th><th>Description</th><th>Status focus</th><th>Available</th></tr></thead><tbody>"
        f"{demo_rows}"
        "</tbody></table></div>"
        "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Guided review sequence</div>"
        "<div class='table-wrap'><table><thead><tr><th>Step</th><th>Phase</th><th>Page</th><th>Objective</th><th>Reviewer question</th><th>Expected signal</th><th>Available</th></tr></thead><tbody>"
        f"{review_rows}"
        "</tbody></table></div>"
        "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Evidence bundle</div>"
        "<div class='table-wrap'><table><thead><tr><th>Item</th><th>Value</th></tr></thead><tbody>"
        f"{evidence_rows or '<tr><td colspan=\'2\'>No evidence summary available.</td></tr>'}"
        "</tbody></table></div>"
        "</section>"
    )
