from __future__ import annotations

import html
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote_plus


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



def _safe_navigation_page_name(href: str) -> str:
    return str(href).split('?', 1)[0].split('#', 1)[0]



def _is_safe_internal_navigation_href(href: str) -> bool:
    return bool(href) and href.endswith('.html') or bool(href) and '.html?' in href or bool(href) and '.html#' in href



def _render_nav_link(*, href: str | None, label: str, css_class: str, available_pages: set[str]) -> str:
    href = str(href or '').strip()
    if not href:
        return html.escape(label)
    page_name = _safe_navigation_page_name(href)
    if not _is_safe_internal_navigation_href(href) or page_name not in available_pages:
        return html.escape(label)
    return f"<a class='{css_class}' href='{html.escape(href)}'>{html.escape(label)}</a>"



def _coverage_prefill_href(*, country_id: str, focus_section: str, missing_domains: list[str] | None = None) -> str:
    query_parts = [
        f"focus_country={quote_plus(country_id)}",
        f"focus_section={quote_plus(focus_section)}",
    ]
    if missing_domains:
        query_parts.append(f"missing_domains={quote_plus(','.join(str(item) for item in missing_domains if str(item)))}")
    anchor_target = 'stale-priority' if focus_section == 'stale_priority' else 'country-gap'
    return f"coverage.html?{'&'.join(query_parts)}#{anchor_target}-{country_id}"



def _validation_prefill_href(*, country_id: str, case_id: str, attention_reason: str) -> str:
    hash_parts = [
        f"ra_reason={quote_plus(attention_reason)}",
        f"ra_text={quote_plus(f'{country_id} {case_id}')}",
    ]
    return f"validation.html#ra={'&'.join(hash_parts)}"



def _annotation_type_and_decision_posture(*, attention_case: dict[str, Any]) -> tuple[str, str]:
    attention_reason = str(attention_case.get('attention_reason', '') or '').strip().lower()
    if attention_reason == 'status_overcall':
        return (
            'false_positive_note',
            'Treat as potential false-positive over-escalation until bounded expectation alignment is reviewed.',
        )
    if attention_reason in {'domain_coverage_gap', 'weak_replay_evidence'}:
        return (
            'source_quality_note',
            'Treat as source-quality or coverage issue before escalating this case.',
        )
    if attention_reason == 'status_mismatch_and_domain_gap':
        return (
            'source_quality_note',
            'Review expectation alignment and source coverage together before treating this case as a strong signal.',
        )
    return (
        'review_note',
        'Review bounded validation expectation alignment before accepting or rejecting this signal.',
    )


def _build_follow_up_decision_template(*, annotation_type: str, decision_posture: str) -> dict[str, Any]:
    annotation_type = str(annotation_type or '').strip().lower()
    decision_posture = str(decision_posture or '').strip()
    if annotation_type == 'false_positive_note':
        return {
            'decision_focus': 'false_positive_review',
            'recommended_disposition': 'defer',
            'reviewer_prompt': 'Confirm bounded expectation misalignment before approving or distributing this signal.',
            'checklist': [
                'Compare expected vs replayed status and record why the replay may be overstated.',
                'Confirm whether the available evidence supports a false-positive interpretation instead of escalation.',
                'Record explicit reviewer rationale before any external distribution decision.',
            ],
        }
    if annotation_type == 'source_quality_note':
        return {
            'decision_focus': 'source_quality_review',
            'recommended_disposition': 'approve_with_conditions',
            'reviewer_prompt': 'Confirm whether coverage or evidence-quality remediation is required before treating this signal as distribution-ready.',
            'checklist': [
                'Verify whether missing domains or weak evidence materially change the signal interpretation.',
                'Record the required remediation or compensating reviewer condition explicitly.',
                'Keep distribution gated until the evidence-quality condition is bounded.',
            ],
        }
    return {
        'decision_focus': 'bounded_alignment_review',
        'recommended_disposition': 'approve_with_conditions',
        'reviewer_prompt': 'Confirm bounded expectation alignment and capture any residual reviewer condition before distribution.',
        'checklist': [
            'Review the bounded expectation and replay evidence together.',
            'Record any remaining reviewer caveat explicitly in the decision log.',
            'Proceed only when the interpretation is bounded for stakeholder handoff.',
        ],
    }


def _render_follow_up_decision_template_html(template: dict[str, Any]) -> str:
    if not isinstance(template, dict) or not template:
        return ''
    checklist_html = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in template.get('checklist', [])
    ) or '<li>none</li>'
    return (
        "<div><strong>Follow-up decision template</strong><ul>"
        f"<li><strong>Decision focus</strong>: {html.escape(str(template.get('decision_focus', 'n/a')))}</li>"
        f"<li><strong>Recommended disposition</strong>: {html.escape(str(template.get('recommended_disposition', 'n/a')))}</li>"
        f"<li><strong>Reviewer prompt</strong>: {html.escape(str(template.get('reviewer_prompt', 'n/a')))}</li>"
        f"<li><strong>Checklist</strong><ul>{checklist_html}</ul></li>"
        "</ul></div>"
    )


def _annotation_prefill_href(*, attention_case: dict[str, Any]) -> str:
    annotation_type, decision_posture = _annotation_type_and_decision_posture(attention_case=attention_case)
    query_parts = [
        "scope=country",
        f"annotation_type={quote_plus(annotation_type)}",
        f"country_id={quote_plus(str(attention_case.get('country_id', '')))}",
        f"case_id={quote_plus(str(attention_case.get('case_id', '')))}",
        f"attention_reason={quote_plus(str(attention_case.get('attention_reason', '')))}",
        f"owner_hint={quote_plus(str(attention_case.get('owner_hint', '')))}",
        f"suggested_next_action={quote_plus(str(attention_case.get('suggested_next_action', '')))}",
        f"decision_posture={quote_plus(decision_posture)}",
        f"attention_level={quote_plus(str(attention_case.get('attention_level', '')))}",
        f"replay_evidence_tier={quote_plus(str(attention_case.get('replay_evidence_tier', '')))}",
        f"review_verdict={quote_plus(str(attention_case.get('review_verdict', '')))}",
        f"replay_evidence_score={quote_plus(str(attention_case.get('replay_evidence_score', '')))}",
        f"domain_match_ratio={quote_plus(str(attention_case.get('domain_match_ratio', '')))}",
        f"expected_status={quote_plus(str(attention_case.get('expected_status', '')))}",
        f"replayed_status={quote_plus(str(attention_case.get('replayed_status', '')))}",
        f"missing_expected_domains={quote_plus(','.join(str(domain) for domain in attention_case.get('missing_expected_domains', [])))}",
        f"unexpected_observed_domains={quote_plus(','.join(str(domain) for domain in attention_case.get('unexpected_observed_domains', [])))}",
        f"linked_item={quote_plus(str(attention_case.get('case_id', '')))}",
    ]
    return f"annotations.html?{'&'.join(query_parts)}"



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
    approval_lifecycle_view_model: dict[str, Any] | None = None,
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
    approval_lifecycle_view_model = approval_lifecycle_view_model or {}
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
                    'target_href': 'readiness.html',
                }
            )
        if country_gap_rows:
            top_gap = country_gap_rows[0]
            gap_country = str(top_gap.get('country_id', 'UNKNOWN'))
            missing_domains = [str(domain) for domain in top_gap.get('missing_domains', []) if str(domain)]
            source_items.append(
                {
                    'category': 'country_gap',
                    'title': f"Country gap: {gap_country} missing {', '.join(missing_domains) or 'unknown domains'}",
                    'why_it_matters': f"Country coverage is incomplete for {gap_country}.",
                    'recommended_next_check': 'Inspect coverage.html and the country/domain gap details.',
                    'evidence_source': 'system_status.json country_coverage_visibility.country_gap_rows',
                    'target_page': 'coverage.html',
                    'target_href': _coverage_prefill_href(country_id=gap_country, focus_section='country_gap', missing_domains=missing_domains),
                }
            )
        validation_summary = validation_view_model.get('historical_replay_summary', {}) if isinstance(validation_view_model, dict) else {}
        attention_cases = [item for item in validation_summary.get('attention_cases', []) if isinstance(item, dict)] if isinstance(validation_summary, dict) else []
        if attention_cases:
            top_case = attention_cases[0]
            annotation_type, decision_posture = _annotation_type_and_decision_posture(attention_case=top_case)
            source_items.append(
                {
                    'category': 'validation_attention',
                    'title': f"Validation attention: {top_case.get('case_id', 'unknown')}",
                    'why_it_matters': f"{top_case.get('country_id', 'unknown')} needs review because {top_case.get('attention_reason', 'validation_attention')}.",
                    'recommended_next_check': str(top_case.get('suggested_next_action', 'Review validation evidence.')),
                    'evidence_source': 'validation_backtest.json historical_replay_summary.attention_cases',
                    'target_page': 'validation.html',
                    'target_href': _validation_prefill_href(
                        country_id=str(top_case.get('country_id', 'unknown')),
                        case_id=str(top_case.get('case_id', 'unknown')),
                        attention_reason=str(top_case.get('attention_reason', 'validation_attention')),
                    ),
                    'action_label': 'Create Annotation Draft',
                    'action_href': _annotation_prefill_href(attention_case=top_case),
                    'action_annotation_type': annotation_type,
                    'action_decision_posture': decision_posture,
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
                    'target_href': 'traceability.html',
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
                    'target_href': 'readiness.html',
                }
            )
        if stale_priority_watchlist:
            top_stale = stale_priority_watchlist[0]
            stale_country = str(top_stale.get('country_id', 'UNKNOWN'))
            source_items.append(
                {
                    'category': 'stale_priority',
                    'title': f"Stale priority: {stale_country}",
                    'why_it_matters': f"Priority {top_stale.get('priority', 'n/a')} country has {top_stale.get('freshness_hours', 'n/a')} stale hours.",
                    'recommended_next_check': 'Inspect stale coverage priority queue and remediation watchlist.',
                    'evidence_source': 'system_status.json country_coverage_visibility.stale_priority_watchlist',
                    'target_page': 'coverage.html',
                    'target_href': _coverage_prefill_href(country_id=stale_country, focus_section='stale_priority'),
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

    def _first_source_item_for(*categories: str) -> dict[str, Any]:
        return next(
            (item for item in source_items if str(item.get('category', '')) in categories),
            {},
        )

    top_coverage_item = _first_source_item_for('country_gap', 'stale_priority')
    top_validation_item = _first_source_item_for('validation_attention')
    top_traceability_item = _first_source_item_for('traceability_risk')
    top_validation_case = next(
        (
            item
            for item in _as_dict_list((validation_view_model.get('historical_replay_summary', {}) or {}).get('attention_cases', []))
            if isinstance(item, dict)
        ),
        {},
    )

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
    validation_focus_href = str(
        top_validation_item.get('target_href')
        or (
            _validation_prefill_href(
                country_id=str(top_validation_case.get('country_id', 'unknown')),
                case_id=str(top_validation_case.get('case_id', 'unknown')),
                attention_reason=str(top_validation_case.get('attention_reason') or top_validation_case.get('reason') or 'validation_attention'),
            )
            if top_validation_case
            else ''
        )
        or (
            _validation_prefill_href(
                country_id=str(validation_view_model.get('country_id', 'unknown')),
                case_id=str(validation_view_model.get('case_id', 'unknown')),
                attention_reason='validation_attention',
            )
            if validation_view_model.get('case_id')
            else ''
        )
        or 'validation.html'
    )
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
            'page_label': _page_label(_safe_navigation_page_name(str(source_items[0].get('target_href') or source_items[0].get('target_page', 'readiness.html')))),
            'page_name': _safe_navigation_page_name(str(source_items[0].get('target_href') or source_items[0].get('target_page', 'readiness.html'))),
            'objective': 'Inspect the highest-priority current review item first.',
            'reviewer_question': str(source_items[0].get('recommended_next_check', 'Inspect the primary review item.')),
            'expected_signal': str(source_items[0].get('title', 'n/a')),
            'available': _safe_navigation_page_name(str(source_items[0].get('target_href') or source_items[0].get('target_page', ''))) in available_pages,
            'href': str(source_items[0].get('target_href') or source_items[0].get('target_page', '')) if _safe_navigation_page_name(str(source_items[0].get('target_href') or source_items[0].get('target_page', ''))) in available_pages else '',
            'action_label': source_items[0].get('action_label'),
            'action_href': source_items[0].get('action_href') if _safe_navigation_page_name(str(source_items[0].get('action_href') or '')) in available_pages else '',
        },
        {
            'step_id': 'C3-03',
            'phase': 'Coverage posture',
            'page_label': _page_label(_safe_navigation_page_name(str(top_coverage_item.get('target_href') or 'coverage.html'))),
            'page_name': _safe_navigation_page_name(str(top_coverage_item.get('target_href') or 'coverage.html')),
            'objective': 'Check whether geographic/source coverage gaps undermine stakeholder confidence.',
            'reviewer_question': 'Do coverage gaps or stale-priority queues change the interpretation of the current package?',
            'expected_signal': 'country gaps and stale-priority cues are explicit and bounded',
            'available': _safe_navigation_page_name(str(top_coverage_item.get('target_href') or 'coverage.html')) in available_pages,
            'href': str(top_coverage_item.get('target_href') or 'coverage.html') if _safe_navigation_page_name(str(top_coverage_item.get('target_href') or 'coverage.html')) in available_pages else '',
        },
        {
            'step_id': 'C3-04',
            'phase': 'Validation posture',
            'page_label': _page_label(_safe_navigation_page_name(validation_focus_href)),
            'page_name': _safe_navigation_page_name(validation_focus_href),
            'objective': 'Verify whether replay-attention evidence supports or weakens the current storyline.',
            'reviewer_question': 'Which replay-attention slice most directly challenges the current package conclusion?',
            'expected_signal': 'attention cases, verdict mix, and replay evidence tier stay visible',
            'available': _safe_navigation_page_name(validation_focus_href) in available_pages,
            'href': validation_focus_href if _safe_navigation_page_name(validation_focus_href) in available_pages else '',
            'action_label': top_validation_item.get('action_label'),
            'action_href': str(top_validation_item.get('action_href') or '') if _safe_navigation_page_name(str(top_validation_item.get('action_href') or '')) in available_pages else '',
        },
        {
            'step_id': 'C3-05',
            'phase': 'Traceability posture',
            'page_label': _page_label(_safe_navigation_page_name(str(top_traceability_item.get('target_href') or 'traceability.html'))),
            'page_name': _safe_navigation_page_name(str(top_traceability_item.get('target_href') or 'traceability.html')),
            'objective': 'Confirm that the stakeholder narrative is still anchored in traceable governed evidence.',
            'reviewer_question': 'Are there traceability or closure-at-risk signals that would block sign-off?',
            'expected_signal': 'lineage, repo closure, and mapping-health evidence are reviewable',
            'available': _safe_navigation_page_name(str(top_traceability_item.get('target_href') or 'traceability.html')) in available_pages,
            'href': str(top_traceability_item.get('target_href') or 'traceability.html') if _safe_navigation_page_name(str(top_traceability_item.get('target_href') or 'traceability.html')) in available_pages else '',
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
    strongest_evidence_points = [
        f"Release verdict={release_verdict}",
        f"Gate verdict={gate_verdict}",
        f"Demo verdict={demo_verdict}",
        f"Primary focus={source_items[0].get('title', 'n/a')}",
    ]
    top_blockers = [str(item.get('title', 'n/a')) for item in source_items if str(item.get('category', '')) == 'release_blocker']
    if not top_blockers:
        top_blockers = [str(item.get('title', 'n/a')) for item in source_items[:2]]
    explicit_limitations = []
    if system_status_read_model.get('data_gaps'):
        explicit_limitations.append('data_gaps=' + ', '.join(str(item) for item in system_status_read_model.get('data_gaps', [])))
    if readiness_view_model.get('known_gaps'):
        explicit_limitations.append('known_gaps=' + ', '.join(str(item) for item in readiness_view_model.get('known_gaps', [])))
    if not explicit_limitations:
        explicit_limitations.append('No explicit known gaps recorded in the current package inputs.')
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
    executive_decision_summary = {
        'recommendation': 'go' if package_status == 'ready' else ('conditional_go' if package_status == 'attention' else 'no_go'),
        'decision_confidence': 'bounded' if explicit_limitations else 'high',
        'decision_basis': 'release/gate/demo verdicts plus prioritized review items',
        'review_completion_signal': review_sequence[-1].get('phase', 'artifact handoff'),
        'top_blockers': top_blockers,
        'strongest_evidence_points': strongest_evidence_points,
        'explicit_limitations': explicit_limitations,
    }
    lifecycle_status = approval_lifecycle_view_model.get('lifecycle_status', {}) if isinstance(approval_lifecycle_view_model, dict) else {}
    lifecycle_decision_status = str(approval_lifecycle_view_model.get('decision_status') or 'pending_signoff')
    lifecycle_state = str(approval_lifecycle_view_model.get('lifecycle_state') or lifecycle_decision_status)
    lifecycle_reviewer_role = str(
        approval_lifecycle_view_model.get('reviewer_role')
        or ('management' if package_status in {'ready', 'attention'} else 'operator')
    )
    lifecycle_distributed = bool(approval_lifecycle_view_model.get('distributed', False))
    lifecycle_distribution_recipients = [
        str(item) for item in approval_lifecycle_view_model.get('distribution_recipients', []) if str(item)
    ] if isinstance(approval_lifecycle_view_model.get('distribution_recipients', []), list) else []
    lifecycle_distribution_bundle_artifacts = [
        str(item) for item in approval_lifecycle_view_model.get('distribution_bundle_artifacts', []) if str(item)
    ] if isinstance(approval_lifecycle_view_model.get('distribution_bundle_artifacts', []), list) else []
    lifecycle_distribution_note = str(approval_lifecycle_view_model.get('distribution_record_note') or '').strip()
    signoff_readiness = (
        'distribution_completed'
        if lifecycle_distributed or lifecycle_state == 'distributed'
        else (
            'decision_recorded'
            if lifecycle_decision_status in {'approved', 'approved_with_conditions'}
            else (
                'review_deferred'
                if lifecycle_decision_status == 'deferred'
                else ('review_rejected' if lifecycle_decision_status == 'rejected' else ('ready_for_review' if package_status in {'ready', 'attention'} else 'blocked_for_signoff'))
            )
        )
    )
    canonical_handoff_artifact = 'release_package.html' if 'release_package.html' in available_pages else 'reports.html'
    share_now = lifecycle_distribution_bundle_artifacts or [
        item for item in ['release_package.html', 'release_demo_package.json', 'reports.html'] if item in available_pages or item.endswith('.json')
    ]
    follow_up_decision_template = _build_follow_up_decision_template(
        annotation_type=str(source_items[0].get('action_annotation_type') or ''),
        decision_posture=str(source_items[0].get('action_decision_posture') or ''),
    )
    _fut_checklist = follow_up_decision_template.get('checklist', [])
    decision_log_auto_seed = {
        'decision_focus': follow_up_decision_template.get('decision_focus', 'n/a'),
        'recommended_disposition': follow_up_decision_template.get('recommended_disposition', 'n/a'),
        'reviewer_prompt': follow_up_decision_template.get('reviewer_prompt', 'n/a'),
        'primary_focus': source_items[0].get('title', 'n/a'),
        'annotation_type': str(source_items[0].get('action_annotation_type') or ''),
        'decision_posture': str(source_items[0].get('action_decision_posture') or ''),
        'pre_filled_rationale': (
            str(follow_up_decision_template.get('reviewer_prompt', ''))
            + (' — ' + str(_fut_checklist[0]) if _fut_checklist else '')
        ),
        'pre_filled_conditions': [str(item) for item in _fut_checklist[1:]] if len(_fut_checklist) > 1 else [],
    }
    reviewer_handoff_summary = {
        'next_reviewer_role': 'project_lead' if package_status in {'ready', 'attention'} else 'operator',
        'canonical_handoff_artifact': canonical_handoff_artifact,
        'secondary_artifacts': share_now,
        'share_now': share_now,
        'primary_follow_up_action_label': source_items[0].get('action_label'),
        'primary_follow_up_action_href': source_items[0].get('action_href'),
        'primary_follow_up_action_annotation_type': source_items[0].get('action_annotation_type') or '',
        'primary_follow_up_action_decision_posture': source_items[0].get('action_decision_posture') or '',
        'decision_log_seed': {
            'package_status': package_status,
            'recommendation': executive_decision_summary['recommendation'],
            'primary_focus': source_items[0].get('title', 'n/a'),
            'next_check': source_items[0].get('recommended_next_check', 'n/a'),
            'primary_follow_up_action_label': source_items[0].get('action_label') or '',
            'primary_follow_up_action_href': source_items[0].get('action_href') or '',
            'primary_follow_up_action_annotation_type': source_items[0].get('action_annotation_type') or '',
            'primary_follow_up_action_decision_posture': source_items[0].get('action_decision_posture') or '',
            'decision_log_auto_seed': decision_log_auto_seed,
        },
    }
    review_signoff_scaffold = {
        'reviewer_role': reviewer_handoff_summary['next_reviewer_role'],
        'decision_status': lifecycle_decision_status,
        'decision_date_utc': str(approval_lifecycle_view_model.get('decision_date_utc') or ''),
        'bounded_rationale': [
            f"Recommendation={executive_decision_summary['recommendation']}",
            f"Confidence={executive_decision_summary['decision_confidence']}",
            f"Primary focus={source_items[0].get('title', 'n/a')}",
        ],
        'follow_up_actions': [
            str(source_items[0].get('recommended_next_check', 'Review the primary package item.')),
            (
                'Distribution already recorded; verify recipients and archive the lifecycle outcome.'
                if lifecycle_distributed or lifecycle_state == 'distributed'
                else (
                    'Resolve approval conditions, then proceed with controlled distribution.'
                    if lifecycle_decision_status == 'approved_with_conditions'
                    else (
                        'Re-open review once deferred conditions are resolved.'
                        if lifecycle_decision_status == 'deferred'
                        else (
                            'Address rejection rationale before re-initiating review.'
                            if lifecycle_decision_status == 'rejected'
                            else 'Record reviewer decision and date before external distribution.'
                        )
                    )
                )
            ),
        ],
        'primary_follow_up_action_label': source_items[0].get('action_label'),
        'primary_follow_up_action_href': source_items[0].get('action_href'),
        'primary_follow_up_action_annotation_type': source_items[0].get('action_annotation_type') or '',
        'primary_follow_up_action_decision_posture': source_items[0].get('action_decision_posture') or '',
        'follow_up_decision_template': follow_up_decision_template,
        'signoff_readiness': signoff_readiness,
    }
    approval_state = {
        'package_status': package_status,
        'recommendation': executive_decision_summary['recommendation'],
        'lifecycle_state': lifecycle_state,
        'decision_status': review_signoff_scaffold['decision_status'],
        'signoff_readiness': review_signoff_scaffold['signoff_readiness'],
        'reviewer_role': review_signoff_scaffold['reviewer_role'],
        'distributed': lifecycle_distributed,
        'distribution_date_utc': str(approval_lifecycle_view_model.get('distribution_date_utc') or ''),
        'distribution_recipients': lifecycle_distribution_recipients,
    }
    stakeholder_cover_sheet = {
        'audience': 'management / external stakeholder reviewer',
        'requested_decision': (
            'Package distribution is already recorded; confirm the governed recipients and archive outcome evidence.'
            if lifecycle_distributed or lifecycle_state == 'distributed'
            else (
                'Resolve explicit approval conditions before stakeholder distribution proceeds.'
                if lifecycle_decision_status == 'approved_with_conditions'
                else (
                    'Approve external review handoff and proceed with stakeholder walkthrough.'
                    if package_status in {'ready', 'attention'}
                    else 'Do not distribute externally until the blocking package issue is resolved.'
                )
            )
        ),
        'top_3_caveats': (top_blockers + explicit_limitations)[:3] or ['No explicit caveats recorded.'],
        'start_here': {
            'page_name': _safe_navigation_page_name(str(source_items[0].get('target_href') or source_items[0].get('target_page', review_sequence[0].get('page_name', 'readiness.html')))),
            'page_label': _page_label(_safe_navigation_page_name(str(source_items[0].get('target_href') or source_items[0].get('target_page', review_sequence[0].get('page_name', 'readiness.html'))))),
            'href': str(source_items[0].get('target_href') or source_items[0].get('target_page', review_sequence[0].get('href', 'readiness.html'))),
            'reason': str(source_items[0].get('recommended_next_check') or 'Inspect the highest-priority current review item first.'),
            'action_label': source_items[0].get('action_label'),
            'action_href': source_items[0].get('action_href') or '',
        },
        'external_share_summary': {
            'recommendation': executive_decision_summary['recommendation'],
            'package_status': package_status,
            'decision_status': approval_state['decision_status'],
            'canonical_artifact': reviewer_handoff_summary['canonical_handoff_artifact'],
            'supporting_artifacts': reviewer_handoff_summary['share_now'],
            'distribution_recipients': lifecycle_distribution_recipients,
            'distribution_note': lifecycle_distribution_note,
            'primary_focus': source_items[0].get('title', 'n/a'),
            'primary_follow_up_action_label': source_items[0].get('action_label') or '',
            'primary_follow_up_action_href': source_items[0].get('action_href') or '',
            'primary_follow_up_action_annotation_type': source_items[0].get('action_annotation_type') or '',
            'primary_follow_up_action_decision_posture': source_items[0].get('action_decision_posture') or '',
        },
    }
    reviewer_handoff_summary['decision_log_seed'].update(
        {
            'decision_status': approval_state['decision_status'],
            'signoff_readiness': approval_state['signoff_readiness'],
            'reviewer_role': approval_state['reviewer_role'],
            'requested_decision': stakeholder_cover_sheet['requested_decision'],
        }
    )
    decision_log_export_summary = {
        'approval_state': approval_state,
        'requested_decision_linkage': {
            'requested_decision': stakeholder_cover_sheet['requested_decision'],
            'recommendation': executive_decision_summary['recommendation'],
            'decision_status': approval_state['decision_status'],
            'primary_follow_up_action_label': source_items[0].get('action_label') or '',
            'primary_follow_up_action_href': source_items[0].get('action_href') or '',
            'primary_follow_up_action_annotation_type': source_items[0].get('action_annotation_type') or '',
            'primary_follow_up_action_decision_posture': source_items[0].get('action_decision_posture') or '',
        },
        'distribution_bundle': reviewer_handoff_summary['share_now'],
        'decision_entry_template': {
            'package_status': approval_state['package_status'],
            'decision_status': approval_state['decision_status'],
            'reviewer_role': approval_state['reviewer_role'],
            'requested_decision': stakeholder_cover_sheet['requested_decision'],
            'primary_focus': source_items[0].get('title', 'n/a'),
            'canonical_artifact': reviewer_handoff_summary['canonical_handoff_artifact'],
            'primary_follow_up_action_label': source_items[0].get('action_label') or '',
            'primary_follow_up_action_href': source_items[0].get('action_href') or '',
            'primary_follow_up_action_annotation_type': source_items[0].get('action_annotation_type') or '',
            'primary_follow_up_action_decision_posture': source_items[0].get('action_decision_posture') or '',
        },
    }
    reviewer_disposition_standard = {
        'disposition_options': ['approve', 'approve_with_conditions', 'defer', 'reject'],
        'selected_disposition': (
            'approve'
            if lifecycle_decision_status in {'approved', 'distributed'}
            else (
                'approve_with_conditions'
                if lifecycle_decision_status == 'approved_with_conditions'
                else (
                    'defer'
                    if lifecycle_decision_status == 'deferred'
                    else ('reject' if lifecycle_decision_status == 'rejected' else ('approve' if package_status == 'ready' else ('approve_with_conditions' if package_status == 'attention' else 'defer')))
                )
            )
        ),
        'disposition_rationale_bounds': [
            'State the decision in one of the standard disposition categories only.',
            'Bound rationale to the current package evidence, top caveats, and explicit follow-up conditions.',
        ],
        'follow_up_owner': approval_state['reviewer_role'],
    }
    disposition_action_routing = {
        'route_trigger': reviewer_disposition_standard['selected_disposition'],
        'primary_action_bundle': (
            ['Distribute canonical release package.', 'Record approval decision in decision log.']
            if reviewer_disposition_standard['selected_disposition'] == 'approve'
            else (
                ['Record conditions explicitly.', 'Assign follow-up checks before external distribution.']
                if reviewer_disposition_standard['selected_disposition'] == 'approve_with_conditions'
                else ['Hold external distribution.', 'Re-run the highest-priority follow-up check before review resumes.']
            )
        ),
        'primary_follow_up_action_label': source_items[0].get('action_label'),
        'primary_follow_up_action_href': source_items[0].get('action_href'),
        'primary_follow_up_action_annotation_type': source_items[0].get('action_annotation_type') or '',
        'primary_follow_up_action_decision_posture': source_items[0].get('action_decision_posture') or '',
        'follow_up_decision_template': follow_up_decision_template,
        'escalation_handoff_route': (
            'management -> stakeholder distribution'
            if reviewer_disposition_standard['selected_disposition'] == 'approve'
            else (
                'management -> operator follow-up -> stakeholder re-review'
                if reviewer_disposition_standard['selected_disposition'] == 'approve_with_conditions'
                else 'operator remediation -> management re-review'
            )
        ),
        'action_owner': reviewer_disposition_standard['follow_up_owner'],
    }
    decision_packet_seed = {
        'packet_headline': f"{executive_decision_summary['recommendation']} / {reviewer_disposition_standard['selected_disposition']} / {package_status}",
        'decision_snapshot': {
            'recommendation': executive_decision_summary['recommendation'],
            'selected_disposition': reviewer_disposition_standard['selected_disposition'],
            'decision_status': approval_state['decision_status'],
            'primary_focus': source_items[0].get('title', 'n/a'),
            'primary_follow_up_action_label': source_items[0].get('action_label') or '',
            'primary_follow_up_action_href': source_items[0].get('action_href') or '',
            'primary_follow_up_action_annotation_type': source_items[0].get('action_annotation_type') or '',
            'primary_follow_up_action_decision_posture': source_items[0].get('action_decision_posture') or '',
        },
        'share_now_packet': reviewer_handoff_summary['share_now'],
        'primary_follow_up_action_label': source_items[0].get('action_label'),
        'primary_follow_up_action_href': source_items[0].get('action_href'),
        'primary_follow_up_action_annotation_type': source_items[0].get('action_annotation_type') or '',
        'primary_follow_up_action_decision_posture': source_items[0].get('action_decision_posture') or '',
        'decision_packet_note': 'Export-ready seed for management/stakeholder forwarding; validate latest evidence before external send.',
        'decision_log_auto_seed': decision_log_auto_seed,
    }
    decision_packet_send_readiness = {
        'overall_send_readiness': (
            'already_distributed'
            if lifecycle_distributed or lifecycle_state == 'distributed'
            else (
                'ready_to_send'
                if package_status == 'ready' and approval_state['decision_status'] == 'approved'
                else ('internal_review_only' if package_status in {'ready', 'attention'} else 'blocked')
            )
        ),
        'external_send_allowed': (
            lifecycle_distributed
            or lifecycle_state == 'distributed'
            or (package_status == 'ready' and approval_state['decision_status'] == 'approved')
        ),
        'next_unblocker': (
            'Distribution outcome already recorded; archive the packet and confirm recipient traceability.'
            if lifecycle_distributed or lifecycle_state == 'distributed'
            else (
                'Capture explicit reviewer approval in the sign-off scaffold before external send.'
                if package_status in {'ready', 'attention'} and approval_state['decision_status'] != 'approved'
                else (
                    'Resolve the blocking package issue before any external distribution.'
                    if package_status == 'blocked'
                    else 'Packet may be distributed externally.'
                )
            )
        ),
        'follow_up_decision_template': follow_up_decision_template,
        'checklist_items': [
            {
                'item_id': 'gate_posture_green',
                'label': 'Release/gate posture is green',
                'status': 'pass' if release_green else 'block',
                'reason': f"release_green={release_green}",
            },
            {
                'item_id': 'reviewer_signoff_captured',
                'label': 'Reviewer sign-off is captured',
                'status': 'pass' if approval_state['decision_status'] in {'approved', 'approved_with_conditions', 'distributed'} else 'pending',
                'reason': f"decision_status={approval_state['decision_status']}",
            },
            {
                'item_id': 'canonical_packet_available',
                'label': 'Canonical packet artifact is available',
                'status': 'pass' if reviewer_handoff_summary['canonical_handoff_artifact'] in share_now else 'block',
                'reason': reviewer_handoff_summary['canonical_handoff_artifact'],
            },
            {
                'item_id': 'distribution_bundle_prepared',
                'label': 'Distribution bundle is prepared',
                'status': 'pass' if bool(reviewer_handoff_summary['share_now']) else 'block',
                'reason': ', '.join(reviewer_handoff_summary['share_now']) or 'none',
            },
            {
                'item_id': 'distribution_record_captured',
                'label': 'Distribution outcome is recorded when already sent',
                'status': 'pass' if not lifecycle_distributed or bool(lifecycle_distribution_recipients) else 'pending',
                'reason': (
                    ', '.join(lifecycle_distribution_recipients)
                    if lifecycle_distribution_recipients
                    else ('not_distributed' if not lifecycle_distributed else 'distribution recipients missing')
                ),
            },
            {
                'item_id': 'decision_scope_bounded',
                'label': 'Decision scope and caveats are bounded',
                'status': 'pass' if bool(executive_decision_summary['explicit_limitations']) else 'pending',
                'reason': '; '.join(executive_decision_summary['explicit_limitations']) or 'none',
            },
            {
                'item_id': 'follow_up_false_positive_rationale_recorded',
                'label': 'False-positive follow-up rationale is explicitly recorded before send',
                'status': (
                    'pending'
                    if follow_up_decision_template.get('decision_focus') == 'false_positive_review' and not lifecycle_distributed
                    else ('pass' if follow_up_decision_template.get('decision_focus') == 'false_positive_review' else 'n/a')
                ),
                'reason': (
                    str(follow_up_decision_template.get('reviewer_prompt', ''))
                    if follow_up_decision_template.get('decision_focus') == 'false_positive_review'
                    else 'not_applicable'
                ),
            },
        ],
    }

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
        'primary_item_target_href': source_items[0].get('target_href') or source_items[0].get('target_page'),
        'primary_item_next_check': source_items[0].get('recommended_next_check', 'n/a'),
        'primary_item_evidence_source': source_items[0].get('evidence_source', 'n/a'),
        'primary_item_action_label': source_items[0].get('action_label'),
        'primary_item_action_href': source_items[0].get('action_href'),
        'primary_item_action_annotation_type': source_items[0].get('action_annotation_type') or '',
        'primary_item_action_decision_posture': source_items[0].get('action_decision_posture') or '',
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
        'executive_decision_summary': executive_decision_summary,
        'reviewer_handoff_summary': reviewer_handoff_summary,
        'review_signoff_scaffold': review_signoff_scaffold,
        'approval_state': approval_state,
        'stakeholder_cover_sheet': stakeholder_cover_sheet,
        'decision_log_export_summary': decision_log_export_summary,
        'reviewer_disposition_standard': reviewer_disposition_standard,
        'disposition_action_routing': disposition_action_routing,
        'decision_packet_seed': decision_packet_seed,
        'decision_packet_send_readiness': decision_packet_send_readiness,
        'evidence_items': [{'label': label, 'value': value} for label, value in evidence_items],
        'available_pages': sorted(available_pages),
        'priority_target_pages': sorted({str(item.get('target_page', '')) for item in source_items if item.get('target_page')}),
        'source_item_pages': sorted({str(item.get('target_page', '')) for item in source_items if item.get('target_page')}),
        'readiness_view_model': {
            'demo_verdict': readiness_view_model.get('demo_verdict'),
            'release_verdict': readiness_view_model.get('release_verdict'),
            'release_readiness_percent': readiness_view_model.get('release_readiness_percent'),
        },
    }


def render_release_demo_package_body(view_model: dict[str, Any]) -> str:
    available_pages = {
        _safe_navigation_page_name(str(item))
        for item in view_model.get('available_pages', [])
        if str(item)
    }
    available_pages.update(
        _safe_navigation_page_name(str(item.get('page_name', '')))
        for item in _as_dict_list(view_model.get('demo_sequence'))
        if item.get('available')
    )
    priority_items = _as_dict_list(view_model.get('priority_items'))
    if not priority_items:
        priority_items = [{
            'rank': 1,
            'category': 'release_ready',
            'title': 'Release package ready for review',
            'why_it_matters': 'No blocking evidence remains in the current package.',
            'recommended_next_check': 'Proceed with the demo sequence.',
            'target_page': 'readiness.html',
            'target_href': 'readiness.html',
            'evidence_source': 'readiness.json',
        }]
    priority_rows = ''.join(
        '<tr>'
        f"<td>{html.escape(str(item.get('rank', '')))}</td>"
        f"<td>{html.escape(str(item.get('category', '')))}</td>"
        f"<td>{html.escape(str(item.get('title', '')))}</td>"
        f"<td>{html.escape(str(item.get('why_it_matters', '')))}</td>"
        f"<td>{html.escape(str(item.get('recommended_next_check', '')))}</td>"
        f"<td>{' | '.join(part for part in [
            _render_nav_link(href=item.get('target_href') or item.get('target_page'), label=str(item.get('target_page', '')), css_class='analyst-briefing-target-link', available_pages=available_pages),
            (_render_nav_link(href=item.get('action_href'), label=str(item.get('action_label', 'Open action')), css_class='analyst-briefing-action-link', available_pages=available_pages) if item.get('action_href') and item.get('action_label') else ''),
        ] if part)}</td>"
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
        f"<td>{' | '.join(part for part in [
            _render_nav_link(href=item.get('href') or item.get('page_name'), label=str(item.get('page_label', '')), css_class='analyst-briefing-target-link', available_pages=available_pages),
            (_render_nav_link(href=item.get('action_href'), label=str(item.get('action_label', 'Open action')), css_class='analyst-briefing-action-link', available_pages=available_pages) if item.get('action_href') and item.get('action_label') else ''),
        ] if part)}</td>"
        f"<td>{html.escape(str(item.get('objective', '')))}</td>"
        f"<td>{html.escape(str(item.get('reviewer_question', '')))}</td>"
        f"<td>{html.escape(str(item.get('expected_signal', '')))}</td>"
        f"<td>{html.escape('yes' if bool(item.get('available')) else 'no')}</td>"
        '</tr>'
        for item in _as_dict_list(view_model.get('review_sequence'))
    ) or "<tr><td colspan='7'>No guided review sequence available.</td></tr>"
    executive_summary = dict(view_model.get('executive_decision_summary', {})) if isinstance(view_model.get('executive_decision_summary'), dict) else {}
    executive_recommendation = html.escape(str(executive_summary.get('recommendation', 'n/a')))
    executive_confidence = html.escape(str(executive_summary.get('decision_confidence', 'n/a')))
    executive_basis = html.escape(str(executive_summary.get('decision_basis', 'n/a')))
    executive_completion_signal = html.escape(str(executive_summary.get('review_completion_signal', 'n/a')))
    executive_blockers = ''.join(f"<li>{html.escape(str(item))}</li>" for item in executive_summary.get('top_blockers', [])) or '<li>none</li>'
    executive_evidence = ''.join(f"<li>{html.escape(str(item))}</li>" for item in executive_summary.get('strongest_evidence_points', [])) or '<li>none</li>'
    executive_limitations = ''.join(f"<li>{html.escape(str(item))}</li>" for item in executive_summary.get('explicit_limitations', [])) or '<li>none</li>'
    handoff_summary = dict(view_model.get('reviewer_handoff_summary', {})) if isinstance(view_model.get('reviewer_handoff_summary'), dict) else {}
    handoff_next_reviewer = html.escape(str(handoff_summary.get('next_reviewer_role', 'n/a')))
    handoff_canonical_artifact = html.escape(str(handoff_summary.get('canonical_handoff_artifact', 'n/a')))
    handoff_share_now = ''.join(f"<li>{html.escape(str(item))}</li>" for item in handoff_summary.get('share_now', [])) or '<li>none</li>'
    handoff_primary_action_label = str(handoff_summary.get('primary_follow_up_action_label') or '').strip()
    handoff_primary_action_href = str(handoff_summary.get('primary_follow_up_action_href') or '').strip()
    handoff_primary_action_link = (
        _render_nav_link(
            href=handoff_primary_action_href,
            label=handoff_primary_action_label,
            css_class='analyst-briefing-action-link',
            available_pages=available_pages,
        )
        if handoff_primary_action_href and handoff_primary_action_label
        else ''
    )
    decision_log_seed = dict(handoff_summary.get('decision_log_seed', {})) if isinstance(handoff_summary.get('decision_log_seed'), dict) else {}
    decision_log_seed_html = ''.join(
        f"<li><strong>{html.escape(str(key))}</strong>: {html.escape(str(value))}</li>"
        for key, value in decision_log_seed.items()
        if key != 'decision_log_auto_seed'
    ) or '<li>none</li>'
    handoff_auto_seed = dict(decision_log_seed.get('decision_log_auto_seed', {})) if isinstance(decision_log_seed.get('decision_log_auto_seed'), dict) else {}
    handoff_auto_seed_html = ''
    if handoff_auto_seed:
        _has_conditions = ''.join(
            f"<li>{html.escape(str(c))}</li>" for c in handoff_auto_seed.get('pre_filled_conditions', [])
        )
        handoff_auto_seed_html = (
            "<div><strong>Decision-log auto-seed</strong><ul>"
            f"<li><strong>Decision focus</strong>: {html.escape(str(handoff_auto_seed.get('decision_focus', 'n/a')))}</li>"
            f"<li><strong>Recommended disposition</strong>: {html.escape(str(handoff_auto_seed.get('recommended_disposition', 'n/a')))}</li>"
            f"<li><strong>Annotation type</strong>: {html.escape(str(handoff_auto_seed.get('annotation_type', '')))}</li>"
            f"<li><strong>Pre-filled rationale</strong>: {html.escape(str(handoff_auto_seed.get('pre_filled_rationale', '')))}</li>"
            f"<li><strong>Pre-filled conditions</strong><ul>{_has_conditions or '<li>none</li>'}</ul></li>"
            "</ul></div>"
        )
    signoff_scaffold = dict(view_model.get('review_signoff_scaffold', {})) if isinstance(view_model.get('review_signoff_scaffold'), dict) else {}
    signoff_reviewer_role = html.escape(str(signoff_scaffold.get('reviewer_role', 'n/a')))
    signoff_decision_status = html.escape(str(signoff_scaffold.get('decision_status', 'n/a')))
    signoff_decision_date = html.escape(str(signoff_scaffold.get('decision_date_utc', '')) or 'pending')
    signoff_readiness = html.escape(str(signoff_scaffold.get('signoff_readiness', 'n/a')))
    signoff_rationale = ''.join(f"<li>{html.escape(str(item))}</li>" for item in signoff_scaffold.get('bounded_rationale', [])) or '<li>none</li>'
    signoff_followups = ''.join(f"<li>{html.escape(str(item))}</li>" for item in signoff_scaffold.get('follow_up_actions', [])) or '<li>none</li>'
    signoff_action_label = str(signoff_scaffold.get('primary_follow_up_action_label') or '').strip()
    signoff_action_href = str(signoff_scaffold.get('primary_follow_up_action_href') or '').strip()
    signoff_action_annotation_type = html.escape(str(signoff_scaffold.get('primary_follow_up_action_annotation_type', '')))
    signoff_action_decision_posture = html.escape(str(signoff_scaffold.get('primary_follow_up_action_decision_posture', '')))
    signoff_decision_template_html = _render_follow_up_decision_template_html(
        dict(signoff_scaffold.get('follow_up_decision_template', {})) if isinstance(signoff_scaffold.get('follow_up_decision_template'), dict) else {}
    )
    signoff_action_link = (
        _render_nav_link(
            href=signoff_action_href,
            label=signoff_action_label,
            css_class='analyst-briefing-action-link',
            available_pages=available_pages,
        )
        if signoff_action_href and signoff_action_label
        else ''
    )
    stakeholder_cover_sheet = dict(view_model.get('stakeholder_cover_sheet', {})) if isinstance(view_model.get('stakeholder_cover_sheet'), dict) else {}
    cover_sheet_audience = html.escape(str(stakeholder_cover_sheet.get('audience', 'n/a')))
    cover_sheet_requested_decision = html.escape(str(stakeholder_cover_sheet.get('requested_decision', 'n/a')))
    cover_sheet_top_caveats = ''.join(f"<li>{html.escape(str(item))}</li>" for item in stakeholder_cover_sheet.get('top_3_caveats', [])) or '<li>none</li>'
    cover_sheet_start_here = dict(stakeholder_cover_sheet.get('start_here', {})) if isinstance(stakeholder_cover_sheet.get('start_here'), dict) else {}
    cover_sheet_start_here_label = html.escape(str(cover_sheet_start_here.get('page_label', 'n/a')))
    cover_sheet_start_here_page = html.escape(str(cover_sheet_start_here.get('page_name', 'n/a')))
    cover_sheet_start_here_href = str(cover_sheet_start_here.get('href') or cover_sheet_start_here.get('page_name') or '').strip()
    cover_sheet_start_here_reason = html.escape(str(cover_sheet_start_here.get('reason', 'n/a')))
    cover_sheet_start_here_action_label = str(cover_sheet_start_here.get('action_label') or '').strip()
    cover_sheet_start_here_action_href = str(cover_sheet_start_here.get('action_href') or '').strip()
    external_share_summary = dict(stakeholder_cover_sheet.get('external_share_summary', {})) if isinstance(stakeholder_cover_sheet.get('external_share_summary'), dict) else {}
    external_share_action_label = str(external_share_summary.get('primary_follow_up_action_label') or '').strip()
    external_share_action_href = str(external_share_summary.get('primary_follow_up_action_href') or '').strip()
    external_share_action_annotation_type = html.escape(str(external_share_summary.get('primary_follow_up_action_annotation_type', '')))
    external_share_action_decision_posture = html.escape(str(external_share_summary.get('primary_follow_up_action_decision_posture', '')))
    external_share_action_link = (
        _render_nav_link(
            href=external_share_action_href,
            label=external_share_action_label,
            css_class='analyst-briefing-action-link',
            available_pages=available_pages,
        )
        if external_share_action_href and external_share_action_label
        else ''
    )
    external_share_summary_html = ''.join(
        f"<li><strong>{html.escape(str(key).replace('_', ' ').title())}</strong>: {html.escape(str(value))}</li>"
        for key, value in external_share_summary.items()
        if key not in {
            'primary_follow_up_action_label',
            'primary_follow_up_action_href',
            'primary_follow_up_action_annotation_type',
            'primary_follow_up_action_decision_posture',
        }
    ) or '<li>none</li>'
    decision_log_export_summary = dict(view_model.get('decision_log_export_summary', {})) if isinstance(view_model.get('decision_log_export_summary'), dict) else {}
    approval_state = dict(decision_log_export_summary.get('approval_state', {})) if isinstance(decision_log_export_summary.get('approval_state'), dict) else {}
    approval_state_html = ''.join(
        f"<li><strong>{html.escape(str(key).replace('_', ' ').title())}</strong>: {html.escape(str(value))}</li>"
        for key, value in approval_state.items()
    ) or '<li>none</li>'
    requested_decision_linkage = dict(decision_log_export_summary.get('requested_decision_linkage', {})) if isinstance(decision_log_export_summary.get('requested_decision_linkage'), dict) else {}
    requested_decision_action_label = str(requested_decision_linkage.get('primary_follow_up_action_label') or '').strip()
    requested_decision_action_href = str(requested_decision_linkage.get('primary_follow_up_action_href') or '').strip()
    requested_decision_action_annotation_type = html.escape(str(requested_decision_linkage.get('primary_follow_up_action_annotation_type', '')))
    requested_decision_action_decision_posture = html.escape(str(requested_decision_linkage.get('primary_follow_up_action_decision_posture', '')))
    requested_decision_action_link = (
        _render_nav_link(
            href=requested_decision_action_href,
            label=requested_decision_action_label,
            css_class='analyst-briefing-action-link',
            available_pages=available_pages,
        )
        if requested_decision_action_href and requested_decision_action_label
        else ''
    )
    requested_decision_linkage_html = ''.join(
        f"<li><strong>{html.escape(str(key).replace('_', ' ').title())}</strong>: {html.escape(str(value))}</li>"
        for key, value in requested_decision_linkage.items()
        if key not in {
            'primary_follow_up_action_label',
            'primary_follow_up_action_href',
            'primary_follow_up_action_annotation_type',
            'primary_follow_up_action_decision_posture',
        }
    ) or '<li>none</li>'
    distribution_bundle_html = ''.join(
        f"<li>{html.escape(str(item))}</li>" for item in decision_log_export_summary.get('distribution_bundle', [])
    ) or '<li>none</li>'
    decision_entry_template = dict(decision_log_export_summary.get('decision_entry_template', {})) if isinstance(decision_log_export_summary.get('decision_entry_template'), dict) else {}
    decision_entry_action_label = str(decision_entry_template.get('primary_follow_up_action_label') or '').strip()
    decision_entry_action_href = str(decision_entry_template.get('primary_follow_up_action_href') or '').strip()
    decision_entry_action_annotation_type = html.escape(str(decision_entry_template.get('primary_follow_up_action_annotation_type', '')))
    decision_entry_action_decision_posture = html.escape(str(decision_entry_template.get('primary_follow_up_action_decision_posture', '')))
    decision_entry_action_link = (
        _render_nav_link(
            href=decision_entry_action_href,
            label=decision_entry_action_label,
            css_class='analyst-briefing-action-link',
            available_pages=available_pages,
        )
        if decision_entry_action_href and decision_entry_action_label
        else ''
    )
    decision_entry_template_html = ''.join(
        f"<li><strong>{html.escape(str(key).replace('_', ' ').title())}</strong>: {html.escape(str(value))}</li>"
        for key, value in decision_entry_template.items()
        if key not in {
            'primary_follow_up_action_label',
            'primary_follow_up_action_href',
            'primary_follow_up_action_annotation_type',
            'primary_follow_up_action_decision_posture',
        }
    ) or '<li>none</li>'
    reviewer_disposition_standard = dict(view_model.get('reviewer_disposition_standard', {})) if isinstance(view_model.get('reviewer_disposition_standard'), dict) else {}
    disposition_options_html = ''.join(
        f"<li>{html.escape(str(item))}</li>" for item in reviewer_disposition_standard.get('disposition_options', [])
    ) or '<li>none</li>'
    selected_disposition = html.escape(str(reviewer_disposition_standard.get('selected_disposition', 'n/a')))
    disposition_rationale_bounds_html = ''.join(
        f"<li>{html.escape(str(item))}</li>" for item in reviewer_disposition_standard.get('disposition_rationale_bounds', [])
    ) or '<li>none</li>'
    follow_up_owner = html.escape(str(reviewer_disposition_standard.get('follow_up_owner', 'n/a')))
    disposition_action_routing = dict(view_model.get('disposition_action_routing', {})) if isinstance(view_model.get('disposition_action_routing'), dict) else {}
    route_trigger = html.escape(str(disposition_action_routing.get('route_trigger', 'n/a')))
    primary_action_bundle_html = ''.join(
        f"<li>{html.escape(str(item))}</li>" for item in disposition_action_routing.get('primary_action_bundle', [])
    ) or '<li>none</li>'
    routing_action_label = str(disposition_action_routing.get('primary_follow_up_action_label') or '').strip()
    routing_action_href = str(disposition_action_routing.get('primary_follow_up_action_href') or '').strip()
    routing_action_annotation_type = html.escape(str(disposition_action_routing.get('primary_follow_up_action_annotation_type', '')))
    routing_action_decision_posture = html.escape(str(disposition_action_routing.get('primary_follow_up_action_decision_posture', '')))
    routing_decision_template_html = _render_follow_up_decision_template_html(
        dict(disposition_action_routing.get('follow_up_decision_template', {})) if isinstance(disposition_action_routing.get('follow_up_decision_template'), dict) else {}
    )
    routing_action_link = (
        _render_nav_link(
            href=routing_action_href,
            label=routing_action_label,
            css_class='analyst-briefing-action-link',
            available_pages=available_pages,
        )
        if routing_action_href and routing_action_label
        else ''
    )
    escalation_handoff_route = html.escape(str(disposition_action_routing.get('escalation_handoff_route', 'n/a')))
    action_owner = html.escape(str(disposition_action_routing.get('action_owner', 'n/a')))
    decision_packet_seed = dict(view_model.get('decision_packet_seed', {})) if isinstance(view_model.get('decision_packet_seed'), dict) else {}
    packet_headline = html.escape(str(decision_packet_seed.get('packet_headline', 'n/a')))
    decision_snapshot = dict(decision_packet_seed.get('decision_snapshot', {})) if isinstance(decision_packet_seed.get('decision_snapshot'), dict) else {}
    decision_snapshot_html = ''.join(
        f"<li><strong>{html.escape(str(key).replace('_', ' ').title())}</strong>: {html.escape(str(value))}</li>"
        for key, value in decision_snapshot.items()
    ) or '<li>none</li>'
    share_now_packet_html = ''.join(
        f"<li>{html.escape(str(item))}</li>" for item in decision_packet_seed.get('share_now_packet', [])
    ) or '<li>none</li>'
    decision_packet_primary_action_label = str(decision_packet_seed.get('primary_follow_up_action_label') or '').strip()
    decision_packet_primary_action_href = str(decision_packet_seed.get('primary_follow_up_action_href') or '').strip()
    decision_packet_primary_action_annotation_type = html.escape(str(decision_packet_seed.get('primary_follow_up_action_annotation_type', '')))
    decision_packet_primary_action_decision_posture = html.escape(str(decision_packet_seed.get('primary_follow_up_action_decision_posture', '')))
    decision_packet_primary_action_link = (
        _render_nav_link(
            href=decision_packet_primary_action_href,
            label=decision_packet_primary_action_label,
            css_class='analyst-briefing-action-link',
            available_pages=available_pages,
        )
        if decision_packet_primary_action_href and decision_packet_primary_action_label
        else ''
    )
    decision_packet_note = html.escape(str(decision_packet_seed.get('decision_packet_note', 'n/a')))
    packet_auto_seed = dict(decision_packet_seed.get('decision_log_auto_seed', {})) if isinstance(decision_packet_seed.get('decision_log_auto_seed'), dict) else {}
    packet_auto_seed_html = ''
    if packet_auto_seed:
        _pac_conditions = ''.join(
            f"<li>{html.escape(str(c))}</li>" for c in packet_auto_seed.get('pre_filled_conditions', [])
        )
        packet_auto_seed_html = (
            "<div><strong>Decision-log auto-seed</strong><ul>"
            f"<li><strong>Decision focus</strong>: {html.escape(str(packet_auto_seed.get('decision_focus', 'n/a')))}</li>"
            f"<li><strong>Recommended disposition</strong>: {html.escape(str(packet_auto_seed.get('recommended_disposition', 'n/a')))}</li>"
            f"<li><strong>Annotation type</strong>: {html.escape(str(packet_auto_seed.get('annotation_type', '')))}</li>"
            f"<li><strong>Pre-filled rationale</strong>: {html.escape(str(packet_auto_seed.get('pre_filled_rationale', '')))}</li>"
            f"<li><strong>Pre-filled conditions</strong><ul>{_pac_conditions or '<li>none</li>'}</ul></li>"
            "</ul></div>"
        )
    decision_packet_send_readiness = dict(view_model.get('decision_packet_send_readiness', {})) if isinstance(view_model.get('decision_packet_send_readiness'), dict) else {}
    packet_send_readiness = html.escape(str(decision_packet_send_readiness.get('overall_send_readiness', 'n/a')))
    packet_external_send_allowed = html.escape('yes' if bool(decision_packet_send_readiness.get('external_send_allowed')) else 'no')
    packet_next_unblocker = html.escape(str(decision_packet_send_readiness.get('next_unblocker', 'n/a')))
    packet_follow_up_decision_template_html = _render_follow_up_decision_template_html(
        dict(decision_packet_send_readiness.get('follow_up_decision_template', {})) if isinstance(decision_packet_send_readiness.get('follow_up_decision_template'), dict) else {}
    )
    packet_send_checklist_rows = ''.join(
        '<tr>'
        f"<td>{html.escape(str(item.get('item_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('label', '')))}</td>"
        f"<td>{html.escape(str(item.get('status', '')))}</td>"
        f"<td>{html.escape(str(item.get('reason', '')))}</td>"
        '</tr>'
        for item in _as_dict_list(decision_packet_send_readiness.get('checklist_items'))
    ) or "<tr><td colspan='4'>No send-readiness checklist available.</td></tr>"
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
    primary_target_href = str(view_model.get('primary_item_target_href') or view_model.get('primary_item_target_page') or '').strip()
    primary_action_label = str(view_model.get('primary_item_action_label') or '').strip()
    primary_action_href = str(view_model.get('primary_item_action_href') or '').strip()
    primary_action_annotation_type = html.escape(str(view_model.get('primary_item_action_annotation_type', '')))
    primary_action_decision_posture = html.escape(str(view_model.get('primary_item_action_decision_posture', '')))
    package_name = html.escape(str(view_model.get('package_name', 'Release / Demo Package')))
    generated_at = html.escape(str(view_model.get('generated_at_utc', 'n/a')))

    primary_target_link = _render_nav_link(
        href=primary_target_href,
        label=str(view_model.get('primary_item_target_page', 'n/a')),
        css_class='analyst-briefing-target-link',
        available_pages=available_pages,
    )
    primary_action_link = (
        _render_nav_link(
            href=primary_action_href,
            label=primary_action_label,
            css_class='analyst-briefing-action-link',
            available_pages=available_pages,
        )
        if primary_action_href and primary_action_label
        else ''
    )

    return (
        "<section class='panel'>"
        f"<div class='panel-header'>{package_name}</div>"
        f"<p><strong>Package status:</strong> {status} · <strong>Release verdict:</strong> {release_verdict} · <strong>Demo verdict:</strong> {demo_verdict} · <strong>Gate verdict:</strong> {gate_verdict}</p>"
        f"<p><strong>Primary focus:</strong> {primary_focus}</p>"
        f"<p><strong>Next check:</strong> {primary_next_check}</p>"
        f"<p><strong>Primary target page:</strong> {primary_target_link}"
        + (f" · <strong>Primary action:</strong> {primary_action_link}" if primary_action_link else "")
        + "</p>"
        + (f"<p><strong>Follow-up annotation type:</strong> {primary_action_annotation_type}</p>" if primary_action_annotation_type else "")
        + (f"<p><strong>Follow-up decision posture:</strong> {primary_action_decision_posture}</p>" if primary_action_decision_posture else "")
        + f"<p><strong>Generated:</strong> {generated_at}</p>"
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
        "<div class='table-wrap'><table><thead><tr><th>Step</th><th>Phase</th><th>Page / action</th><th>Objective</th><th>Reviewer question</th><th>Expected signal</th><th>Available</th></tr></thead><tbody>"
        f"{review_rows}"
        "</tbody></table></div>"
        "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Executive decision summary</div>"
        f"<p><strong>Recommendation:</strong> {executive_recommendation} · <strong>Decision confidence:</strong> {executive_confidence}</p>"
        f"<p><strong>Decision basis:</strong> {executive_basis}</p>"
        f"<p><strong>Review completion signal:</strong> {executive_completion_signal}</p>"
        f"<div><strong>Top blockers</strong><ul>{executive_blockers}</ul></div>"
        f"<div><strong>Strongest supporting evidence</strong><ul>{executive_evidence}</ul></div>"
        f"<div><strong>Explicit limitations</strong><ul>{executive_limitations}</ul></div>"
        "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Reviewer handoff and export summary</div>"
        f"<p><strong>Next reviewer role</strong>: {handoff_next_reviewer}</p>"
        f"<p><strong>Canonical handoff artifact</strong>: {handoff_canonical_artifact}</p>"
        + (f"<p><strong>Primary follow-up action</strong>: {handoff_primary_action_link}</p>" if handoff_primary_action_link else "")
        + f"<div><strong>Share/export now</strong><ul>{handoff_share_now}</ul></div>"
        + f"<div><strong>Decision log seed</strong><ul>{decision_log_seed_html}</ul></div>"
        + handoff_auto_seed_html
        + "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Review sign-off scaffold</div>"
        f"<p><strong>Reviewer / approver</strong>: {signoff_reviewer_role}</p>"
        f"<p><strong>Decision status</strong>: {signoff_decision_status}</p>"
        f"<p><strong>Decision date</strong>: {signoff_decision_date}</p>"
        f"<p><strong>Sign-off readiness</strong>: {signoff_readiness}</p>"
        f"<div><strong>Bounded rationale</strong><ul>{signoff_rationale}</ul></div>"
        f"<div><strong>Follow-up actions</strong><ul>{signoff_followups}</ul></div>"
        + (f"<p><strong>Primary follow-up action</strong>: {signoff_action_link}</p>" if signoff_action_link else "")
        + (f"<p><strong>Follow-up annotation type</strong>: {signoff_action_annotation_type}</p>" if signoff_action_annotation_type else "")
        + (f"<p><strong>Follow-up decision posture</strong>: {signoff_action_decision_posture}</p>" if signoff_action_decision_posture else "")
        + signoff_decision_template_html
        + "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Stakeholder cover sheet</div>"
        f"<p><strong>Audience</strong>: {cover_sheet_audience}</p>"
        f"<p><strong>Requested decision</strong>: {cover_sheet_requested_decision}</p>"
        f"<div><strong>Top 3 caveats</strong><ul>{cover_sheet_top_caveats}</ul></div>"
        f"<p><strong>Start here</strong>: {_render_nav_link(href=cover_sheet_start_here_href, label=str(cover_sheet_start_here.get('page_label', 'n/a')), css_class='analyst-briefing-target-link', available_pages=available_pages)} ({cover_sheet_start_here_page})"
        + (
            " | "
            + _render_nav_link(
                href=cover_sheet_start_here_action_href,
                label=cover_sheet_start_here_action_label,
                css_class='analyst-briefing-action-link',
                available_pages=available_pages,
            )
            if cover_sheet_start_here_action_href and cover_sheet_start_here_action_label
            else ""
        )
        + "</p>"
        f"<p>{cover_sheet_start_here_reason}</p>"
        + f"<div><strong>External-share summary</strong><ul>{external_share_summary_html}</ul></div>"
        + (f"<p><strong>Primary follow-up action</strong>: {external_share_action_link}</p>" if external_share_action_link else "")
        + (f"<p><strong>Follow-up annotation type</strong>: {external_share_action_annotation_type}</p>" if external_share_action_annotation_type else "")
        + (f"<p><strong>Follow-up decision posture</strong>: {external_share_action_decision_posture}</p>" if external_share_action_decision_posture else "")
        + "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Decision log export summary</div>"
        f"<div><strong>Approval state</strong><ul>{approval_state_html}</ul></div>"
        + f"<div><strong>Requested decision linkage</strong><ul>{requested_decision_linkage_html}</ul></div>"
        + (f"<p><strong>Primary follow-up action</strong>: {requested_decision_action_link}</p>" if requested_decision_action_link else "")
        + (f"<p><strong>Follow-up annotation type</strong>: {requested_decision_action_annotation_type}</p>" if requested_decision_action_annotation_type else "")
        + (f"<p><strong>Follow-up decision posture</strong>: {requested_decision_action_decision_posture}</p>" if requested_decision_action_decision_posture else "")
        + f"<div><strong>Distribution bundle</strong><ul>{distribution_bundle_html}</ul></div>"
        + f"<div><strong>Decision entry template</strong><ul>{decision_entry_template_html}</ul></div>"
        + (f"<p><strong>Decision-entry follow-up action</strong>: {decision_entry_action_link}</p>" if decision_entry_action_link else "")
        + (f"<p><strong>Follow-up annotation type</strong>: {decision_entry_action_annotation_type}</p>" if decision_entry_action_annotation_type else "")
        + (f"<p><strong>Follow-up decision posture</strong>: {decision_entry_action_decision_posture}</p>" if decision_entry_action_decision_posture else "")
        + "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Reviewer disposition standard</div>"
        f"<div><strong>Disposition options</strong><ul>{disposition_options_html}</ul></div>"
        f"<p><strong>Selected disposition</strong>: {selected_disposition}</p>"
        f"<div><strong>Disposition rationale bounds</strong><ul>{disposition_rationale_bounds_html}</ul></div>"
        f"<p><strong>Follow-up owner</strong>: {follow_up_owner}</p>"
        "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Disposition-aware action routing</div>"
        f"<p><strong>Route trigger</strong>: {route_trigger}</p>"
        f"<div><strong>Primary action bundle</strong><ul>{primary_action_bundle_html}</ul></div>"
        + (f"<p><strong>Primary follow-up action</strong>: {routing_action_link}</p>" if routing_action_link else "")
        + (f"<p><strong>Follow-up annotation type</strong>: {routing_action_annotation_type}</p>" if routing_action_annotation_type else "")
        + (f"<p><strong>Follow-up decision posture</strong>: {routing_action_decision_posture}</p>" if routing_action_decision_posture else "")
        + routing_decision_template_html
        + f"<p><strong>Escalation / handoff route</strong>: {escalation_handoff_route}</p>"
        + f"<p><strong>Action owner</strong>: {action_owner}</p>"
        + "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Decision packet seed</div>"
        f"<p><strong>Packet headline</strong>: {packet_headline}</p>"
        f"<div><strong>Decision snapshot</strong><ul>{decision_snapshot_html}</ul></div>"
        f"<div><strong>Share now packet</strong><ul>{share_now_packet_html}</ul></div>"
        + (f"<p><strong>Primary follow-up action</strong>: {decision_packet_primary_action_link}</p>" if decision_packet_primary_action_link else "")
        + (f"<p><strong>Follow-up annotation type</strong>: {decision_packet_primary_action_annotation_type}</p>" if decision_packet_primary_action_annotation_type else "")
        + (f"<p><strong>Follow-up decision posture</strong>: {decision_packet_primary_action_decision_posture}</p>" if decision_packet_primary_action_decision_posture else "")
        + f"<p><strong>Decision packet note</strong>: {decision_packet_note}</p>"
        + packet_auto_seed_html
        + "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Decision packet send-readiness checklist</div>"
        f"<p><strong>Overall send readiness</strong>: {packet_send_readiness}</p>"
        f"<p><strong>External send allowed</strong>: {packet_external_send_allowed}</p>"
        f"<p><strong>Next unblocker</strong>: {packet_next_unblocker}</p>"
        + packet_follow_up_decision_template_html
        + "<div class='table-wrap'><table><thead><tr><th>Item ID</th><th>Checklist item</th><th>Status</th><th>Reason</th></tr></thead><tbody>"
        f"{packet_send_checklist_rows}"
        "</tbody></table></div>"
        "</section>"
        "<section class='panel'>"
        "<div class='panel-header'>Evidence bundle</div>"
        "<div class='table-wrap'><table><thead><tr><th>Item</th><th>Value</th></tr></thead><tbody>"
        f"{evidence_rows or '<tr><td colspan=\'2\'>No evidence summary available.</td></tr>'}"
        "</tbody></table></div>"
        "</section>"
    )
