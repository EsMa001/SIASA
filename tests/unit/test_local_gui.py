import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from siasa.gui import local_app
from siasa.gui.local_app import build_local_mvp_site
from siasa.readmodels.release_evidence import build_release_failure_drill_report


_HREF_PATTERN = re.compile(r"href='([^']+)'")


def _internal_hrefs(html_text: str) -> list[str]:
    return [
        href
        for href in _HREF_PATTERN.findall(html_text)
        if not href.startswith(("http://", "https://", "#"))
    ]



def test_render_watchlist_evidence_link_allows_internal_coverage_targets_only() -> None:
    assert local_app._render_watchlist_evidence_link("coverage.html#source-SRC-A") == "<a href='coverage.html#source-SRC-A'>coverage.html#source-SRC-A</a>"
    assert local_app._render_watchlist_evidence_link("coverage.html") == "<a href='coverage.html'>coverage.html</a>"
    assert local_app._render_watchlist_evidence_link("javascript:alert(1)") == "invalid evidence link"
    assert local_app._render_watchlist_evidence_link("https://example.com") == "invalid evidence link"



def test_render_remediation_watchlist_shows_empty_state_when_no_priorities_exist() -> None:
    html = local_app._render_remediation_watchlist({"remediation_watchlist": []})
    assert "No remediation priorities recorded." in html



def test_render_stale_priority_watchlist_shows_summary_and_rows() -> None:
    html = local_app._render_stale_priority_watchlist(
        {
            "stale_priority_summary": {
                "stale_country_count": 2,
                "p1_stale_count": 1,
                "p2_stale_count": 1,
                "p3_stale_count": 0,
            },
            "stale_priority_watchlist": [
                {
                    "priority_rank": 1,
                    "country_id": "UKR",
                    "priority": "P1",
                    "freshness_hours": 8760.0,
                    "source_depth_band": "moderate",
                },
                {
                    "priority_rank": 2,
                    "country_id": "POL",
                    "priority": "P2",
                    "freshness_hours": 744.0,
                    "source_depth_band": "minimal",
                },
            ],
        }
    )
    assert "Stale Coverage Priority Queue" in html
    assert "Stale countries: 2 | P1=1, P2=1, P3=0" in html
    assert "UKR" in html and "POL" in html
    assert "id='stale-priority-UKR'" in html
    assert "id='stale-priority-POL'" in html
    assert "class='coverage-focus-target'" in html
    assert "data-focus-country='UKR'" in html
    assert "data-focus-section='stale_priority'" in html





def test_build_analyst_briefing_view_model_prioritizes_traceability_and_operability_risks() -> None:
    briefing = local_app._build_analyst_briefing_view_model(
        readiness_view_model={"release_verdict": "ready", "run_id": "RUN-TEST-002"},
        release_gate_view_model={"gate_verdict": "go"},
        operator_release_summary_view_model={
            "failed_gate_count": 0,
            "operator_next_action": "No action required; release gates are green.",
        },
        operator_blocker_causality_view_model={
            "primary_root_cause_gate_id": None,
            "operator_next_action": "No blocker-chain action required; release gates are green.",
        },
        operator_operability_cluster_view_model={
            "cluster_status": "degraded",
            "failed_gate_count": 2,
            "operator_next_action": "Review operability cluster and browser acceptance coverage.",
        },
        system_status_read_model={"country_coverage_visibility": {"stale_priority_watchlist": []}},
        validation_view_model={"historical_replay_summary": {"attention_cases": []}},
        traceability_view_model={
            "summary": {
                "missing_requirement_mapping_count": 1,
                "orphan_mapped_requirement_count": 0,
                "unhealthy_slice_count": 1,
                "closure_at_risk": 1,
            }
        },
    )

    assert briefing["item_count"] == 2
    assert briefing["traceability_risk_count"] == 1
    assert briefing["operability_cluster_count"] == 1
    assert briefing["primary_item_category"] == "traceability_risk"
    assert briefing["primary_item_target_page"] == "traceability.html"
    assert briefing["primary_item_next_check"] == "Inspect traceability.html and repo closure slice details."
    assert [item["category"] for item in briefing["items"]] == ["traceability_risk", "operability_cluster"]
    assert briefing["items"][0]["title"] == "Traceability risk: 1 missing mappings, 1 unhealthy slices, 1 at-risk closures"
    assert briefing["items"][1]["title"] == "Operability cluster: degraded"



def test_build_analyst_briefing_view_model_adds_country_hotspot_matrix() -> None:
    briefing = local_app._build_analyst_briefing_view_model(
        readiness_view_model={"release_verdict": "ready", "run_id": "RUN-TEST-002"},
        release_gate_view_model={"gate_verdict": "go"},
        system_status_read_model={
            "country_coverage_visibility": {
                "country_gap_rows": [
                    {
                        "country_id": "POL",
                        "priority": "P1",
                        "missing_domains": ["B", "D"],
                    },
                    {
                        "country_id": "EST",
                        "priority": "P2",
                        "missing_domains": ["B"],
                    },
                ],
                "stale_priority_watchlist": [
                    {
                        "priority_rank": 1,
                        "country_id": "POL",
                        "priority": "P1",
                        "freshness_hours": 240.0,
                        "source_depth_band": "moderate",
                    },
                    {
                        "priority_rank": 2,
                        "country_id": "UKR",
                        "priority": "P1",
                        "freshness_hours": 180.0,
                        "source_depth_band": "deep",
                    },
                ],
            }
        },
        validation_view_model={
            "historical_replay_summary": {
                "attention_cases": [
                    {
                        "country_id": "POL",
                        "case_id": "VAL-POL-2024-001",
                        "attention_reason": "status_mismatch",
                        "suggested_next_action": "Review POL replay alignment.",
                    },
                    {
                        "country_id": "POL",
                        "case_id": "VAL-POL-2024-002",
                        "attention_reason": "weak_replay_evidence",
                        "suggested_next_action": "Inspect replay evidence tier.",
                    },
                    {
                        "country_id": "UKR",
                        "case_id": "VAL-UKR-2024-001",
                        "attention_reason": "watch",
                        "suggested_next_action": "Review UKR reference case.",
                    },
                ]
            }
        },
    )

    hotspot_matrix = briefing["country_hotspot_matrix"]
    assert hotspot_matrix["row_count"] == 3
    assert hotspot_matrix["multi_signal_country_count"] == 2
    assert hotspot_matrix["rows"][0]["country_id"] == "POL"
    assert hotspot_matrix["rows"][0]["signal_count"] == 3
    assert hotspot_matrix["rows"][0]["signals"] == ["country_gap", "stale_priority", "validation_attention"]
    assert hotspot_matrix["rows"][0]["attention_case_count"] == 2
    assert hotspot_matrix["rows"][0]["missing_domains"] == ["B", "D"]
    assert hotspot_matrix["rows"][0]["recommended_next_check"] == "Coverage + Validation review"
    assert hotspot_matrix["rows"][0]["coverage_href"] == "coverage.html#country-gap-POL"
    assert hotspot_matrix["rows"][0]["validation_href"] == "validation.html#attention-case-VAL-POL-2024-001"
    assert hotspot_matrix["rows"][0]["coverage_prefill_href"] == "coverage.html?focus_country=POL&focus_section=country_gap&missing_domains=B%2CD#country-gap-POL"
    assert hotspot_matrix["rows"][0]["validation_prefill_href"] == "validation.html#ra=ra_reason=status_mismatch&ra_text=POL+VAL-POL-2024-001"
    assert hotspot_matrix["rows"][1]["country_id"] == "UKR"
    assert hotspot_matrix["rows"][1]["coverage_href"] == "coverage.html#stale-priority-UKR"
    assert hotspot_matrix["rows"][1]["validation_href"] == "validation.html#attention-case-VAL-UKR-2024-001"
    assert hotspot_matrix["rows"][1]["coverage_prefill_href"] == "coverage.html?focus_country=UKR&focus_section=stale_priority#stale-priority-UKR"
    assert hotspot_matrix["rows"][1]["validation_prefill_href"] == "validation.html#ra=ra_reason=watch&ra_text=UKR+VAL-UKR-2024-001"
    assert hotspot_matrix["rows"][2]["country_id"] == "EST"
    assert hotspot_matrix["rows"][2]["coverage_href"] == "coverage.html#country-gap-EST"
    assert hotspot_matrix["rows"][2]["validation_href"] is None
    assert hotspot_matrix["rows"][2]["coverage_prefill_href"] == "coverage.html?focus_country=EST&focus_section=country_gap&missing_domains=B#country-gap-EST"
    assert hotspot_matrix["rows"][2]["validation_prefill_href"] is None



def test_source_depth_band_matches_artifact_thresholds() -> None:
    assert local_app._source_depth_band(1) == "minimal"
    assert local_app._source_depth_band(2) == "moderate"
    assert local_app._source_depth_band(3) == "moderate"
    assert local_app._source_depth_band(4) == "deep"



def test_build_local_mvp_site_creates_required_mvp_pages_and_exports() -> None:
    world_map = {
        "baseline_mode": "Combined 30/90/365",
        "active_domains": ["A", "B", "D"],
        "countries": [
            {
                "country_id": "UKR",
                "status": "S3",
                "active_domains": ["A", "B", "D"],
                "drill_down_target": "/countries/UKR",
            }
        ],
    }
    country_profiles = {
        "UKR": {
            "country_id": "UKR",
            "multi_domain_status": "S3",
            "domain_states": {"A": "D3", "B": "D2", "D": "D1"},
            "trends": {
                "yearly": [
                    {"label": "2025-11", "value": 0.22},
                    {"label": "2025-12", "value": 0.48},
                    {"label": "2026-01", "value": 0.73},
                ]
            },
            "drivers": ["A_news_volume"],
            "linked_events": ["EVT-001"],
            "coverage": 0.84,
            "confidence": 0.73,
            "counter_indicators": ["D_macro_stability"],
            "uncertainty": ["partial_success"],
            "annotations": ["ANN-001"],
            "explanation_summary": "Escalation is primarily driven by Domain A with partial corroboration from Domain B.",
            "country_context": {"priority": "P1", "selection_type": "Core Focus", "region": "Europe / Black Sea"},
            "source_depth": {"source_ids": ["SRC-A", "SRC-B"], "source_count": 2},
            "domain_gap_summary": {
                "expected_domains": ["A", "B", "D"],
                "observed_domains": ["A", "B", "D"],
                "missing_domains": [],
                "gap_details": [{"domain": "D", "reason": "source_failed_this_run", "source_ids": ["SRC-D"], "diagnostics_by_source": {"SRC-D": "timeout"}}],
            },
        }
    }
    domain_details = {
        ("UKR", "A"): {
            "country_id": "UKR",
            "domain": "A",
            "time_series": [
                {"timestamp": "2026-05-09", "value": 0.31},
                {"timestamp": "2026-05-10", "value": 0.44},
                {"timestamp": "2026-05-11", "value": 0.67},
            ],
            "baseline_comparison": {"current_window": 0.67, "baseline_30d": 0.31, "delta_to_baseline": 0.36},
            "feature_values": [{"feature_id": "A_article_count", "value": 12.0, "coverage": 0.9}],
            "source_context": [{"source_id": "SRC-A", "freshness_hours": 6, "history_horizon": "3y", "status": "success"}],
            "anomaly_state": "D3",
            "uncertainty": ["source_bias_possible"],
        }
    }
    source_coverage = {
        "sources": [
            {"source_id": "SRC-A", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.9, "record_count": 12, "diagnostics": "fetch_ok"},
            {"source_id": "ACLED", "status": "prepared_adapter", "history_horizon": "n/a", "freshness_hours": None, "confidence": None, "record_count": 0, "diagnostics": "not_enabled"},
        ],
        "failed_sources": ["SRC-B"],
        "missing_sources": ["SRC-C"],
        "source_activation_readiness": [
            {"source_id": "SRC-UCDP-GED", "domain": "B", "activation_status": "blocked_missing_credentials", "credential_name": "UCDP_API_TOKEN", "configured": False, "provider_requirement": "api_token", "applicable_country_ids": ["UKR", "POL"], "blocked_reason": "missing_credential:UCDP_API_TOKEN", "activation_next_step": "Set UCDP_API_TOKEN in the runtime environment and rerun the governed live pipeline."},
            {"source_id": "SRC-RELIEFWEB", "domain": "C", "activation_status": "blocked_missing_credentials", "credential_name": "RELIEFWEB_APPNAME", "configured": False, "provider_requirement": "pre_approved_appname", "applicable_country_ids": ["UKR", "POL"], "blocked_reason": "missing_credential:RELIEFWEB_APPNAME", "activation_next_step": "Obtain an approved ReliefWeb appname, set RELIEFWEB_APPNAME, and rerun the governed live pipeline."},
        ],
        "source_activation_readiness_summary": {
            "total_sources": 2,
            "blocked_source_count": 2,
            "configured_ready_count": 0,
            "status_counts": {"blocked_missing_credentials": 2},
            "blocked_sources": ["SRC-UCDP-GED", "SRC-RELIEFWEB"],
            "configured_ready_sources": [],
        },
    }
    reports = {
        "daily_snapshot": {
            "format": "Markdown + JSON",
            "report_id": "REP-DAILY-RUN-200",
            "uncertainty": ["partial_success"],
            "failed_sources": ["SRC-B"],
            "snapshot_id": "SNAP-RUN-200-v1",
        },
        "country_profile": {"format": "Markdown + JSON", "report_id": "REP-COUNTRY-UKR", "country_id": "UKR"},
        "coverage_report": {"format": "Markdown + JSON + CSV", "report_id": "REP-COVERAGE-001"},
    }
    traceability_view = {
        "lineage_records": [
            {
                "source_id": "SRC-A",
                "raw_record_id": "RAW-SRC-A-1",
                "normalized_id": "NORM-SRC-A-1",
                "feature_id": "A_article_count",
                "domain_status_id": "DST-UKR-A-RUN-200",
                "multi_domain_status_id": "MST-UKR-RUN-200",
                "snapshot_id": "SNAP-RUN-200-v1",
                "observed_at": "2026-05-11T17:00:00Z",
                "report_id": "REP-DAILY-RUN-200",
            },
            {
                "source_id": "SRC-B",
                "raw_record_id": "RAW-SRC-B-7",
                "normalized_id": "NORM-SRC-B-7",
                "feature_id": "A_article_count",
                "domain_status_id": "DST-UKR-A-RUN-200",
                "multi_domain_status_id": "MST-UKR-RUN-200",
                "snapshot_id": "SNAP-RUN-200-v1",
                "observed_at": "2026-05-11T17:20:00Z",
                "report_id": "REP-DAILY-RUN-200",
            },
            {
                "source_id": "SRC-C",
                "raw_record_id": "RAW-SRC-C-3",
                "normalized_id": "NORM-SRC-C-3",
                "feature_id": "D_macro_index",
                "domain_status_id": "DST-UKR-D-RUN-200",
                "multi_domain_status_id": "MST-UKR-RUN-200",
                "snapshot_id": "SNAP-RUN-200-v1",
                "observed_at": "2026-05-11T18:05:00Z",
                "report_id": "REP-DAILY-RUN-200",
            },
        ]
    }
    annotations_view = {
        "annotations": [
            {
                "annotation_id": "ANN-001",
                "created_at": "2026-05-11T18:05:00Z",
                "author": "analyst",
                "scope": "country",
                "annotation_type": "context_note",
                "severity_assessment": "relevant",
                "confidence_assessment": "medium",
                "text": "Replicated agency report likely inflated country-level signal volume.",
                "tags": ["source_dependency"],
                "linked_items": ["UKR"],
                "review_status": "draft",
            },
            {
                "annotation_id": "ANN-002",
                "created_at": "2026-05-11T18:06:00Z",
                "author": "analyst",
                "scope": "domain",
                "annotation_type": "lineage_note",
                "severity_assessment": "uncertain",
                "confidence_assessment": "high",
                "text": "Domain A spike is traceable to two closely coupled source clusters.",
                "tags": ["lineage"],
                "linked_items": ["UKR:A", "A_article_count"],
                "review_status": "reviewed",
            },
            {
                "annotation_id": "ANN-003",
                "created_at": "2026-05-11T18:07:00Z",
                "author": "analyst",
                "scope": "snapshot",
                "annotation_type": "review_note",
                "severity_assessment": "uncertain",
                "confidence_assessment": "low",
                "text": "Snapshot review pending source outage assessment.",
                "tags": ["review_pending"],
                "linked_items": ["SNAP-RUN-200-v1"],
                "review_status": "unreviewed",
            },
        ],
        "by_scope": {
            "country": ["ANN-001"],
            "domain": ["ANN-002"],
            "snapshot": ["ANN-003"],
        },
        "by_linked_item": {
            "UKR": ["ANN-001"],
            "UKR:A": ["ANN-002"],
            "A_article_count": ["ANN-002"],
            "SNAP-RUN-200-v1": ["ANN-003"],
        },
    }
    validation_view = {
        "case_id": "VAL-UKR-2022-001",
        "country_id": "UKR",
        "case_name": "Escalation reference case",
        "time_range": {"start": "2022-02-01", "end": "2022-03-01"},
        "expected_domains": ["A", "B", "D"],
        "observed_domains": ["A", "B"],
        "domain_match_ratio": 2 / 3,
        "status_match": True,
        "expected_pattern": "Aligned information, event, and economic stress escalation.",
        "validation_goal": "Check multi-domain alignment detection.",
        "reference_sources": ["SRC-A", "SRC-B"],
        "validation_metrics": ["Domain Match", "Status Match"],
        "known_limitations": ["historical coverage incomplete"],
        "reprocessing_comparison": {"prior_snapshot_id": "SNAP-RUN-001-v1", "new_snapshot_id": "SNAP-RUN-001-v2", "changed_versions": ["rule_version"]},
        "validation_cases": [
            {
                "case_id": "VAL-UKR-2022-001",
                "country_id": "UKR",
                "review_verdict": "match_with_gaps",
                "expected_domains": ["A", "B", "D"],
                "observed_domains": ["A", "B"],
            },
            {
                "case_id": "VAL-POL-2022-001",
                "country_id": "POL",
                "review_verdict": "match",
                "expected_domains": ["A", "B"],
                "observed_domains": ["A", "B"],
            },
        ],
        "portfolio_summary": {
            "case_count": 2,
            "countries_covered": ["POL", "UKR"],
            "review_verdict_counts": {"match": 1, "match_with_gaps": 1},
            "cases_with_gaps": [{"case_id": "VAL-UKR-2022-001", "country_id": "UKR", "review_verdict": "match_with_gaps"}],
        },
        "reference_case_library": [
            {
                "case_id": "VAL-UKR-2022-001",
                "country_id": "UKR",
                "case_name": "Escalation reference case",
                "case_type": "military_escalation",
                "time_range": {"start": "2022-02-01", "end": "2022-03-01"},
                "expected_domains": ["A", "B", "D"],
            },
            {
                "case_id": "VAL-POL-2023-001",
                "country_id": "POL",
                "case_name": "Hybrid pressure reference case",
                "case_type": "hybrid_pressure",
                "time_range": {"start": "2023-10-01", "end": "2023-10-31"},
                "expected_domains": ["A", "B", "D"],
            },
        ],
        "reference_case_library_summary": {
            "case_count": 4,
            "countries_covered": ["ISR", "POL", "TWN", "UKR"],
            "case_type_counts": {
                "disinformation_spike": 1,
                "hybrid_pressure": 1,
                "military_escalation": 1,
                "strategic_posturing": 1,
            },
            "time_range": {"start": "2022-02-01", "end": "2024-05-31"},
        },
        "historical_reference_reviews": [
            {
                "case_id": "VAL-UKR-2022-001",
                "country_id": "UKR",
                "review_verdict": "historical_alignment_confirmed",
                "evidence_tier": "verified_multi_source",
                "evidence_score": 1.0,
                "expected_status": "S3",
                "historical_observed_status": "S3",
            },
            {
                "case_id": "VAL-TWN-2024-001",
                "country_id": "TWN",
                "review_verdict": "historical_alignment_with_gaps",
                "evidence_tier": "curated_public_source",
                "evidence_score": 0.6,
                "expected_status": "S1",
                "historical_observed_status": "S1",
            },
        ],
        "historical_reference_review_summary": {
            "case_count": 4,
            "countries_covered": ["ISR", "POL", "TWN", "UKR"],
            "review_verdict_counts": {
                "historical_alignment_confirmed": 3,
                "historical_alignment_with_gaps": 1,
            },
            "evidence_tier_counts": {
                "corroborated_multi_source": 1,
                "curated_public_source": 1,
                "verified_multi_source": 2,
            },
            "average_evidence_score": 0.85,
        },
        "historical_replay_reviews": [
            {
                "case_id": "VAL-UKR-2022-001",
                "country_id": "UKR",
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
                "replay_input_country_ids": ["UKR"],
                "archival_data_files": ["archival_replay_inputs/VAL-UKR-2022-001.json"],
                "provenance_notes": "Provider-derived archival normalized-record bundle captured and governed in repo for replay reproducibility.",
                "replay_known_limitations": ["provider_backed_archival_replay_uses_repo_stored_archival_inputs_not_live_backfill_at_runtime"],
                "replay_source_coverage_ratio": 1.0,
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 1.0,
                "replay_evidence_tier": "verified_replay_evidence",
                "replayed_status": "S3",
                "expected_status": "S3",
                "status_match": True,
                "expected_domains": ["A", "B", "D"],
                "replayed_domains": ["A", "B", "D"],
                "domain_match_ratio": 1.0,
                "review_verdict": "replay_match",
                "replay_input_record_count": 8,
            },
            {
                "case_id": "VAL-POL-2023-001",
                "country_id": "POL",
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
                "replay_input_country_ids": ["POL"],
                "archival_data_files": ["archival_replay_inputs/VAL-POL-2023-001.json"],
                "provenance_notes": "Provider-derived archival normalized-record bundle captured and governed in repo for replay reproducibility.",
                "replay_known_limitations": ["provider_backed_archival_replay_uses_repo_stored_archival_inputs_not_live_backfill_at_runtime"],
                "replay_source_coverage_ratio": 1.0,
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 1.0,
                "replay_evidence_tier": "verified_replay_evidence",
                "replayed_status": "S3",
                "expected_status": "S3",
                "status_match": True,
                "expected_domains": ["A", "B", "D"],
                "replayed_domains": ["A", "B", "D"],
                "domain_match_ratio": 1.0,
                "review_verdict": "replay_match",
                "replay_input_record_count": 8,
            },
            {
                "case_id": "VAL-POL-2024-002",
                "country_id": "POL",
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS"],
                "replay_input_country_ids": ["POL"],
                "archival_data_files": ["archival_replay_inputs/VAL-POL-2024-002.json"],
                "provenance_notes": "Provider-derived archival normalized-record bundle intentionally captured with no usable governed Domain D record to exercise replay gap behavior.",
                "replay_known_limitations": [
                    "provider_backed_archival_replay_uses_repo_stored_archival_inputs_not_live_backfill_at_runtime",
                    "governed_archival_bundle_intentionally_omits_domain_d_records_to_exercise_partial_replay_behavior",
                ],
                "replay_source_coverage_ratio": 0.75,
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 0.85,
                "replay_evidence_tier": "strong_replay_evidence",
                "replayed_status": "S3",
                "expected_status": "S3",
                "status_match": True,
                "expected_domains": ["A", "B", "D"],
                "replayed_domains": ["A", "B"],
                "missing_expected_domains": ["D"],
                "domain_match_ratio": 2 / 3,
                "review_verdict": "replay_match_with_gaps",
                "replay_input_record_count": 5,
            },
            {
                "case_id": "VAL-ISR-2023-001",
                "country_id": "ISR",
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
                "replay_input_country_ids": ["ISR"],
                "archival_data_files": ["archival_replay_inputs/VAL-ISR-2023-001.json"],
                "provenance_notes": "Provider-derived archival normalized-record bundle captured and governed in repo for replay reproducibility.",
                "replay_known_limitations": ["provider_backed_archival_replay_uses_repo_stored_archival_inputs_not_live_backfill_at_runtime"],
                "replay_source_coverage_ratio": 1.0,
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 1.0,
                "replay_evidence_tier": "verified_replay_evidence",
                "replayed_status": "S3",
                "expected_status": "S3",
                "status_match": True,
                "expected_domains": ["A", "B", "D"],
                "replayed_domains": ["A", "B", "D"],
                "domain_match_ratio": 1.0,
                "review_verdict": "replay_match",
                "replay_input_record_count": 8,
            },
            {
                "case_id": "VAL-ISR-2024-002",
                "country_id": "ISR",
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDELT-DOC"],
                "replay_input_country_ids": ["ISR"],
                "archival_data_files": ["archival_replay_inputs/VAL-ISR-2024-002.json"],
                "provenance_notes": "Provider-derived archival normalized-record bundle intentionally constrained to information-domain evidence to exercise replay mismatch behavior.",
                "replay_known_limitations": [
                    "provider_backed_archival_replay_uses_repo_stored_archival_inputs_not_live_backfill_at_runtime",
                    "governed_archival_bundle_intentionally_constrained_to_information_domain_records_to_exercise_mismatch_behavior",
                ],
                "replay_source_coverage_ratio": 0.25,
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 0.25,
                "replay_evidence_tier": "weak_replay_evidence",
                "replayed_status": "S1",
                "expected_status": "S3",
                "status_match": False,
                "expected_domains": ["A", "B", "D"],
                "replayed_domains": ["A"],
                "missing_expected_domains": ["B", "D"],
                "domain_match_ratio": 1 / 3,
                "review_verdict": "replay_mismatch",
                "replay_input_record_count": 2,
            },
            {
                "case_id": "VAL-TWN-2024-001",
                "country_id": "TWN",
                "review_basis": "provider_backed_archival_replay",
                "replay_input_source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS"],
                "replay_input_country_ids": ["TWN"],
                "archival_data_files": ["archival_replay_inputs/VAL-TWN-2024-001.json"],
                "provenance_notes": "Provider-derived archival normalized-record bundle captured and governed in repo for replay reproducibility.",
                "replay_known_limitations": ["provider_backed_archival_replay_uses_repo_stored_archival_inputs_not_live_backfill_at_runtime"],
                "replay_source_coverage_ratio": 1.0,
                "replay_provenance_completeness_ratio": 1.0,
                "replay_evidence_score": 1.0,
                "replay_evidence_tier": "verified_replay_evidence",
                "replayed_status": "S1",
                "expected_status": "S1",
                "status_match": True,
                "expected_domains": ["A", "B"],
                "replayed_domains": ["A", "B"],
                "domain_match_ratio": 1.0,
                "review_verdict": "replay_match",
                "replay_input_record_count": 4,
            },
        ],
        "historical_replay_summary": {
            "case_count": 6,
            "countries_covered": ["ISR", "POL", "TWN", "UKR"],
            "review_verdict_counts": {
                "replay_match": 4,
                "replay_match_with_gaps": 1,
                "replay_mismatch": 1,
            },
            "status_match_count": 5,
            "average_domain_match_ratio": 0.83,
            "average_replay_evidence_score": 0.85,
            "average_replay_source_coverage_ratio": 0.83,
            "average_replay_provenance_completeness_ratio": 1.0,
            "replay_input_record_total": 35,
            "archival_data_file_count": 6,
            "replay_evidence_tier_counts": {
                "strong_replay_evidence": 1,
                "verified_replay_evidence": 4,
                "weak_replay_evidence": 1,
            },
            "replay_input_source_coverage_counts": {
                "SRC-GDACS": 5,
                "SRC-GDELT-DOC": 6,
                "SRC-GDELT-EVENTS": 5,
                "WB-INDICATORS": 3,
            },
            "review_basis_counts": {
                "provider_backed_archival_replay": 6,
            },
        },
    }
    system_status = {
        "run_id": "RUN-200",
        "run_status": "partial_success",
        "active_domains": ["A", "B", "D"],
        "coverage": {"countries_total": 30, "countries_with_updates": 27},
        "failed_sources": ["SRC-B"],
        "available_reports": ["REP-DAILY-RUN-200", "REP-COUNTRY-UKR"],
        "snapshot_id": "SNAP-RUN-200-v1",
        "reprocessing_status": "idle",
        "last_run": "2026-05-11T18:00:00Z",
        "top_status_changes": [
            {"country_id": "UKR", "from_status": "S2", "to_status": "S3", "direction": "up"},
            {"country_id": "POL", "from_status": "S2", "to_status": "S1", "direction": "down"},
        ],
        "data_gaps": ["failed_source:SRC-B", "country_without_update:POL"],
        "country_coverage_visibility": {
            "priority_summary": [{"priority": "P1", "country_count": 1, "countries": ["UKR"]}],
            "source_depth_band_summary": [{"band": "moderate", "country_count": 1, "countries": ["UKR"]}],
            "country_gap_rows": [
                {
                    "country_id": "UKR",
                    "priority": "P1",
                    "source_count": 2,
                    "source_depth_band": "moderate",
                    "missing_domains": ["D"],
                    "missing_domain_count": 1,
                    "gap_details": [{"domain": "D", "reason": "source_failed_this_run", "source_ids": ["SRC-D"], "source_links": ["coverage.html#source-SRC-D"]}],
                }
            ],
            "missing_domain_totals": {"D": 1},
            "remediation_watchlist": [
                {
                    "action_category": "fetch_problem",
                    "severity": "high",
                    "country_count": 1,
                    "source_count": 1,
                    "countries": ["UKR"],
                    "source_ids": ["SRC-D"],
                    "suggested_next_action": "Retry adapter execution and inspect source-side rate limiting or transport failures.",
                    "owner_hint": "adapter/source integration",
                    "evidence_link": "coverage.html#source-SRC-D",
                }
            ],
        },
        "operational_evidence_lane": {
            "latest_summary": {
                "run_id": "RUN-200",
                "run_status": "partial_success",
                "pilot_set": "focus-complete",
                "country_set_id": "MVP-COUNTRIES-LIVE-focus-complete-v1",
                "countries_total": 21,
                "countries_with_updates": 18,
                "countries_without_updates_count": 3,
                "countries_without_updates": ["EST", "MMR", "QAT"],
                "combined_ce_ratio": 0.8571,
                "governance_verdict": "amber",
                "policy_gate_verdict": "pass",
                "release_verdict": "blocked_by_known_gaps",
                "readiness_interpretation": "runtime_degraded_and_release_blocked",
                "known_gap_count": 2,
                "known_gaps": ["failed_source:SRC-B", "country_gap:UKR:D:source_failed_this_run"],
                "suppressed_known_gaps": [],
                "known_gap_suppression_reason": None,
                "failed_source_count": 1,
                "failed_sources": ["SRC-B"],
                "verification_policy": {
                    "allow_partial_success": True,
                    "allow_failed_sources": True,
                    "allow_policy_gate_fail": False,
                    "enabled_overrides": ["allow_partial_success", "allow_failed_sources"],
                    "mode": "explicit_override_enabled",
                },
                "operator_next_action": "Investigate failed sources and restore source availability.",
                "evidence_links": {
                    "bundle_index_href": "/tmp/siasa-gui-test/index.html",
                    "coverage_page_href": "/tmp/siasa-gui-test/coverage.html",
                    "coverage_json_href": "/tmp/siasa-gui-test/source_coverage.json",
                    "system_status_json_href": "/tmp/siasa-gui-test/system_status.json",
                    "readiness_page_href": "/tmp/siasa-gui-test/readiness.html",
                    "readiness_json_href": "/tmp/siasa-gui-test/readiness.json",
                    "release_package_page_href": "/tmp/siasa-gui-test/release_package.html",
                    "release_package_json_href": "/tmp/siasa-gui-test/release_demo_package.json",
                    "release_gate_json_href": "/tmp/siasa-gui-test/release_gate.json",
                },
                "share_refs": {
                    "bundle_ref": "bundle:/tmp/siasa-gui-test",
                    "coverage_json_ref": "coverage_json:/tmp/siasa-gui-test/source_coverage.json",
                    "system_status_json_ref": "system_status_json:/tmp/siasa-gui-test/system_status.json",
                    "readiness_json_ref": "readiness_json:/tmp/siasa-gui-test/readiness.json",
                    "release_package_json_ref": "release_package_json:/tmp/siasa-gui-test/release_demo_package.json",
                    "release_gate_json_ref": "release_gate_json:/tmp/siasa-gui-test/release_gate.json",
                },
                "handoff_summary": "Run RUN-200: bundle at /tmp/siasa-gui-test; review readiness_json:/tmp/siasa-gui-test/readiness.json, coverage_json:/tmp/siasa-gui-test/source_coverage.json, and release_gate_json:/tmp/siasa-gui-test/release_gate.json.",
                "triage_tag": "degraded_release_blocked",
                "triage_summary": "Runtime degraded and release blocked; review failed sources and known gaps first.",
                "breadth_coverage_tag": "breadth_partial_slice_updated",
                "breadth_coverage_summary": "18/21 countries updated; missing updates remain in EST, MMR, QAT.",
            },
            "recent_runs": [
                {
                    "run_id": "RUN-200",
                    "recorded_at": "2026-05-11T18:00:00Z",
                    "run_status": "partial_success",
                    "pilot_set": "focus-complete",
                    "artifacts_dir": "/tmp/siasa-gui-test-artifacts/RUN-200",
                    "gui_index": "/tmp/siasa-gui-test/index.html",
                    "bundle_root": "/tmp/siasa-gui-test",
                    "country_set_id": "MVP-COUNTRIES-LIVE-focus-complete-v1",
                    "countries_total": 21,
                    "countries_with_updates": 18,
                    "countries_without_updates_count": 3,
                    "countries_without_updates": ["EST", "MMR", "QAT"],
                    "combined_ce_ratio": 0.8571,
                    "governance_verdict": "amber",
                    "policy_gate_verdict": "pass",
                    "release_verdict": "blocked_by_known_gaps",
                    "readiness_interpretation": "runtime_degraded_and_release_blocked",
                    "known_gap_count": 2,
                    "failed_source_count": 1,
                    "failed_sources": ["SRC-B"],
                    "verification_policy": {
                        "allow_partial_success": True,
                        "allow_failed_sources": True,
                        "allow_policy_gate_fail": False,
                        "enabled_overrides": ["allow_partial_success", "allow_failed_sources"],
                        "mode": "explicit_override_enabled",
                    },
                    "evidence_links": {
                        "bundle_index_href": "/tmp/siasa-gui-test/index.html",
                        "coverage_page_href": "/tmp/siasa-gui-test/coverage.html",
                        "coverage_json_href": "/tmp/siasa-gui-test/source_coverage.json",
                        "system_status_json_href": "/tmp/siasa-gui-test/system_status.json",
                        "readiness_page_href": "/tmp/siasa-gui-test/readiness.html",
                        "readiness_json_href": "/tmp/siasa-gui-test/readiness.json",
                        "release_package_page_href": "/tmp/siasa-gui-test/release_package.html",
                        "release_package_json_href": "/tmp/siasa-gui-test/release_demo_package.json",
                        "release_gate_json_href": "/tmp/siasa-gui-test/release_gate.json",
                    },
                    "share_refs": {
                        "bundle_ref": "bundle:/tmp/siasa-gui-test",
                        "coverage_json_ref": "coverage_json:/tmp/siasa-gui-test/source_coverage.json",
                        "system_status_json_ref": "system_status_json:/tmp/siasa-gui-test/system_status.json",
                        "readiness_json_ref": "readiness_json:/tmp/siasa-gui-test/readiness.json",
                        "release_package_json_ref": "release_package_json:/tmp/siasa-gui-test/release_demo_package.json",
                        "release_gate_json_ref": "release_gate_json:/tmp/siasa-gui-test/release_gate.json",
                    },
                    "handoff_summary": "Run RUN-200: bundle at /tmp/siasa-gui-test; review readiness_json:/tmp/siasa-gui-test/readiness.json, coverage_json:/tmp/siasa-gui-test/source_coverage.json, and release_gate_json:/tmp/siasa-gui-test/release_gate.json.",
                    "triage_tag": "degraded_release_blocked",
                    "triage_summary": "Runtime degraded and release blocked; review failed sources and known gaps first.",
                    "breadth_coverage_tag": "breadth_partial_slice_updated",
                    "breadth_coverage_summary": "18/21 countries updated; missing updates remain in EST, MMR, QAT.",
                },
                {
                    "run_id": "RUN-150",
                    "recorded_at": "2026-05-10T18:00:00Z",
                    "run_status": "success",
                    "pilot_set": "extended-focus-complete",
                    "artifacts_dir": "/tmp/siasa-history/RUN-150",
                    "gui_index": "/tmp/siasa-history/RUN-150/index.html",
                    "bundle_root": "/tmp/siasa-history/RUN-150",
                    "country_set_id": "MVP-COUNTRIES-LIVE-extended-focus-complete-v1",
                    "countries_total": 11,
                    "countries_with_updates": 11,
                    "countries_without_updates_count": 0,
                    "countries_without_updates": [],
                    "combined_ce_ratio": 1.0,
                    "governance_verdict": "green",
                    "policy_gate_verdict": "pass",
                    "release_verdict": "ready",
                    "readiness_interpretation": "release_ready",
                    "known_gap_count": 0,
                    "failed_source_count": 0,
                    "failed_sources": [],
                    "verification_policy": {
                        "allow_partial_success": False,
                        "allow_failed_sources": False,
                        "allow_policy_gate_fail": False,
                        "enabled_overrides": [],
                        "mode": "strict",
                    },
                    "evidence_links": {
                        "bundle_index_href": "/tmp/siasa-history/RUN-150/index.html",
                        "coverage_page_href": "/tmp/siasa-history/RUN-150/coverage.html",
                        "coverage_json_href": "/tmp/siasa-history/RUN-150/source_coverage.json",
                        "system_status_json_href": "/tmp/siasa-history/RUN-150/system_status.json",
                        "readiness_page_href": "/tmp/siasa-history/RUN-150/readiness.html",
                        "readiness_json_href": "/tmp/siasa-history/RUN-150/readiness.json",
                        "release_package_page_href": "/tmp/siasa-history/RUN-150/release_package.html",
                        "release_package_json_href": "/tmp/siasa-history/RUN-150/release_demo_package.json",
                        "release_gate_json_href": "/tmp/siasa-history/RUN-150/release_gate.json",
                    },
                    "share_refs": {
                        "bundle_ref": "bundle:/tmp/siasa-history/RUN-150",
                        "coverage_json_ref": "coverage_json:/tmp/siasa-history/RUN-150/source_coverage.json",
                        "system_status_json_ref": "system_status_json:/tmp/siasa-history/RUN-150/system_status.json",
                        "readiness_json_ref": "readiness_json:/tmp/siasa-history/RUN-150/readiness.json",
                        "release_package_json_ref": "release_package_json:/tmp/siasa-history/RUN-150/release_demo_package.json",
                        "release_gate_json_ref": "release_gate_json:/tmp/siasa-history/RUN-150/release_gate.json",
                    },
                    "handoff_summary": "Run RUN-150: bundle at /tmp/siasa-history/RUN-150; review readiness_json:/tmp/siasa-history/RUN-150/readiness.json, coverage_json:/tmp/siasa-history/RUN-150/source_coverage.json, and release_gate_json:/tmp/siasa-history/RUN-150/release_gate.json.",
                    "triage_tag": "ready_green",
                    "triage_summary": "Run is green and release-ready; suitable as the default handoff baseline.",
                    "breadth_coverage_tag": "breadth_full_slice_updated",
                    "breadth_coverage_summary": "All countries in the governed slice produced updates; this run is a full breadth proof for the selected slice.",
                }
            ],
        },
    }

    repo_closure_view = {
        "summary": {"slice_count": 4, "requirement_count": 18, "closed": 18, "at_risk": 0},
        "slices": [
            {"slice_id": "governance-and-run-controls", "summary": {"closed": 6, "at_risk": 0}},
            {"slice_id": "reporting-and-export", "summary": {"closed": 4, "at_risk": 0}},
        ],
    }
    stakeholder_functional_closure_view = {
        "focus_gap_cluster": {
            "stakeholder_ids": [
                "StR-001", "StR-002", "StR-004", "StR-007", "StR-024", "StR-025",
                "StR-135", "StR-136", "StR-137", "StR-138", "StR-139", "StR-140", "StR-141", "StR-142",
                "StR-226", "StR-227", "StR-228", "StR-229", "StR-230",
            ],
            "covered_count": 19,
            "implemented_count": 19,
            "not_implemented_count": 0,
            "not_implemented_ids": [],
        }
    }

    pages = build_local_mvp_site(
        output_dir=Path("/tmp/siasa-gui-test"),
        world_map_read_model=world_map,
        country_profile_read_models=country_profiles,
        domain_detail_read_models=domain_details,
        source_coverage_read_model=source_coverage,
        report_catalog=reports,
        system_status_read_model=system_status,
        validation_view_model=validation_view,
        traceability_view_model=traceability_view,
        repo_closure_view_model=repo_closure_view,
        annotations_view_model=annotations_view,
        stakeholder_functional_closure_view_model=stakeholder_functional_closure_view,
    )

    assert (pages.output_dir / "index.html").exists()
    assert (pages.output_dir / "countries" / "UKR.html").exists()
    assert (pages.output_dir / "domains" / "UKR-A.html").exists()
    assert (pages.output_dir / "coverage.html").exists()
    assert (pages.output_dir / "source_coverage.json").exists()
    assert (pages.output_dir / "reports.html").exists()
    assert (pages.output_dir / "runs.html").exists()
    assert (pages.output_dir / "system_status.json").exists()
    assert (pages.output_dir / "trends.html").exists()
    assert (pages.output_dir / "events.html").exists()
    assert (pages.output_dir / "comparison.html").exists()
    assert (pages.output_dir / "validation.html").exists()
    assert (pages.output_dir / "traceability.html").exists()
    assert (pages.output_dir / "annotations.html").exists()
    assert (pages.output_dir / "readiness.html").exists()
    assert (pages.output_dir / "release_package.html").exists()
    assert (pages.output_dir / "release_demo_package.json").exists()
    assert (pages.output_dir / "release_gate.json").exists()
    assert (pages.output_dir / "stakeholder_functional_closure.json").exists()
    assert (pages.output_dir / "stakeholder_e2e_flow_coverage.json").exists()
    assert (pages.output_dir / "release_readiness_index.json").exists()
    assert (pages.output_dir / "stakeholder_e2e_ui_smoke.json").exists()
    assert (pages.output_dir / "analyst_briefing.json").exists()

    index_html = (pages.output_dir / "index.html").read_text()
    assert "World Anomaly Map" in index_html
    # AP-F19: Dynamic role switcher
    assert "role-switcher" in index_html
    assert "role-select" in index_html
    assert "applyRole" in index_html
    assert "value='analyst'" in index_html
    assert "value='admin'" in index_html
    assert "value='viewer'" in index_html
    assert "data-activeRole" in index_html or "activeRole" in index_html
    assert "world-map-svg" in index_html
    assert "map-zoom-container" in index_html
    assert "map-overlay-controls" in index_html
    assert "map-overlay-btn" in index_html
    assert "map-tooltip" in index_html
    assert "map-zoom-reset" in index_html
    assert "data-overlay='status'" in index_html
    assert "data-overlay='anomaly'" in index_html
    assert "data-overlay='freshness'" in index_html
    assert "applyOverlay" in index_html
    assert "applyTransform" in index_html
    assert "data-anomaly-score" in index_html
    assert "Coverage / Confidence Visualization" in index_html
    assert "coverage-visualization-block" in index_html
    assert "Europe / Black Sea" in index_html
    assert "Baseline / View Controls" in index_html
    assert "Domain Filter" in index_html
    assert "Time Window" in index_html
    assert "Status Filter" in index_html
    assert "country-search" in index_html
    assert "overview-save-state" in index_html
    assert "overview-restore-state" in index_html
    assert "overview-copy-link" in index_html
    assert "overview-link-status" in index_html
    assert "persistOverviewStateToHash" in index_html
    assert "applyOverviewStateFromHash" in index_html
    assert "saveOverviewStateLocally" in index_html
    assert "restoreOverviewStateLocally" in index_html
    assert "copyOverviewFilterLink" in index_html
    assert "ov_priority" in index_html
    assert "ov_view" in index_html
    assert "overview-visible-count" in index_html
    assert "Visible countries:" in index_html
    assert "Status Filter: " in index_html
    assert "Baseline Mode" in index_html
    assert "<svg" in index_html
    assert "Global Overview" in index_html
    assert "UKR" in index_html
    assert "countries/UKR.html" in index_html
    assert "Countries Monitored" in index_html
    assert "Priority" in index_html
    assert "Source Depth" in index_html
    assert "Domain Gaps" in index_html
    assert "Top Status Changes" in index_html
    assert "S2 → S3" in index_html
    assert "Data Gaps / Trust Limits" in index_html
    assert "failed_source:SRC-B" in index_html
    assert "country_without_update:POL" in index_html
    assert "Priority Coverage Summary" in index_html
    assert "Source Depth Band Summary" in index_html
    assert "Country Coverage / Gap Watchlist" in index_html
    assert "Remediation Watchlist" in index_html
    assert "fetch_problem" in index_html
    assert "severity=high" in index_html
    assert "Retry adapter execution and inspect source-side rate limiting or transport failures." in index_html
    assert "adapter/source integration" in index_html
    assert "coverage.html#source-SRC-D" in index_html
    assert "SRC-D" in index_html
    assert "Gap Cause" in index_html
    assert "moderate" in index_html
    assert "source_failed_this_run" in index_html
    assert "coverage.html#source-SRC-D" in index_html
    assert "SRC-D" in index_html
    assert "Multi-Domain Status" in index_html
    assert "supported" in index_html

    country_html = (pages.output_dir / "countries" / "UKR.html").read_text()
    assert "Country Profile" in country_html
    assert "Trust / Uncertainty" in country_html
    assert "Coverage" in country_html
    assert "Confidence" in country_html
    assert "P1" in country_html
    assert "Core Focus" in country_html
    assert "Source Depth" in country_html
    assert "SRC-A" in country_html and "SRC-B" in country_html
    assert "Domain Gap" in country_html
    assert "Gap Cause Details" in country_html
    assert "../coverage.html#source-SRC-D" in country_html
    assert "uncertainty-badge" in country_html
    assert "Analysis Path" in country_html
    assert "Escalation is primarily driven by Domain A with partial corroboration from Domain B." in country_html
    assert "Analysis Path" in country_html
    assert "A_news_volume" in country_html
    assert "Domain Deep" in country_html
    assert "../domains/UKR-A.html" in country_html
    assert "B — not available" in country_html
    assert "ANN-001" in country_html
    assert "Analyst Annotations" in country_html
    assert "Replicated agency report likely inflated country-level signal volume." in country_html
    assert "../annotations.html?scope=country&amp;linked_item=UKR&amp;annotation_type=context_note" in country_html
    assert "Open Annotation Workflow for this Country" in country_html

    domain_html = (pages.output_dir / "domains" / "UKR-A.html").read_text()
    assert "Domain Detail" in domain_html
    assert "delta_to_baseline" in domain_html
    assert "Time Series Chart" in domain_html
    assert "Domain Deep-Dive Controls" in domain_html
    assert "domain-feature-filter" in domain_html
    assert "domain-source-filter" in domain_html
    assert "domain-feature-visible-count" in domain_html
    assert "domain-source-visible-count" in domain_html
    assert "domain-feature-row" in domain_html
    assert "domain-source-row" in domain_html
    assert "applyDomainFilters" in domain_html
    assert "Feature Values Table" in domain_html
    assert "Source Context Table" in domain_html
    assert "2026-05-09" in domain_html
    assert "<svg" in domain_html
    assert "SRC-A" in domain_html
    assert "Domain A spike is traceable to two closely coupled source clusters." in domain_html
    assert "Comparison vs Baseline" in domain_html
    assert "Current Window" in domain_html
    assert "30d Baseline" in domain_html
    assert "Baseline Delta Band" in domain_html
    assert "Historical Window Context" in domain_html
    assert "2026-05-11" in domain_html
    assert "../annotations.html?scope=domain&amp;linked_item=UKR%3AA&amp;annotation_type=lineage_note" in domain_html
    assert "Open Annotation Workflow for this Domain" in domain_html

    coverage_html = (pages.output_dir / "coverage.html").read_text()
    assert "Source / Coverage View" in coverage_html
    assert "Trust Summary" in coverage_html
    assert "Source status summary keeps live, failed, degraded, and prepared-adapter access visible at a glance." in coverage_html
    assert "Source Status" in coverage_html
    assert "failed" in coverage_html
    assert "prepared_adapter" in coverage_html
    assert "Coverage / Confidence Matrix" in coverage_html
    assert "Country Coverage / Gap Matrix" in coverage_html
    assert "Gap Cause" in coverage_html
    assert "source_failed_this_run" in coverage_html
    assert "source-SRC-A" in coverage_html
    assert "Diagnostics" in coverage_html
    assert "fetch_ok" in coverage_html
    assert "Confidence Band" in coverage_html
    assert "partial_success" in coverage_html
    assert "failed_source:SRC-B" in coverage_html
    assert "ACLED" in coverage_html
    assert "Degraded Sources" in coverage_html
    assert "Credential-gated Source Activation Readiness" in coverage_html
    assert "Credential-gated Source Activation Readiness Summary" in coverage_html
    assert "Provides a compact activation snapshot so operators can scan how many credential-gated sources are ready versus blocked before reading the detailed source table." in coverage_html
    assert "Total credential-gated sources" in coverage_html
    assert "Blocked missing credentials" in coverage_html
    assert "Configured-ready sources" in coverage_html
    assert "Blocked sources" in coverage_html
    assert "blocked_missing_credentials: 2" in coverage_html
    assert "SRC-UCDP-GED, SRC-RELIEFWEB" in coverage_html
    assert "operationally activatable in the current environment or still blocked by missing credentials/registrations" in coverage_html
    assert "SRC-UCDP-GED" in coverage_html
    assert "SRC-RELIEFWEB" in coverage_html
    assert "missing_credential:UCDP_API_TOKEN" in coverage_html
    assert "missing_credential:RELIEFWEB_APPNAME" in coverage_html
    assert "pre_approved_appname" in coverage_html
    assert "api_token" in coverage_html
    assert "Next Step" in coverage_html
    assert "The Next Step column turns each blocker/configured-ready state into the concrete follow-through action required for the first real credential-backed evidence run." in coverage_html
    assert "Set UCDP_API_TOKEN in the runtime environment and rerun the governed live pipeline." in coverage_html
    assert "Obtain an approved ReliefWeb appname, set RELIEFWEB_APPNAME, and rerun the governed live pipeline." in coverage_html
    assert "id='country-gap-UKR'" in coverage_html
    assert "class='coverage-focus-target'" in coverage_html
    assert "data-focus-country='UKR'" in coverage_html
    assert "data-focus-section='country_gap'" in coverage_html
    assert "data-missing-domains='D'" in coverage_html
    assert "coverage-focus-summary" in coverage_html
    assert "applyCoverageFocusState" in coverage_html
    assert "coverage-focus-target-active" in coverage_html
    assert "focus_target_count" in coverage_html
    assert "focus_country" in coverage_html
    assert "focus_section" in coverage_html

    reports_html = (pages.output_dir / "reports.html").read_text()
    assert "Report / Export View" in reports_html
    assert "REP-COVERAGE-001" in reports_html
    assert "Evidence Summary" in reports_html
    assert "Report Scope Controls" in reports_html
    assert "report-type-filter" in reports_html
    assert "report-id-filter" in reports_html
    assert "report-visible-count" in reports_html
    assert "class='report-row'" in reports_html
    assert "applyReportFilters" in reports_html
    assert "partial_success" in reports_html
    assert "SRC-B" in reports_html
    assert "SNAP-RUN-200-v1" in reports_html

    runs_html = (pages.output_dir / "runs.html").read_text()
    assert "System Status / Runs" in runs_html
    assert "partial_success" in runs_html
    assert "Operational Evidence Lane" in runs_html
    assert "MVP-COUNTRIES-LIVE-focus-complete-v1" in runs_html
    assert "Coverage scope: <strong>18/21</strong> updated" in runs_html
    assert "Countries without updates: <strong>3</strong>" in runs_html
    assert "Breadth coverage: <strong>breadth_partial_slice_updated</strong>" in runs_html
    assert "18/21 countries updated; missing updates remain in EST, MMR, QAT." in runs_html
    assert "Countries without updates (3)" in runs_html
    assert "EST" in runs_html and "MMR" in runs_html and "QAT" in runs_html
    assert "0.8571" in runs_html
    assert "blocked_by_known_gaps" in runs_html
    assert "runtime_degraded_and_release_blocked" in runs_html
    assert "Triage tag:" in runs_html
    assert "degraded_release_blocked" in runs_html
    assert "Runtime degraded and release blocked; review failed sources and known gaps first." in runs_html
    assert "Verification mode:" in runs_html
    assert "explicit_override_enabled" in runs_html
    assert "Enabled overrides:" in runs_html
    assert "allow_partial_success, allow_failed_sources" in runs_html
    assert "ready_green" in runs_html
    assert "Run is green and release-ready; suitable as the default handoff baseline." in runs_html
    assert "Latest known gaps (2)" in runs_html
    assert "Latest bundle evidence links" in runs_html
    assert "Latest bundle share refs" in runs_html
    assert "bundle:/tmp/siasa-gui-test" in runs_html
    assert "coverage_json:/tmp/siasa-gui-test/source_coverage.json" in runs_html
    assert "system_status_json:/tmp/siasa-gui-test/system_status.json" in runs_html
    assert "readiness_json:/tmp/siasa-gui-test/readiness.json" in runs_html
    assert "release_package_json:/tmp/siasa-gui-test/release_demo_package.json" in runs_html
    assert "release_gate_json:/tmp/siasa-gui-test/release_gate.json" in runs_html
    assert "Handoff summary:" in runs_html
    assert "Run RUN-200: bundle at /tmp/siasa-gui-test; review readiness_json:/tmp/siasa-gui-test/readiness.json, coverage_json:/tmp/siasa-gui-test/source_coverage.json, and release_gate_json:/tmp/siasa-gui-test/release_gate.json." in runs_html
    assert "Bundle root:" in runs_html
    assert "/tmp/siasa-gui-test-artifacts/RUN-200" in runs_html
    assert "/tmp/siasa-gui-test/index.html" in runs_html
    assert "href='/tmp/siasa-gui-test/index.html'" in runs_html
    assert "href='/tmp/siasa-gui-test/coverage.html'" in runs_html
    assert "href='/tmp/siasa-gui-test/source_coverage.json'" in runs_html
    assert "href='/tmp/siasa-gui-test/system_status.json'" in runs_html
    assert "href='/tmp/siasa-gui-test/readiness.html'" in runs_html
    assert "href='/tmp/siasa-gui-test/readiness.json'" in runs_html
    assert "href='/tmp/siasa-gui-test/release_package.html'" in runs_html
    assert "href='/tmp/siasa-gui-test/release_demo_package.json'" in runs_html
    assert "href='/tmp/siasa-gui-test/release_gate.json'" in runs_html
    assert ">Bundle</a> | <a href='/tmp/siasa-history/RUN-150/coverage.html'>Coverage</a> | <a href='/tmp/siasa-history/RUN-150/readiness.html'>Readiness</a> | <a href='/tmp/siasa-history/RUN-150/release_package.html'>Release</a>" in runs_html
    assert ">Coverage JSON</a> | <a href='/tmp/siasa-history/RUN-150/system_status.json'>System JSON</a> | <a href='/tmp/siasa-history/RUN-150/readiness.json'>Readiness JSON</a> | <a href='/tmp/siasa-history/RUN-150/release_demo_package.json'>Release JSON</a> | <a href='/tmp/siasa-history/RUN-150/release_gate.json'>Gate JSON</a>" in runs_html
    assert "bundle_root=/tmp/siasa-history/RUN-150" in runs_html
    assert "artifacts_dir=/tmp/siasa-history/RUN-150" in runs_html
    assert "bundle:/tmp/siasa-history/RUN-150" in runs_html
    assert "coverage_json:/tmp/siasa-history/RUN-150/source_coverage.json" in runs_html
    assert "system_status_json:/tmp/siasa-history/RUN-150/system_status.json" in runs_html
    assert "readiness_json:/tmp/siasa-history/RUN-150/readiness.json" in runs_html
    assert "release_package_json:/tmp/siasa-history/RUN-150/release_demo_package.json" in runs_html
    assert "release_gate_json:/tmp/siasa-history/RUN-150/release_gate.json" in runs_html
    assert "Run RUN-150: bundle at /tmp/siasa-history/RUN-150; review readiness_json:/tmp/siasa-history/RUN-150/readiness.json, coverage_json:/tmp/siasa-history/RUN-150/source_coverage.json, and release_gate_json:/tmp/siasa-history/RUN-150/release_gate.json." in runs_html
    assert "Coverage scope: 18/21 updated | without updates: 3" in runs_html
    assert "Countries without updates: EST, MMR, QAT" in runs_html
    assert "breadth_partial_slice_updated" in runs_html
    assert "18/21 countries updated; missing updates remain in EST, MMR, QAT." in runs_html
    assert "Coverage scope: 11/11 updated | without updates: 0" in runs_html
    assert "Countries without updates: none" in runs_html
    assert "breadth_full_slice_updated" in runs_html
    assert "All countries in the governed slice produced updates; this run is a full breadth proof for the selected slice." in runs_html
    assert "operational-evidence-history-table" in runs_html
    assert "operational-history-triage-filter" in runs_html
    assert "operational-history-recency-filter" in runs_html
    assert "operational-history-sort" in runs_html
    assert "operational-history-text-filter" in runs_html
    assert "operational-history-reset" in runs_html
    assert "operational-history-copy-link" in runs_html
    assert "operational-history-copy-summary" in runs_html
    assert "operational-history-export-json" in runs_html
    assert "operational-history-export-csv" in runs_html
    assert "operational-history-copy-csv" in runs_html
    assert "operational-history-preset-blocked-review" in runs_html
    assert "operational-history-preset-latest-only" in runs_html
    assert "operational-history-preset-ready-green" in runs_html
    assert "operational-history-preset-oldest-audit" in runs_html
    assert "data-operational-history-preset='blocked-review'" in runs_html
    assert "data-operational-history-preset='latest-only'" in runs_html
    assert "data-operational-history-preset='ready-green'" in runs_html
    assert "data-operational-history-preset='oldest-audit'" in runs_html
    assert "operational-history-link-status" in runs_html
    assert "Blocked review" in runs_html
    assert "Latest only" in runs_html
    assert "Ready green" in runs_html
    assert "Oldest audit" in runs_html
    assert "Latest first" in runs_html
    assert "Oldest first" in runs_html
    assert "Triage tag (A-Z)" in runs_html
    assert "run id, pilot set, triage, handoff" in runs_html
    assert "Recorded At" in runs_html
    assert "Hours Behind Latest" in runs_html
    assert "2026-05-11T18:00:00Z" in runs_html
    assert "2026-05-10T18:00:00Z" in runs_html
    assert ">0h<" in runs_html
    assert ">24h<" in runs_html
    assert "Verification Mode" in runs_html
    assert "Enabled Overrides" in runs_html
    assert "All triage tags (2)" in runs_html
    assert "All recency bands (2)" in runs_html
    assert "last_24h (1)" in runs_html
    assert "latest (1)" in runs_html
    assert "degraded_release_blocked (1)" in runs_html
    assert "ready_green (1)" in runs_html
    assert "Visible runs: <strong id='operational-history-visible-count'>2</strong>" in runs_html
    assert "Triage tag counts: <strong id='operational-history-triage-counts'>degraded_release_blocked: 1 | ready_green: 1</strong>" in runs_html
    assert "Recency band counts: <strong id='operational-history-recency-counts'>last_24h: 1 | latest: 1</strong>" in runs_html
    assert "Active history filter state: <strong id='operational-history-active-state'>triage=all | recency=all | search=none | sort=latest-first</strong>" in runs_html
    assert "Visible slice summary: <strong id='operational-history-visible-summary'>visible_runs=0 | run_ids=none | triage=none | recency=none | breadth=none | verification=none | overrides=none</strong>" in runs_html
    assert "operational-history-visible-payload" in runs_html
    assert "Visible slice payload" in runs_html
    assert "Visible triage counts: <strong id='operational-history-visible-triage-counts'>n/a</strong>" in runs_html
    assert "Visible recency counts: <strong id='operational-history-visible-recency-counts'>n/a</strong>" in runs_html
    assert "Visible breadth counts: <strong id='operational-history-visible-breadth-counts'>n/a</strong>" in runs_html
    assert "Visible verification counts: <strong id='operational-history-visible-verification-counts'>n/a</strong>" in runs_html
    assert "Visible override counts: <strong id='operational-history-visible-override-counts'>n/a</strong>" in runs_html
    assert "Visible governance digest: <strong id='operational-history-visible-governance-digest'>0 visible runs | triage: none | recency: none | breadth: none | verification: none | overrides: none</strong>" in runs_html
    assert "class='operational-history-row'" in runs_html
    assert "data-triage-tag='degraded_release_blocked'" in runs_html
    assert "data-triage-tag='ready_green'" in runs_html
    assert "data-recency-band='latest'" in runs_html
    assert "data-recency-band='last_24h'" in runs_html
    assert "data-hours-behind-latest='0'" in runs_html
    assert "data-hours-behind-latest='24'" in runs_html
    assert "data-history-search-text='run-150 2026-05-10t18:00:00z success extended-focus-complete mvp-countries-live-extended-focus-complete-v1 11 11 0 breadth_full_slice_updated all countries in the governed slice produced updates; this run is a full breadth proof for the selected slice. green pass ready release_ready ready_green" in runs_html
    assert "data-history-search-text='run-200 2026-05-11t18:00:00z partial_success focus-complete mvp-countries-live-focus-complete-v1 21 18 3 est mmr qat breadth_partial_slice_updated 18/21 countries updated; missing updates remain in est, mmr, qat. amber pass blocked_by_known_gaps runtime_degraded_and_release_blocked degraded_release_blocked" in runs_html
    assert "run is green and release-ready; suitable as the default handoff baseline. strict run" in runs_html
    assert "data-recorded-at='2026-05-11T18:00:00Z'" in runs_html
    assert "data-recorded-at='2026-05-10T18:00:00Z'" in runs_html
    assert "applyOperationalHistoryTriageFilter" in runs_html
    assert "sortOperationalHistoryRows" in runs_html
    assert "getOperationalHistoryState" in runs_html
    assert "serializeOperationalHistoryState" in runs_html
    assert "persistOperationalHistoryStateToHash" in runs_html
    assert "applyOperationalHistoryStateFromHash" in runs_html
    assert "copyOperationalHistoryFilterLink" in runs_html
    assert "buildOperationalHistoryVisibleSummary" in runs_html
    assert "buildOperationalHistoryVisibleGovernanceDigest" in runs_html
    assert "verification=${verificationModeSummary}" in runs_html
    assert "breadth=${breadthSummary}" in runs_html
    assert "overrides=${overrideSummary}" in runs_html
    assert "buildOperationalHistoryVisiblePayload" in runs_html
    assert "governance_digest: governanceDigest" in runs_html
    assert "verification_mode_counts: verificationModeCounts" in runs_html
    assert "breadth_coverage_counts: breadthCoverageCounts" in runs_html
    assert "override_profile_counts: overrideProfileCounts" in runs_html
    assert "visible_runs" in runs_html
    assert "run_ids" in runs_html
    assert "triage_counts" in runs_html
    assert "recency_counts" in runs_html
    assert "breadth_coverage_counts" in runs_html
    assert "verification_mode_counts" in runs_html
    assert "override_profile_counts" in runs_html
    assert "governance_digest" in runs_html
    assert "recorded_at" in runs_html
    assert "hours_behind_latest" in runs_html
    assert "run_status" in runs_html
    assert "pilot_set" in runs_html
    assert "country_set_id" in runs_html
    assert "combined_ce_ratio" in runs_html
    assert "governance_verdict" in runs_html
    assert "policy_gate_verdict" in runs_html
    assert "release_verdict" in runs_html
    assert "readiness_interpretation" in runs_html
    assert "verification_mode" in runs_html
    assert "enabled_overrides" in runs_html
    assert "triage_tag" in runs_html
    assert "'known_gap_count'," in runs_html
    assert "'failed_source_count'," in runs_html
    assert "'breadth_coverage_tag'," in runs_html
    assert "'breadth_coverage_summary'," in runs_html
    assert "row.getAttribute('data-breadth-coverage-tag')" in runs_html
    assert "row.getAttribute('data-breadth-coverage-summary')" in runs_html
    assert "copyOperationalHistoryVisibleSummary" in runs_html
    assert "exportOperationalHistoryVisiblePayload" in runs_html
    assert "buildOperationalHistoryVisibleCsv" in runs_html
    assert "exportOperationalHistoryVisibleCsv" in runs_html
    assert "copyOperationalHistoryVisibleCsv" in runs_html
    assert "Visible CSV copied." in runs_html
    assert "Visible CSV copy unavailable in this browser." in runs_html
    assert "operational_history_visible_slice.csv" in runs_html
    assert "text/csv;charset=utf-8" in runs_html
    assert "applyOperationalHistoryPreset" in runs_html
    assert "Preset applied: ${preset}." in runs_html
    assert "renderOperationalHistoryActiveState" in runs_html
    assert "resetOperationalHistoryFilters" in runs_html
    assert "oh_triage" in runs_html
    assert "oh_recency" in runs_html
    assert "oh_sort" in runs_html
    assert "oh_text" in runs_html
    assert "operational-history-visible-triage-counts" in runs_html
    assert "operational-history-visible-recency-counts" in runs_html
    assert "operational-history-visible-breadth-counts" in runs_html
    assert "operational-history-visible-verification-counts" in runs_html
    assert "operational-history-visible-override-counts" in runs_html
    assert "operational-history-visible-governance-digest" in runs_html
    assert "Repo Closure Summary" in runs_html
    assert "governance-and-run-controls" in runs_html
    assert "reporting-and-export" in runs_html

    trends_html = (pages.output_dir / "trends.html").read_text()
    assert "Yearly Trend Page" in trends_html
    assert "Trend Chart" in trends_html
    assert "Historical Comparison Summary" in trends_html
    assert "Net Change" in trends_html
    assert "Peak Label" in trends_html
    assert "Current vs First Label" in trends_html
    assert "2026-01" in trends_html
    assert "<svg" in trends_html
    assert "trend-range-btn" in trends_html
    assert "data-range='6m'" in trends_html
    assert "data-range='1y'" in trends_html
    assert "data-range='all'" in trends_html
    assert "trend-range-controls" in trends_html
    assert "data-idx=" in trends_html
    assert "_render_enhanced_trend_controls_js" or "Enhanced trend chart zoom" in trends_html

    events_html = (pages.output_dir / "events.html").read_text()
    assert "Current Events Page" in events_html
    assert "EVT-001" in events_html

    comparison_html = (pages.output_dir / "comparison.html").read_text()
    assert "Cross-Country Comparison" in comparison_html
    assert "Coverage / Confidence Comparison" in comparison_html
    assert "Comparison controls" in comparison_html
    assert "UKR" in comparison_html
    assert "S3" in comparison_html
    assert "multi-window-controls" in comparison_html
    assert "mw-country-left" in comparison_html
    assert "mw-country-right" in comparison_html
    assert "mw-panel-left" in comparison_html
    assert "mw-panel-right" in comparison_html
    assert "multi-window-panels" in comparison_html
    assert "renderMWPanel" in comparison_html
    assert "comparison-mode" in comparison_html
    assert "comparison-baseline" in comparison_html
    assert "renderComparisonBaseline" in comparison_html

    validation_html = (pages.output_dir / "validation.html").read_text()
    assert "Validation / Backtest" in validation_html
    assert "VAL-UKR-2022-001" in validation_html
    assert "Domain Match" in validation_html
    # UX uplift: structured panels replace raw section headings
    assert "Active Case" in validation_html  # was: "Review Summary"
    assert "Reference Case Portfolio" in validation_html  # was: "Reference Case Portfolio Summary"
    assert "Reference Case Portfolio" in validation_html  # was: "Validation Case Portfolio"
    assert "Non-Perfect Cases" in validation_html
    assert "Validation Realism Snapshot" in validation_html
    assert "Curated Reference Case Library" in validation_html
    assert "case_count" in validation_html or "Cases" in validation_html  # was: "Library Cases"
    assert "Historical Reference Reviews" in validation_html  # was: "Historical Reference Review Summary"
    assert "Historical Reference Reviews" in validation_html
    assert "average_evidence_score" in validation_html or "Ref. Evidence Score" in validation_html  # was: "Average Evidence Score"
    assert "historical_alignment_confirmed" in validation_html
    assert "verified_multi_source" in validation_html
    assert "Historical Replay Summary" in validation_html
    assert "Historical Replay Reviews" in validation_html
    assert "replay_match" in validation_html
    assert "replay_match_with_gaps" in validation_html
    assert "replay_mismatch" in validation_html
    assert "provider_backed_archival_replay" in validation_html
    assert "strong_replay_evidence" in validation_html
    assert "verified_replay_evidence" in validation_html
    assert "weak_replay_evidence" in validation_html
    assert "Replay Evidence Score" in validation_html  # was: "Average Replay Evidence Score"
    assert "replay_evidence_tier" in validation_html or "Evidence Tier" in validation_html  # was: "Replay Evidence Tiers"
    assert "Input Records" in validation_html  # was: "Replay Input Record Total"
    assert "Archival Files" in validation_html  # was: "Archival Data Files"
    assert "Source Coverage" in validation_html  # was: "Replay Source Coverage"
    assert "Replay Attention Watchlist" in validation_html
    assert "Attention Cases" in validation_html  # was: "Replay Attention Summary"
    assert "replay-attention-level-filter" in validation_html
    assert "replay-attention-owner-filter" in validation_html
    assert "replay-attention-reason-filter" in validation_html
    assert "replay-attention-verdict-filter" in validation_html
    assert "replay-attention-tier-filter" in validation_html
    assert "replay-attention-text-filter" in validation_html
    assert "replay-attention-reset" in validation_html
    assert "replay-attention-copy-link" in validation_html
    assert "replay-attention-visible-count" in validation_html
    assert "replay-attention-focus-target-count" in validation_html
    assert "replay-attention-active-state" in validation_html
    assert "replay-attention-visible-verdict-breakdown" in validation_html
    assert "replay-attention-link-status" in validation_html
    assert "applyReplayAttentionFilters" in validation_html
    assert "applyReplayAttentionFocusState" in validation_html
    assert "renderReplayAttentionActiveState" in validation_html
    assert "persistReplayAttentionStateToHash" in validation_html
    assert "applyReplayAttentionStateFromHash" in validation_html
    assert "copyReplayAttentionFilterLink" in validation_html
    assert "ra_level" in validation_html
    assert "ra_owner" in validation_html
    assert "ra_reason" in validation_html
    assert "ra_verdict" in validation_html
    assert "ra_tier" in validation_html
    assert "ra_text" in validation_html
    assert "verdictCounts" in validation_html
    assert "resetReplayAttentionFilters" in validation_html
    assert "replay-attention-card" in validation_html
    assert "replay-attention-focus-active" in validation_html
    assert "replay-attention-focus-target-count" in validation_html
    assert "scrollIntoView({behavior:'smooth', block:'center'})" in validation_html
    assert "id='attention-case-" in validation_html
    assert "hashPrefix='ra='" in validation_html
    assert "suggested_next_action" in validation_html or "Suggested action" in validation_html
    assert "attention_level" in validation_html or "Attention" in validation_html  # was: "Attention Level"
    assert "owner_hint" in validation_html or "Follow-up" in validation_html  # was: "Follow-up Owner"
    assert "validation governance" in validation_html
    assert "runtime/source coverage" in validation_html
    assert "attention_country_summary" in validation_html or "Country" in validation_html  # was: "Attention by Country"
    assert "status_mismatch_and_domain_gap" in validation_html
    assert "domain_coverage_gap" in validation_html
    assert "Review reference-case expectation alignment and archival replay provenance before using this case as a strong validation signal." in validation_html
    assert "Review missing expected domains and source coverage before treating this replay as fully representative." in validation_html
    assert "VAL-ISR-2024-002" in validation_html
    assert "VAL-POL-2024-002" in validation_html
    assert "archival_replay_inputs/VAL-UKR-2022-001.json" in validation_html
    assert "replay_input_record_count" in validation_html or "Records" in validation_html  # was: "Replay Input Records"
    assert "military_escalation" in validation_html
    assert "VAL-POL-2023-001" in validation_html
    assert "2022-02-01" in validation_html  # was: "2022-02-01 to 2024-05-31"
    assert "VAL-POL-2022-001" in validation_html
    assert "POL, UKR" in validation_html or "POL" in validation_html

    traceability_html = (pages.output_dir / "traceability.html").read_text()

    assert "historical-replay-country-filter" in validation_html
    assert "historical-replay-verdict-filter" in validation_html
    assert "historical-replay-basis-filter" in validation_html
    assert "historical-replay-text-filter" in validation_html
    assert "historical-replay-reset" in validation_html
    assert "historical-replay-visible-count" in validation_html
    assert "historical-replay-active-state" in validation_html
    assert "historical-replay-visible-verdict-breakdown" in validation_html
    assert "applyHistoricalReplayFilters" in validation_html
    assert "resetHistoricalReplayFilters" in validation_html
    assert "historical-replay-row" in validation_html
    assert "data-search-text" in validation_html
    assert "Changed Versions" in validation_html

    readiness_html = (pages.output_dir / "readiness.html").read_text()
    assert "Demo / Release Readiness" in readiness_html
    assert "Demo Verdict" in readiness_html
    assert "Release Verdict" in readiness_html
    assert "Gate Verdict" in readiness_html
    assert "Gate Verdict" in readiness_html
    assert "Release Readiness Index" in readiness_html
    assert "Release / Demo Package" in (pages.output_dir / "release_package.html").read_text()
    release_demo_package_json = json.loads((pages.output_dir / "release_demo_package.json").read_text())
    assert release_demo_package_json["decision_packet_send_readiness"]["overall_send_readiness"] == "blocked"
    assert release_demo_package_json["decision_packet_send_readiness"]["external_send_allowed"] is False
    assert "Prioritized items" in (pages.output_dir / "release_package.html").read_text()
    assert "Demo sequence" in (pages.output_dir / "release_package.html").read_text()
    assert "Guided review sequence" in (pages.output_dir / "release_package.html").read_text()
    assert "Reviewer question" in (pages.output_dir / "release_package.html").read_text()
    assert "Expected signal" in (pages.output_dir / "release_package.html").read_text()
    assert "Gate posture" in (pages.output_dir / "release_package.html").read_text()
    assert "Artifact handoff" in (pages.output_dir / "release_package.html").read_text()
    assert "Executive decision summary" in (pages.output_dir / "release_package.html").read_text()
    assert "Recommendation:" in (pages.output_dir / "release_package.html").read_text()
    assert "Decision confidence:" in (pages.output_dir / "release_package.html").read_text()
    assert "Strongest supporting evidence" in (pages.output_dir / "release_package.html").read_text()
    assert "Explicit limitations" in (pages.output_dir / "release_package.html").read_text()
    assert "Reviewer handoff and export summary" in (pages.output_dir / "release_package.html").read_text()
    assert "Next reviewer role" in (pages.output_dir / "release_package.html").read_text()
    assert "Canonical handoff artifact" in (pages.output_dir / "release_package.html").read_text()
    assert "Share/export now" in (pages.output_dir / "release_package.html").read_text()
    assert "Decision log seed" in (pages.output_dir / "release_package.html").read_text()
    assert "Review sign-off scaffold" in (pages.output_dir / "release_package.html").read_text()
    assert "Reviewer / approver" in (pages.output_dir / "release_package.html").read_text()
    assert "Decision status" in (pages.output_dir / "release_package.html").read_text()
    assert "Decision date" in (pages.output_dir / "release_package.html").read_text()
    assert "Bounded rationale" in (pages.output_dir / "release_package.html").read_text()
    assert "Follow-up actions" in (pages.output_dir / "release_package.html").read_text()
    assert "Stakeholder cover sheet" in (pages.output_dir / "release_package.html").read_text()
    assert "Audience" in (pages.output_dir / "release_package.html").read_text()
    assert "Requested decision" in (pages.output_dir / "release_package.html").read_text()
    assert "Top 3 caveats" in (pages.output_dir / "release_package.html").read_text()
    assert "Start here" in (pages.output_dir / "release_package.html").read_text()
    assert "External-share summary" in (pages.output_dir / "release_package.html").read_text()
    assert "Decision log export summary" in (pages.output_dir / "release_package.html").read_text()
    assert "Approval state" in (pages.output_dir / "release_package.html").read_text()
    assert "Requested decision linkage" in (pages.output_dir / "release_package.html").read_text()
    assert "Distribution bundle" in (pages.output_dir / "release_package.html").read_text()
    assert "Decision entry template" in (pages.output_dir / "release_package.html").read_text()
    assert "Reviewer disposition standard" in (pages.output_dir / "release_package.html").read_text()
    assert "Disposition options" in (pages.output_dir / "release_package.html").read_text()
    assert "approve_with_conditions" in (pages.output_dir / "release_package.html").read_text()
    assert "Selected disposition" in (pages.output_dir / "release_package.html").read_text()
    assert "Disposition rationale bounds" in (pages.output_dir / "release_package.html").read_text()
    assert "Follow-up owner" in (pages.output_dir / "release_package.html").read_text()
    assert "Disposition-aware action routing" in (pages.output_dir / "release_package.html").read_text()
    assert "Route trigger" in (pages.output_dir / "release_package.html").read_text()
    assert "Primary action bundle" in (pages.output_dir / "release_package.html").read_text()
    assert "Escalation / handoff route" in (pages.output_dir / "release_package.html").read_text()
    assert "Action owner" in (pages.output_dir / "release_package.html").read_text()
    assert "Decision packet seed" in (pages.output_dir / "release_package.html").read_text()
    assert "Packet headline" in (pages.output_dir / "release_package.html").read_text()
    assert "Decision snapshot" in (pages.output_dir / "release_package.html").read_text()
    assert "Share now packet" in (pages.output_dir / "release_package.html").read_text()
    assert "Decision packet note" in (pages.output_dir / "release_package.html").read_text()
    assert "Decision packet send-readiness checklist" in (pages.output_dir / "release_package.html").read_text()
    assert "Overall send readiness" in (pages.output_dir / "release_package.html").read_text()
    assert "External send allowed" in (pages.output_dir / "release_package.html").read_text()
    assert "Next unblocker" in (pages.output_dir / "release_package.html").read_text()
    assert "reviewer_signoff_captured" in (pages.output_dir / "release_package.html").read_text()
    assert "blocked" in (pages.output_dir / "release_package.html").read_text()
    assert "Resolve the blocking package issue before any external distribution." in (pages.output_dir / "release_package.html").read_text()
    assert "Evidence bundle" in (pages.output_dir / "release_package.html").read_text()
    assert "stakeholder_e2e_flows_covered" in readiness_html
    assert "Stakeholder E2E Flow Coverage (AP-04/AP-05)" in readiness_html
    assert "Stakeholder E2E UI Smoke Coverage (AP-07/AP-08)" in readiness_html
    assert "Stakeholder Functional Closure Focus Cluster" in readiness_html
    assert "Release Gate Blockers" in readiness_html

    assert "validation_backtest" in readiness_html
    assert "present" in readiness_html
    assert "ready" in readiness_html
    assert "blocked_by_known_gaps" in readiness_html
    assert "failed_source:SRC-B" in readiness_html
    assert "country_without_update:POL" in readiness_html
    assert "Source / Coverage" in readiness_html
    assert "Validation / Backtest" in readiness_html

    traceability_html = (pages.output_dir / "traceability.html").read_text()
    assert "Traceability / Lineage" in traceability_html
    assert "RAW-SRC-A-1" in traceability_html
    assert "REP-DAILY-RUN-200" in traceability_html
    assert "Source Dependency" in traceability_html  # was: "Source Dependency Groundwork"
    assert "Cluster Candidates" in traceability_html
    assert "A_article_count" in traceability_html
    assert "SRC-A, SRC-B" in traceability_html
    assert "Observed Lag (min)" in traceability_html
    assert "tight_temporal_coupling_candidate" in traceability_html
    assert "Source-Origin Groundwork" in traceability_html
    assert "First Observed (window)" in traceability_html
    assert "earliest_observed_source_in_window" in traceability_html
    assert "later_observed_source_in_window" in traceability_html

    annotations_html = (pages.output_dir / "annotations.html").read_text()
    assert "Analyst Annotations View" in annotations_html
    assert "Snapshot review pending source outage assessment." in annotations_html
    assert "UKR:A" in annotations_html
    assert "Create / Edit Annotation Workflow" in annotations_html
    assert "Replay-attention Prefill Summary" in annotations_html
    assert "replay-attention-prefill-summary" in annotations_html
    assert "annotation-editor-form" in annotations_html
    assert "annotation-scope-filter" in annotations_html
    assert "annotation-review-filter" in annotations_html
    assert "annotation-linked-item-filter" in annotations_html
    assert "Save Draft Annotation" in annotations_html
    assert "Export Draft Annotations" in annotations_html
    assert "Draft History" in annotations_html
    assert "siasa_annotation_workflow_v1" in annotations_html
    assert "prefillAnnotationFromQuery" in annotations_html
    assert "renderReplayAttentionPrefillSummary" in annotations_html
    assert "collectReplayAttentionPrefillContextFromQuery" in annotations_html
    assert "countryId: (params.get('country_id') || '').trim()" in annotations_html
    assert "caseId: (params.get('case_id') || '').trim()" in annotations_html
    assert "attentionReason: (params.get('attention_reason') || '').trim()" in annotations_html
    assert "ownerHint: (params.get('owner_hint') || '').trim()" in annotations_html
    assert "suggestedNextAction: (params.get('suggested_next_action') || '').trim()" in annotations_html
    assert "attentionLevel: (params.get('attention_level') || '').trim().toLowerCase()" in annotations_html
    assert "validateReplayAttentionPrefillContext" in annotations_html
    assert "replayEvidenceTier: (params.get('replay_evidence_tier') || '').trim().toLowerCase()" in annotations_html
    assert "reviewVerdict: (params.get('review_verdict') || '').trim().toLowerCase()" in annotations_html
    assert "replayEvidenceScore: (params.get('replay_evidence_score') || '').trim()" in annotations_html
    assert "domainMatchRatio: (params.get('domain_match_ratio') || '').trim()" in annotations_html
    assert "missingExpectedDomains: (params.get('missing_expected_domains') || '').trim()" in annotations_html
    assert "unexpectedObservedDomains: (params.get('unexpected_observed_domains') || '').trim()" in annotations_html
    assert "Replay-attention prefill missing fields:" in annotations_html
    assert "Prefilled replay-attention workflow for" in annotations_html
    assert "severityByAttentionLevel" in annotations_html
    assert "confidenceByReplayTier" in annotations_html
    assert "reviewStatusByVerdict" in annotations_html
    assert "document.getElementById('annotation-review-status-input').value = reviewStatusByVerdict[reviewVerdict];" in annotations_html
    assert "verified_replay_evidence" in annotations_html
    assert "strong_replay_evidence" in annotations_html
    assert "weak_replay_evidence" in annotations_html
    assert "Replay evidence:" in annotations_html
    assert "domain_match_ratio=" in annotations_html
    assert "missing_expected_domains=" in annotations_html
    assert "unexpected_observed_domains=" in annotations_html
    assert "missingExpectedDomains.split(',')" in annotations_html
    assert "unexpectedObservedDomains.split(',')" in annotations_html
    assert "Replay attention follow-up for" in annotations_html
    assert "setWorkflowStatus(`Prefilled workflow for ${linkedItems.join(', ')}.`);" in annotations_html
    assert "loadAnnotationIntoEditor" in annotations_html
    assert "function mergedAnnotationsById()" in annotations_html
    assert "const all = Array.from(mergedAnnotationsById().values());" in annotations_html
    assert "function escapeAnnotationHtml(value)" in annotations_html
    assert "${escapeAnnotationHtml(annotation.author || '')}" in annotations_html


def test_build_local_mvp_site_suppresses_country_drill_down_links_without_generated_country_pages(tmp_path: Path) -> None:
    pages = build_local_mvp_site(
        output_dir=tmp_path / "site",
        world_map_read_model={
            "baseline_mode": "Combined 30/90/365",
            "active_domains": ["A", "D"],
            "countries": [
                {"country_id": "UKR", "status": "S3", "active_domains": ["A", "D"], "drill_down_target": "/countries/UKR"},
                {"country_id": "POL", "status": "S1", "active_domains": ["A", "D"], "drill_down_target": "/countries/POL"},
            ],
        },
        country_profile_read_models={
            "UKR": {
                "country_id": "UKR",
                "multi_domain_status": "S3",
                "domain_states": {"A": "D3"},
                "trends": {"yearly": []},
                "drivers": [],
                "linked_events": [],
                "coverage": 0.84,
                "confidence": 0.73,
                "counter_indicators": [],
                "uncertainty": [],
            }
        },
        domain_detail_read_models={},
        source_coverage_read_model={"sources": [], "failed_sources": [], "missing_sources": []},
        report_catalog={},
        system_status_read_model={
            "run_id": "RUN-200",
            "run_status": "success",
            "active_domains": ["A", "D"],
            "coverage": {"countries_total": 2, "countries_with_updates": 1},
            "failed_sources": [],
            "available_reports": [],
            "snapshot_id": "SNAP-RUN-200-v1",
            "reprocessing_status": "idle",
            "last_run": "2026-05-11T18:00:00Z",
        },
    )

    index_html = (pages.output_dir / "index.html").read_text()
    assert "<a href='countries/UKR.html'>UKR</a>" in index_html
    assert "countries/UKR.html" in index_html
    assert "<a href='countries/POL.html'>POL</a>" not in index_html
    assert "countries/POL.html" not in index_html
    assert not (pages.output_dir / "countries" / "POL.html").exists()



def test_build_local_mvp_site_emits_only_resolvable_internal_html_links(tmp_path: Path) -> None:
    pages = build_local_mvp_site(
        output_dir=tmp_path / "site",
        world_map_read_model={
            "baseline_mode": "Combined 30/90/365",
            "active_domains": ["A", "B", "D"],
            "countries": [
                {"country_id": "UKR", "status": "S3", "active_domains": ["A", "B", "D"], "drill_down_target": "/countries/UKR"},
            ],
        },
        country_profile_read_models={
            "UKR": {
                "country_id": "UKR",
                "multi_domain_status": "S3",
                "domain_states": {"A": "D3", "B": "D2", "D": "D1"},
                "trends": {"yearly": ["2025-11", "2025-12", "2026-01"]},
                "drivers": ["A_news_volume"],
                "linked_events": ["EVT-001"],
                "coverage": 0.84,
                "confidence": 0.73,
                "counter_indicators": ["D_macro_stability"],
                "uncertainty": ["partial_success"],
            }
        },
        domain_detail_read_models={
            ("UKR", "A"): {
                "country_id": "UKR",
                "domain": "A",
                "time_series": [{"timestamp": "2026-05-11", "value": 0.67}],
                "baseline_comparison": {"current_window": 0.67, "baseline_30d": 0.31, "delta_to_baseline": 0.36},
                "feature_values": [{"feature_id": "A_article_count", "value": 12.0, "coverage": 0.9}],
                "source_context": [{"source_id": "SRC-A", "freshness_hours": 6, "history_horizon": "3y", "status": "success"}],
                "anomaly_state": "D3",
                "uncertainty": ["source_bias_possible"],
            }
        },
        source_coverage_read_model={"sources": [], "failed_sources": [], "missing_sources": []},
        report_catalog={},
        system_status_read_model={
            "run_id": "RUN-200",
            "run_status": "success",
            "active_domains": ["A", "B", "D"],
            "coverage": {"countries_total": 1, "countries_with_updates": 1},
            "failed_sources": [],
            "available_reports": [],
            "snapshot_id": "SNAP-RUN-200-v1",
            "reprocessing_status": "idle",
            "last_run": "2026-05-11T18:00:00Z",
        },
    )

    html_files = sorted(pages.output_dir.rglob("*.html"))
    assert (pages.output_dir / "readiness.html") in html_files
    broken_links: list[tuple[str, str]] = []
    for html_file in html_files:
        for href in _internal_hrefs(html_file.read_text()):
            resolved_target = html.unescape(href).split('?', 1)[0].split('#', 1)[0]
            if Path(resolved_target).suffix and not (html_file.parent / resolved_target).resolve().exists():
                broken_links.append((html_file.relative_to(pages.output_dir).as_posix(), href))

    assert broken_links == []



def test_build_local_mvp_site_copies_report_export_files_and_renders_download_links(tmp_path: Path) -> None:
    export_source_dir = tmp_path / "artifact_exports"
    export_source_dir.mkdir()
    markdown_export = export_source_dir / "daily_snapshot.md"
    json_export = export_source_dir / "daily_snapshot.json"
    markdown_export.write_text("# Daily Snapshot\n")
    json_export.write_text('{"snapshot_id": "SNAP-RUN-200-v1"}')

    repo_closure_view = {
        "summary": {"slice_count": 4, "requirement_count": 18, "closed": 18, "at_risk": 0},
        "slices": [
            {"slice_id": "governance-and-run-controls", "summary": {"closed": 6, "at_risk": 0}},
            {"slice_id": "reporting-and-export", "summary": {"closed": 4, "at_risk": 0}},
        ],
    }

    pages = build_local_mvp_site(
        output_dir=tmp_path / "site",
        world_map_read_model={"baseline_mode": "Combined 30/90/365", "active_domains": ["A"], "countries": []},
        country_profile_read_models={},
        domain_detail_read_models={},
        source_coverage_read_model={"sources": [], "failed_sources": [], "missing_sources": []},
        report_catalog={
            "daily_snapshot": {
                "report_id": "REP-DAILY-RUN-200",
                "format": "json+markdown",
                "snapshot_id": "SNAP-RUN-200-v1",
                "uncertainty": ["partial_success"],
                "failed_sources": ["SRC-B"],
                "export_files": [
                    {"label": "Markdown", "format": "md", "path": str(markdown_export), "relative_path": "exports/daily_snapshot.md"},
                    {"label": "JSON", "format": "json", "path": str(json_export), "relative_path": "exports/daily_snapshot.json"},
                ],
            }
        },
        system_status_read_model={
            "run_id": "RUN-200",
            "run_status": "success",
            "active_domains": ["A"],
            "coverage": {"countries_total": 2, "countries_with_updates": 1},
            "failed_sources": [],
            "available_reports": ["REP-DAILY-RUN-200", "REP-COUNTRY-UKR"],
            "snapshot_id": "SNAP-RUN-100-v1",
            "reprocessing_status": "idle",
            "last_run": "2026-05-10T12:00:00Z",
        },
        repo_closure_view_model=repo_closure_view,
    )

    reports_html = (pages.output_dir / "reports.html").read_text()
    assert "exports/daily_snapshot.md" in reports_html
    assert "exports/daily_snapshot.json" in reports_html
    assert "Evidence Summary" in reports_html
    assert "Report Scope Controls" in reports_html
    assert "report-type-filter" in reports_html
    assert "report-id-filter" in reports_html
    assert "report-visible-count" in reports_html
    assert "class='report-row'" in reports_html
    assert "partial_success" in reports_html
    assert "SRC-B" in reports_html
    assert "SNAP-RUN-200-v1" in reports_html
    assert (pages.output_dir / "exports" / "daily_snapshot.md").read_text() == "# Daily Snapshot\n"
    assert (pages.output_dir / "exports" / "daily_snapshot.json").read_text() == '{"snapshot_id": "SNAP-RUN-200-v1"}'

    runs_html = (pages.output_dir / "runs.html").read_text()
    assert "Repo Closure Summary" in runs_html
    assert "governance-and-run-controls" in runs_html
    assert "reporting-and-export" in runs_html


def test_load_site_payload_from_artifacts_reads_persisted_json_bundle(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    (artifacts_dir / "readmodels" / "country_profiles").mkdir(parents=True)
    (artifacts_dir / "readmodels" / "domain_details").mkdir(parents=True)
    (artifacts_dir / "reports").mkdir(parents=True)

    snapshot = {
        "snapshot_id": "SNAP-RUN-300-v1",
        "run_id": "RUN-300",
        "country_set_id": "MVP-COUNTRIES-v1",
        "active_domains": ["A", "B", "D"],
        "rule_versions": {"domain_status": "rules-2026-05"},
        "source_state": {"SRC-A": "success", "SRC-B": "failed"},
        "analytical_outputs": {"country_status": {"UKR": "S3"}},
        "status": "partial_success",
        "algorithm_version": "alg-0.1",
        "data_version": "data-0.1",
    }
    world_map = {
        "baseline_mode": "Combined 30/90/365",
        "active_domains": ["A", "B", "D"],
        "countries": [{"country_id": "UKR", "status": "S3", "active_domains": ["A", "B", "D"]}],
    }
    country_profile = {
        "country_id": "UKR",
        "multi_domain_status": "S3",
        "domain_states": {"A": "D3", "B": "D2", "D": "D1"},
        "trends": {"yearly": ["2025-11", "2025-12", "2026-01"]},
        "drivers": ["A_news_volume"],
        "linked_events": ["EVT-301"],
        "coverage": 0.84,
        "confidence": 0.73,
        "counter_indicators": ["D_macro_stability"],
        "uncertainty": ["partial_success"],
        "annotations": ["ANN-301"],
    }
    domain_detail = {
        "country_id": "UKR",
        "domain": "A",
        "anomaly_state": "D3",
        "time_series": [{"timestamp": "2026-05-11", "value": 0.67}],
        "baseline_comparison": {"current_window": 0.67, "baseline_30d": 0.31, "delta_to_baseline": 0.36},
        "feature_values": [{"feature_id": "A_article_count", "value": 12.0, "coverage": 0.9}],
        "source_context": [{"source_id": "SRC-A", "freshness_hours": 6, "history_horizon": "3y", "status": "success"}],
        "uncertainty": ["source_bias_possible"],
    }
    source_coverage = {
        "sources": [{"source_id": "SRC-A", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.9}],
        "failed_sources": ["SRC-B"],
        "missing_sources": ["SRC-C"],
    }
    system_status = {
        "run_id": "RUN-300",
        "run_status": "partial_success",
        "active_domains": ["A", "B", "D"],
        "coverage": {"countries_total": 30, "countries_with_updates": 27},
        "failed_sources": ["SRC-B"],
        "available_reports": ["REP-DAILY-SNAP-RUN-300-v1", "REP-COUNTRY-UKR"],
        "snapshot_id": "SNAP-RUN-300-v1",
        "reprocessing_status": "idle",
        "last_run": "2026-05-11T18:00:00Z",
    }
    reports = {
        "daily_snapshot": {
            "report_id": "REP-DAILY-SNAP-RUN-300-v1",
            "report_type": "daily_snapshot",
            "format": "json",
            "payload": {"snapshot_id": "SNAP-RUN-300-v1", "status": "partial_success"},
        },
        "country_profile": {
            "report_id": "REP-COUNTRY-UKR",
            "report_type": "country_profile",
            "format": "json",
            "payload": {"country_id": "UKR", "multi_domain_status": "S3"},
        },
    }
    validation_view = {
        "case_id": "VAL-UKR-2022-001",
        "country_id": "UKR",
        "case_name": "Escalation reference case",
        "time_range": {"start": "2022-02-01", "end": "2022-03-01"},
        "expected_domains": ["A", "B", "D"],
        "observed_domains": ["A", "B"],
        "domain_match_ratio": 2 / 3,
        "status_match": True,
        "expected_pattern": "Aligned information, event, and economic stress escalation.",
        "validation_goal": "Check multi-domain alignment detection.",
        "reference_sources": ["SRC-A", "SRC-B"],
        "validation_metrics": ["Domain Match", "Status Match"],
        "known_limitations": ["historical coverage incomplete"],
        "reprocessing_comparison": {"prior_snapshot_id": "SNAP-RUN-001-v1", "new_snapshot_id": "SNAP-RUN-001-v2", "changed_versions": ["rule_version"]},
    }
    traceability_view = {
        "lineage_records": [
            {
                "source_id": "SRC-A",
                "raw_record_id": "RAW-SRC-A-1",
                "normalized_id": "NORM-SRC-A-1",
                "feature_id": "A_article_count",
                "domain_status_id": "DST-UKR-A-RUN-300",
                "multi_domain_status_id": "MST-UKR-RUN-300",
                "snapshot_id": "SNAP-RUN-300-v1",
                "observed_at": "2026-05-11T17:00:00Z",
                "report_id": "REP-DAILY-SNAP-RUN-300-v1",
            }
        ]
    }
    annotations_view = {
        "annotations": [
            {
                "annotation_id": "ANN-301",
                "created_at": "2026-05-11T18:05:00Z",
                "author": "analyst",
                "scope": "country",
                "annotation_type": "context_note",
                "severity_assessment": "relevant",
                "confidence_assessment": "medium",
                "text": "Country profile reviewed against replicated reporting.",
                "tags": ["review"],
                "linked_items": ["UKR"],
                "review_status": "draft",
            }
        ],
        "by_scope": {"country": ["ANN-301"]},
        "by_linked_item": {"UKR": ["ANN-301"]},
    }

    (artifacts_dir / "snapshot.json").write_text(json.dumps(snapshot))
    (artifacts_dir / "readmodels" / "world_map.json").write_text(json.dumps(world_map))
    (artifacts_dir / "readmodels" / "source_coverage.json").write_text(json.dumps(source_coverage))
    (artifacts_dir / "readmodels" / "system_status.json").write_text(json.dumps(system_status))
    (artifacts_dir / "readmodels" / "country_profiles" / "UKR.json").write_text(json.dumps(country_profile))
    (artifacts_dir / "readmodels" / "domain_details" / "UKR__A.json").write_text(json.dumps(domain_detail))
    repo_closure_view = {
        "summary": {"slice_count": 4, "requirement_count": 18, "closed": 18, "at_risk": 0},
        "slice_ids": [
            "governance-and-run-controls",
            "gui-readmodels-and-annotations",
            "reporting-and-export",
            "validation-and-backtest",
        ],
        "slices": [
            {"slice_id": "governance-and-run-controls", "summary": {"closed": 6, "at_risk": 0}},
            {"slice_id": "gui-readmodels-and-annotations", "summary": {"closed": 6, "at_risk": 0}},
        ],
    }
    (artifacts_dir / "readmodels" / "validation_backtest.json").write_text(json.dumps(validation_view))
    (artifacts_dir / "readmodels" / "traceability_lineage.json").write_text(json.dumps(traceability_view))
    (artifacts_dir / "readmodels" / "repo_closure.json").write_text(json.dumps(repo_closure_view))
    (artifacts_dir / "readmodels" / "annotations.json").write_text(json.dumps(annotations_view))
    for report_name, report_payload in reports.items():
        (artifacts_dir / "reports" / f"{report_name}.json").write_text(json.dumps(report_payload))

    payload = local_app.load_site_payload_from_artifacts(artifacts_dir)

    assert payload["world_map_read_model"]["countries"][0]["country_id"] == "UKR"
    assert payload["country_profile_read_models"]["UKR"]["annotations"] == ["ANN-301"]
    assert payload["domain_detail_read_models"][("UKR", "A")]["anomaly_state"] == "D3"
    assert payload["source_coverage_read_model"]["failed_sources"] == ["SRC-B"]
    assert payload["system_status_read_model"]["snapshot_id"] == "SNAP-RUN-300-v1"
    assert payload["report_catalog"]["daily_snapshot"]["report_id"] == "REP-DAILY-SNAP-RUN-300-v1"
    assert payload["validation_view_model"]["case_id"] == "VAL-UKR-2022-001"
    assert payload["traceability_view_model"]["lineage_records"][0]["raw_record_id"] == "RAW-SRC-A-1"
    assert payload["repo_closure_view_model"]["summary"] == {"slice_count": 4, "requirement_count": 18, "closed": 18, "at_risk": 0}
    assert payload["annotations_view_model"]["by_linked_item"]["UKR"] == ["ANN-301"]



def test_build_local_mvp_site_from_multi_country_artifact_bundle(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    (artifacts_dir / "readmodels" / "country_profiles").mkdir(parents=True)
    (artifacts_dir / "readmodels" / "domain_details").mkdir(parents=True)
    (artifacts_dir / "reports").mkdir(parents=True)

    (artifacts_dir / "snapshot.json").write_text(
        json.dumps(
            {
                "snapshot_id": "SNAP-RUN-350-v1",
                "run_id": "RUN-350",
                "country_set_id": "MVP-COUNTRIES-v1",
                "active_domains": ["A", "B"],
                "rule_versions": {"domain_status": "rules-2026-05"},
                "source_state": {"SRC-A": "success", "SRC-B": "success"},
                "analytical_outputs": {"country_status": {"POL": "S3", "UKR": "S3"}},
                "status": "success",
                "algorithm_version": "alg-0.1",
                "data_version": "data-0.1",
            }
        )
    )
    (artifacts_dir / "readmodels" / "world_map.json").write_text(
        json.dumps(
            {
                "baseline_mode": "Combined 30/90/365",
                "active_domains": ["A", "B"],
                "countries": [
                    {"country_id": "POL", "status": "S3", "active_domains": ["A", "B"]},
                    {"country_id": "UKR", "status": "S3", "active_domains": ["A", "B"]},
                ],
            }
        )
    )
    for country_id, event_id, trend, domain_states, uncertainty, coverage, confidence in (
        ("POL", "EVT-POL-350", [{"label": "2026-02", "value": 0.61}], {"A": "D3"}, ["partial_signal_loss"], 0.42, 0.88),
        ("UKR", "EVT-UKR-350", [{"label": "2026-01", "value": 0.77}], {"A": "D4", "B": "D3"}, [], 0.91, 0.46),
    ):
        (artifacts_dir / "readmodels" / "country_profiles" / f"{country_id}.json").write_text(
            json.dumps(
                {
                    "country_id": country_id,
                    "multi_domain_status": "S3",
                    "domain_states": domain_states,
                    "trends": {"yearly": trend},
                    "drivers": ["A_news_volume"],
                    "linked_events": [event_id],
                    "coverage": coverage,
                    "confidence": confidence,
                    "counter_indicators": [],
                    "uncertainty": uncertainty,
                    "annotations": [],
                    "country_context": {
                        "priority": "P2" if country_id == "POL" else "P1",
                        "selection_type": "Extended Focus" if country_id == "POL" else "Core Focus",
                        "region": "Europe / NATO East" if country_id == "POL" else "Europe / Black Sea",
                    },
                    "source_depth": {"source_ids": ["SRC-A"] if country_id == "POL" else ["SRC-A", "SRC-B"], "source_count": 1 if country_id == "POL" else 2},
                    "domain_gap_summary": {
                        "expected_domains": ["A", "B"],
                        "observed_domains": sorted(domain_states.keys()),
                        "missing_domains": ["B"] if country_id == "POL" else [],
                        "gap_details": [
                            {
                                "domain": "B",
                                "reason": "no_usable_input_data",
                                "source_ids": ["SRC-B"],
                                "source_reason_details": [
                                    {"source_id": "SRC-B", "reason": "records_only_for_other_countries_in_scope", "diagnostics": "ukr_only_window", "action_category": "scope_config_problem", "severity": "medium"}
                                ],
                            }
                        ] if country_id == "POL" else [],
                    },
                }
            )
        )
        (artifacts_dir / "readmodels" / "domain_details" / f"{country_id}__A.json").write_text(
            json.dumps(
                {
                    "country_id": country_id,
                    "domain": "A",
                    "anomaly_state": "D3",
                    "time_series": [{"timestamp": "2026-05-11", "value": 0.67}],
                    "baseline_comparison": {"delta_to_baseline": 0.36},
                    "feature_values": [{"feature_id": "A_article_count", "value": 12.0, "coverage": 0.9}],
                    "source_context": [{"source_id": "SRC-A", "freshness_hours": 6, "history_horizon": "3y", "status": "success"}],
                    "uncertainty": [],
                }
            )
        )
    (artifacts_dir / "readmodels" / "source_coverage.json").write_text(
        json.dumps(
            {
                "sources": [
                    {"source_id": "SRC-A", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.9, "record_count": 5, "diagnostics": "fetch_ok"},
                    {"source_id": "SRC-B", "status": "success", "history_horizon": "3y", "freshness_hours": 12, "confidence": 0.8, "record_count": 3, "diagnostics": "fetch_ok"},
                ],
                "failed_sources": [],
                "missing_sources": [],
            }
        )
    )
    (artifacts_dir / "readmodels" / "system_status.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-350",
                "run_status": "success",
                "active_domains": ["A", "B"],
                "coverage": {"countries_total": 2, "countries_with_updates": 2},
                "failed_sources": [],
                "available_reports": ["REP-DAILY-SNAP-RUN-350-v1", "REP-COUNTRY-POL", "REP-COUNTRY-UKR"],
                "snapshot_id": "SNAP-RUN-350-v1",
                "reprocessing_status": "idle",
                "last_run": "2026-05-11T18:00:00Z",
                "country_coverage_visibility": {
                    "priority_summary": [
                        {"priority": "P1", "country_count": 1, "countries": ["UKR"]},
                        {"priority": "P2", "country_count": 1, "countries": ["POL"]},
                    ],
                    "source_depth_band_summary": [
                        {"band": "minimal", "country_count": 1, "countries": ["POL"]},
                        {"band": "moderate", "country_count": 1, "countries": ["UKR"]},
                    ],
                    "freshness_band_summary": [
                        {"band": "fresh", "country_count": 2, "countries": ["POL", "UKR"]},
                        {"band": "aging", "country_count": 0, "countries": []},
                        {"band": "stale", "country_count": 0, "countries": []},
                        {"band": "unknown", "country_count": 0, "countries": []},
                    ],
                    "country_freshness_rows": [
                        {"country_id": "POL", "freshness_hours": 12.0, "freshness_band": "fresh", "priority": "P2", "source_depth_band": "minimal"},
                        {"country_id": "UKR", "freshness_hours": 6.0, "freshness_band": "fresh", "priority": "P1", "source_depth_band": "moderate"},
                    ],
                    "country_gap_rows": [
                        {
                            "country_id": "POL",
                            "priority": "P2",
                            "source_count": 1,
                            "source_depth_band": "minimal",
                            "freshness_hours": 12.0,
                            "freshness_band": "fresh",
                            "missing_domains": ["B"],
                            "missing_domain_count": 1,
                            "gap_details": [
                                {
                                    "domain": "B",
                                    "reason": "no_usable_input_data",
                                    "source_ids": ["SRC-B"],
                                    "source_reason_details": [
                                        {"source_id": "SRC-B", "reason": "records_only_for_other_countries_in_scope", "diagnostics": "ukr_only_window", "action_category": "scope_config_problem", "severity": "medium"}
                                    ],
                                }
                            ],
                        },
                    ],
                    "missing_domain_totals": {"B": 1},
                    "remediation_watchlist": [
                        {
                            "priority_rank": 1,
                            "priority_score": 111,
                            "action_category": "scope_config_problem",
                            "severity": "medium",
                            "country_count": 1,
                            "source_count": 1,
                            "countries": ["POL"],
                            "source_ids": ["SRC-B"],
                            "suggested_next_action": "Review country scope and source applicability configuration for the affected source.",
                            "owner_hint": "runtime/source configuration",
                            "evidence_link": "coverage.html#source-SRC-B",
                        }
                    ],
                },
            }
        )
    )
    (artifacts_dir / "reports" / "daily_snapshot.json").write_text(
        json.dumps(
            {
                "report_id": "REP-DAILY-SNAP-RUN-350-v1",
                "report_type": "daily_snapshot",
                "format": "json",
                "payload": {"snapshot_id": "SNAP-RUN-350-v1", "status": "success"},
            }
        )
    )
    (artifacts_dir / "reports" / "country_profile_POL.json").write_text(
        json.dumps({"report_id": "REP-COUNTRY-POL", "report_type": "country_profile", "format": "json", "payload": {"country_id": "POL", "multi_domain_status": "S3"}})
    )
    (artifacts_dir / "reports" / "country_profile_UKR.json").write_text(
        json.dumps({"report_id": "REP-COUNTRY-UKR", "report_type": "country_profile", "format": "json", "payload": {"country_id": "UKR", "multi_domain_status": "S3"}})
    )

    payload = local_app.load_site_payload_from_artifacts(artifacts_dir)
    pages = build_local_mvp_site(output_dir=tmp_path / "site", **payload)

    index_html = (pages.output_dir / "index.html").read_text()
    trends_html = (pages.output_dir / "trends.html").read_text()
    events_html = (pages.output_dir / "events.html").read_text()

    assert (pages.output_dir / "countries" / "POL.html").exists()
    assert (pages.output_dir / "countries" / "UKR.html").exists()
    assert (pages.output_dir / "domains" / "POL-A.html").exists()
    assert (pages.output_dir / "domains" / "UKR-A.html").exists()
    assert (pages.output_dir / "comparison.html").exists()
    assert "countries/POL.html" in index_html
    assert "countries/UKR.html" in index_html
    assert "data-country-id='POL'" in index_html
    assert "data-active-domains='A,B'" in index_html
    assert "Priority" in index_html
    assert "Source Depth" in index_html
    assert "Freshness" in index_html
    assert "Domain Gaps" in index_html
    assert "Priority Filter" in index_html
    assert "option value='P2'" in index_html
    assert "Source Depth Band Summary" in index_html
    assert "Country Coverage / Gap Watchlist" in index_html
    assert "Remediation Watchlist" in index_html
    assert "Priority Rank" in index_html
    assert "Priority Score" in index_html
    assert "scope_config_problem" in index_html
    assert "111" in index_html
    assert "Review country scope and source applicability configuration for the affected source." in index_html
    assert "runtime/source configuration" in index_html
    assert "coverage.html#source-SRC-B" in index_html
    assert "Gap Cause" in index_html
    assert "missing:B" in index_html
    assert "no_usable_input_data" in index_html
    assert "SRC-B" in index_html
    assert "records_only_for_other_countries_in_scope" in index_html
    assert "scope_config_problem" in index_html
    assert "severity=medium" in index_html
    assert "ukr_only_window" in index_html
    assert "data-priority='P2'" in index_html
    assert "data-freshness-band='fresh'" in index_html
    assert "fresh (12h)" in index_html
    assert "fresh (6h)" in index_html
    assert "Freshness Band Summary" in index_html
    assert "P2" in index_html and "P1" in index_html
    assert "1 (SRC-A)" in index_html
    assert "2 (SRC-A, SRC-B)" in index_html
    assert "option value='coverage'" in index_html
    assert "option value='domain-A'" in index_html
    assert "option value='domain-B'" in index_html
    assert "domain-projection-block" in index_html
    assert "function applyOverviewFilters()" in index_html
    assert "dataset.domainAStatus" in index_html
    assert "dataset.domainBStatus" in index_html
    assert "function applyOverviewViewMode()" in index_html
    assert "Event Overlay Summary" in trends_html
    assert "trend-event-overlay" in trends_html
    assert "data-event-ids='EVT-POL-350'" in trends_html
    assert "option value='events'" in trends_html
    assert "function applyTrendViewMode()" in trends_html
    assert "EVT-POL-350" in events_html and "EVT-UKR-350" in events_html
    assert "data-country-id='POL'" in events_html
    assert "function applyEventFilters()" in events_html
    comparison_html = (pages.output_dir / "comparison.html").read_text()
    coverage_html = (pages.output_dir / "coverage.html").read_text()
    assert "Cross-Country Comparison" in comparison_html
    assert "POL" in comparison_html and "UKR" in comparison_html
    assert "option value='low_coverage'" in comparison_html
    assert "option value='low_confidence'" in comparison_html
    assert "option value='relative_baseline'" in comparison_html
    assert "comparison-baseline-controls" in comparison_html
    assert "comparison-relative-summary" in comparison_html
    assert "Relative Baseline Summary" in comparison_html
    assert "data-coverage-band='low'" in comparison_html
    assert "data-confidence-band='low'" in comparison_html
    assert "comparison-baseline-cell" in comparison_html
    assert "function applyComparisonFilters()" in comparison_html
    assert "function renderComparisonBaseline()" in comparison_html
    assert "formatSignedDelta" in comparison_html
    assert "Country Coverage / Gap Matrix" in coverage_html
    assert "Freshness Band Summary" in coverage_html
    assert "fresh" in coverage_html
    assert "Remediation Watchlist" in coverage_html
    assert "Review country scope and source applicability configuration for the affected source." in coverage_html
    assert "coverage.html#source-SRC-B" in coverage_html
    assert "minimal" in coverage_html
    assert "missing:B" in coverage_html
    assert "no_usable_input_data" in coverage_html
    assert "records_only_for_other_countries_in_scope" in coverage_html
    assert "scope_config_problem" in coverage_html



def test_load_site_payload_from_artifacts_falls_back_for_missing_readiness_support_files(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    (artifacts_dir / "readmodels" / "country_profiles").mkdir(parents=True)
    (artifacts_dir / "readmodels" / "domain_details").mkdir(parents=True)
    (artifacts_dir / "reports").mkdir(parents=True)

    (artifacts_dir / "snapshot.json").write_text(
        json.dumps(
            {
                "snapshot_id": "SNAP-RUN-320-v1",
                "run_id": "RUN-320",
                "country_set_id": "MVP-COUNTRIES-v1",
                "active_domains": ["A", "B", "D"],
                "rule_versions": {"domain_status": "rules-2026-05"},
                "source_state": {"SRC-A": "success"},
                "analytical_outputs": {"country_status": {"UKR": "S3"}},
                "status": "success",
                "algorithm_version": "alg-0.1",
                "data_version": "data-0.1",
            }
        )
    )
    (artifacts_dir / "readmodels" / "world_map.json").write_text(
        json.dumps({"baseline_mode": "Combined 30/90/365", "active_domains": ["A", "B", "D"], "countries": [{"country_id": "UKR", "status": "S3", "active_domains": ["A", "B", "D"]}]})
    )
    (artifacts_dir / "readmodels" / "source_coverage.json").write_text(
        json.dumps({"sources": [{"source_id": "SRC-A", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.9}], "failed_sources": [], "missing_sources": []})
    )
    (artifacts_dir / "readmodels" / "system_status.json").write_text(
        json.dumps({
            "run_id": "RUN-320", "run_status": "success", "active_domains": ["A", "B", "D"], "coverage": {"countries_total": 1, "countries_with_updates": 1}, "failed_sources": [], "available_reports": ["REP-DAILY-SNAP-RUN-320-v1"], "snapshot_id": "SNAP-RUN-320-v1", "reprocessing_status": "idle", "last_run": "2026-05-11T18:00:00Z",
            "artifact_status": {
                "validation_backtest": {"status": "absent", "reason": "not_configured"},
                "traceability_lineage": {"status": "present", "reason": None},
                "repo_closure": {"status": "absent", "reason": "not_yet_implemented"},
                "annotations": {"status": "absent", "reason": "not_yet_implemented"}
            }
        })
    )
    (artifacts_dir / "readmodels" / "operational_evidence_lane.json").write_text(
        json.dumps({
            "latest_summary": {
                "run_id": "RUN-320",
                "run_status": "success",
                "pilot_set": "extended-focus-complete",
                "country_set_id": "MVP-COUNTRIES-LIVE-extended-focus-complete-v1",
                "combined_ce_ratio": 1.0,
                "governance_verdict": "green",
                "policy_gate_verdict": "pass",
                "release_verdict": "ready",
                "readiness_interpretation": "release_ready",
                "known_gap_count": 0,
                "known_gaps": [],
                "suppressed_known_gaps": [],
                "known_gap_suppression_reason": None,
                "failed_source_count": 0,
                "failed_sources": [],
                "operator_next_action": "No immediate action required; live probe governance summary is healthy.",
            },
            "recent_runs": [
                {
                    "run_id": "RUN-320",
                    "recorded_at": "2026-05-11T18:00:00Z",
                    "run_status": "success",
                    "pilot_set": "extended-focus-complete",
                    "country_set_id": "MVP-COUNTRIES-LIVE-extended-focus-complete-v1",
                    "combined_ce_ratio": 1.0,
                    "governance_verdict": "green",
                    "policy_gate_verdict": "pass",
                    "release_verdict": "ready",
                    "readiness_interpretation": "release_ready",
                    "known_gap_count": 0,
                    "failed_source_count": 0,
                    "failed_sources": [],
                }
            ],
        })
    )
    (artifacts_dir / "readmodels" / "country_profiles" / "UKR.json").write_text(
        json.dumps({"country_id": "UKR", "multi_domain_status": "S3", "domain_states": {"A": "D3"}, "trends": {"yearly": ["2026-01"]}, "drivers": ["A_news_volume"], "linked_events": [], "coverage": 0.84, "confidence": 0.73, "counter_indicators": [], "uncertainty": []})
    )
    (artifacts_dir / "readmodels" / "domain_details" / "UKR__A.json").write_text(
        json.dumps({"country_id": "UKR", "domain": "A", "anomaly_state": "D3", "time_series": [{"timestamp": "2026-05-11", "value": 0.67}], "baseline_comparison": {"delta_to_baseline": 0.36}, "feature_values": [{"feature_id": "A_article_count", "value": 12.0, "coverage": 0.9}], "source_context": [{"source_id": "SRC-A", "freshness_hours": 6, "history_horizon": "3y", "status": "success"}], "uncertainty": []})
    )
    (artifacts_dir / "readmodels" / "traceability_lineage.json").write_text(
        json.dumps({"lineage_records": [{"source_id": "SRC-A", "raw_record_id": "RAW-SRC-A-1", "normalized_id": "NORM-SRC-A-1", "feature_id": "A_article_count", "domain_status_id": "DST-UKR-A-RUN-320", "multi_domain_status_id": "MST-UKR-RUN-320", "snapshot_id": "SNAP-RUN-320-v1", "report_id": "REP-DAILY-SNAP-RUN-320-v1"}]})
    )
    (artifacts_dir / "reports" / "daily_snapshot.json").write_text(
        json.dumps({"report_id": "REP-DAILY-SNAP-RUN-320-v1", "report_type": "daily_snapshot", "format": "json", "payload": {"snapshot_id": "SNAP-RUN-320-v1", "status": "success"}})
    )

    payload = local_app.load_site_payload_from_artifacts(artifacts_dir)

    assert payload["validation_view_model"] is None
    assert payload["annotations_view_model"] == {"annotations": [], "by_scope": {}, "by_linked_item": {}}
    assert payload["repo_closure_view_model"]["summary"] == {"slice_count": 9, "requirement_count": 51, "closed": 51, "at_risk": 0}
    assert payload["system_status_read_model"]["operational_evidence_lane"]["latest_summary"]["country_set_id"] == "MVP-COUNTRIES-LIVE-extended-focus-complete-v1"

    pages = build_local_mvp_site(output_dir=tmp_path / "site", **payload)
    readiness_html = (pages.output_dir / "readiness.html").read_text()
    assert "validation_backtest_absent:not_configured" in readiness_html
    assert "Artifact Readiness" in readiness_html
    assert "validation_backtest" in readiness_html
    assert "absent (not_configured)" in readiness_html
    assert "missing_validation_artifact" not in readiness_html
    assert "missing_annotations_artifact" not in readiness_html
    assert "missing_repo_closure_artifact" not in readiness_html


def test_load_site_payload_from_artifacts_uses_persisted_readiness_view_model_when_available(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_dir = tmp_path / "artifacts-with-readiness"
    (artifacts_dir / "readmodels" / "country_profiles").mkdir(parents=True)
    (artifacts_dir / "readmodels" / "domain_details").mkdir(parents=True)
    (artifacts_dir / "reports").mkdir(parents=True)

    (artifacts_dir / "snapshot.json").write_text(
        json.dumps(
            {
                "snapshot_id": "SNAP-RUN-321-v1",
                "run_id": "RUN-321",
                "country_set_id": "MVP-COUNTRIES-v1",
                "active_domains": ["A", "B", "D"],
                "rule_versions": {"domain_status": "rules-2026-05"},
                "source_state": {"SRC-A": "success"},
                "analytical_outputs": {"country_status": {"UKR": "S3"}},
                "status": "success",
                "algorithm_version": "alg-0.1",
                "data_version": "data-0.1",
            }
        )
    )
    (artifacts_dir / "readmodels" / "world_map.json").write_text(
        json.dumps({"baseline_mode": "Combined 30/90/365", "active_domains": ["A", "B", "D"], "countries": [{"country_id": "UKR", "status": "S3", "active_domains": ["A", "B", "D"]}]})
    )
    (artifacts_dir / "readmodels" / "source_coverage.json").write_text(
        json.dumps({"sources": [{"source_id": "SRC-A", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.9}], "failed_sources": [], "missing_sources": []})
    )
    (artifacts_dir / "readmodels" / "system_status.json").write_text(
        json.dumps({
            "run_id": "RUN-321", "run_status": "success", "active_domains": ["A", "B", "D"], "coverage": {"countries_total": 1, "countries_with_updates": 1}, "failed_sources": [], "available_reports": ["REP-DAILY-SNAP-RUN-321-v1"], "snapshot_id": "SNAP-RUN-321-v1", "reprocessing_status": "idle", "last_run": "2026-05-11T18:00:00Z",
            "artifact_status": {
                "validation_backtest": {"status": "present", "reason": None},
                "traceability_lineage": {"status": "present", "reason": None},
                "repo_closure": {"status": "present", "reason": None},
                "annotations": {"status": "present", "reason": None}
            }
        })
    )
    (artifacts_dir / "readmodels" / "country_profiles" / "UKR.json").write_text(
        json.dumps({"country_id": "UKR", "multi_domain_status": "S3", "domain_states": {"A": "D3"}, "trends": {"yearly": ["2026-01"]}, "drivers": ["A_news_volume"], "linked_events": [], "coverage": 0.84, "confidence": 0.73, "counter_indicators": [], "uncertainty": []})
    )
    (artifacts_dir / "readmodels" / "domain_details" / "UKR__A.json").write_text(
        json.dumps({"country_id": "UKR", "domain": "A", "anomaly_state": "D3", "time_series": [{"timestamp": "2026-05-11", "value": 0.67}], "baseline_comparison": {"delta_to_baseline": 0.36}, "feature_values": [{"feature_id": "A_article_count", "value": 12.0, "coverage": 0.9}], "source_context": [{"source_id": "SRC-A", "freshness_hours": 6, "history_horizon": "3y", "status": "success"}], "uncertainty": []})
    )
    (artifacts_dir / "readmodels" / "traceability_lineage.json").write_text(
        json.dumps({"lineage_records": [{"source_id": "SRC-A", "raw_record_id": "RAW-SRC-A-1", "normalized_id": "NORM-SRC-A-1", "feature_id": "A_article_count", "domain_status_id": "DST-UKR-A-RUN-321", "multi_domain_status_id": "MST-UKR-RUN-321", "snapshot_id": "SNAP-RUN-321-v1", "report_id": "REP-DAILY-SNAP-RUN-321-v1"}]})
    )
    (artifacts_dir / "readmodels" / "repo_closure.json").write_text(
        json.dumps({"summary": {"slice_count": 9, "requirement_count": 45, "closed": 45, "at_risk": 0}, "slices": []})
    )
    (artifacts_dir / "readmodels" / "annotations.json").write_text(
        json.dumps({"annotations": [], "by_scope": {}, "by_linked_item": {}})
    )
    (artifacts_dir / "readmodels" / "validation_backtest.json").write_text(
        json.dumps({"case_id": "VAL-UKR-2022-001", "country_id": "UKR"})
    )
    (artifacts_dir / "readmodels" / "readiness.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-321",
                "snapshot_id": "SNAP-RUN-321-v1",
                "demo_verdict": "ready",
                "release_verdict": "ready",
                "demo_checks": [{"label": "Persisted Demo Check", "ready": True}],
                "evidence_checks": [{"label": "Persisted Evidence Check", "ready": True}],
                "artifact_checks": [{"artifact": "validation_backtest", "status": "present", "reason": None}],
                "known_gaps": [],
                "report_count": 1,
                "country_profile_count": 1,
                "domain_detail_count": 1,
            }
        )
    )
    (artifacts_dir / "readmodels" / "release_gate.json").write_text(
        json.dumps(
            {
                "gate_verdict": "go",
                "blocker_count": 0,
                "blockers": [],
            }
        )
    )
    (artifacts_dir / "readmodels" / "release_failure_drill_report.json").write_text(
        json.dumps(build_release_failure_drill_report(repo_root=repo_root), indent=2, sort_keys=True)
    )
    (artifacts_dir / "readmodels" / "stakeholder_functional_closure.json").write_text(
        json.dumps(
            {
                "focus_gap_cluster": {
                    "stakeholder_ids": [
                        "StR-001", "StR-002", "StR-004", "StR-007", "StR-024", "StR-025",
                        "StR-135", "StR-136", "StR-137", "StR-138", "StR-139", "StR-140", "StR-141", "StR-142",
                        "StR-226", "StR-227", "StR-228", "StR-229", "StR-230",
                    ],
                    "covered_count": 19,
                    "implemented_count": 19,
                    "not_implemented_count": 0,
                    "not_implemented_ids": [],
                }
            }
        )
    )
    (artifacts_dir / "readmodels" / "stakeholder_e2e_flow_coverage.json").write_text(
        json.dumps(
            {
                "summary": {
                    "flow_count": 6,
                    "covered_flow_count": 6,
                    "flow_gap_count": 0,
                    "missing_evidence_ref_count": 0,
                    "missing_requirement_ref_count": 0,
                },
                "stop_criteria": {
                    "all_flows_covered": True,
                    "all_flow_evidence_refs_resolve": True,
                    "all_flow_requirement_refs_resolve": True,
                    "required_roles_covered": True,
                },
            }
        )
    )
    (artifacts_dir / "readmodels" / "stakeholder_e2e_ui_smoke.json").write_text(
        json.dumps(
            {
                "flow_count": 6,
                "covered_flow_count": 6,
                "flow_gap_count": 0,
                "stop_criteria": {
                    "all_flows_present_in_rendered_ui": True,
                    "all_role_boundaries_hold": True,
                },
            }
        )
    )
    (artifacts_dir / "readmodels" / "release_readiness_index.json").write_text(
        json.dumps(
            {
                "passed_gates": 8,
                "total_gates": 8,
                "percent": 100.0,
                "gates": [
                    {"gate_id": "stakeholder_e2e_flows_covered", "passed": True, "detail": "ok"},
                    {"gate_id": "stakeholder_e2e_ui_smoke_covered", "passed": True, "detail": "ok"},
                ],
            }
        )
    )
    (artifacts_dir / "readmodels" / "release_evidence_assessment.json").write_text(
        json.dumps(
            {
                "operator_release_summary": {
                    "release_gate_verdict": "go",
                    "failed_gate_count": 0,
                    "failed_gates": [],
                    "operator_next_action": "No action required; release gates are green.",
                },
                "operator_blocker_causality": {
                    "primary_root_cause_gate_id": None,
                    "root_cause_gate_ids": [],
                    "derived_gate_ids": [],
                    "operator_next_action": "No blocker-chain action required; release gates are green.",
                    "causal_chain_rows": [],
                },
                "operator_operability_cluster": {
                    "cluster_status": "healthy",
                    "covered_gate_count": 5,
                    "failed_gate_count": 0,
                    "failed_gate_ids": [],
                    "operator_next_action": "No operability-cluster action required; stakeholder flows and browser gates are green.",
                    "cluster_rows": [
                        {"gate_id": "stakeholder_e2e_flows_covered", "gate_group": "flow_definition", "passed": True, "cluster_role": "upstream_flow_spec"},
                        {"gate_id": "stakeholder_e2e_ui_smoke_covered", "gate_group": "flow_rendering", "passed": True, "cluster_role": "rendered_flow_presence"},
                        {"gate_id": "stakeholder_browser_e2e_acceptance_covered", "gate_group": "browser_acceptance", "passed": True, "cluster_role": "bundle_navigation_acceptance"},
                    ],
                },
            }
        )
    )
    (artifacts_dir / "readmodels" / "release_failure_drill_report.json").write_text(
        json.dumps(
            {
                "operator_failure_drill_digest": {
                    "cluster_count": 1,
                    "top_cluster_gate_id": "release_gate_go",
                    "operator_next_action": "Resolve known gaps in readiness inputs.",
                    "clusters": [
                        {
                            "gate_id": "release_gate_go",
                            "scenario_count": 2,
                            "scenario_ids": ["known_gap_injected", "traceability_closure_at_risk_injected"],
                            "remediation_hint": "Resolve known gaps in readiness inputs.",
                        }
                    ],
                },
                "operator_failure_drill_trend_baseline": {
                    "snapshot_count": 1,
                    "top_recurring_gate_id": "release_gate_go",
                    "operator_focus": "Establish follow-up snapshots and monitor drift for release_gate_go.",
                    "trend_rows": [
                        {
                            "gate_id": "release_gate_go",
                            "scenario_count": 2,
                            "trend_status": "baseline_established",
                            "trajectory": "steady",
                            "recurrence_ratio": 1.0,
                        }
                    ],
                },
                "operator_recurrence_aware_remediation_prioritization": {
                    "model": "recurrence_x_urgency",
                    "priority_count": 1,
                    "top_priority_gate_id": "release_gate_go",
                    "operator_next_action": "Resolve known gaps in readiness inputs.",
                    "priorities": [
                        {
                            "rank": 1,
                            "gate_id": "release_gate_go",
                            "priority_score": 3.0,
                            "urgency_boost": 0,
                            "recommended_action": "Resolve known gaps in readiness inputs.",
                        }
                    ],
                },
                "operator_failure_drill_delta_ledger": {
                    "comparison_mode": "no_prior_snapshot",
                    "snapshot_count": 1,
                    "movement_summary": {
                        "steady": 1,
                        "regressed": 0,
                        "improved": 0,
                        "new_issue": 0,
                        "resolved": 0,
                    },
                    "top_regression_gate_id": None,
                    "operator_impact_narrative": "No prior AP-23 snapshot available; current release drill establishes the first delta baseline.",
                    "delta_rows": [
                        {
                            "gate_id": "release_gate_go",
                            "movement_status": "steady",
                            "current_scenario_count": 2,
                            "previous_scenario_count": 2,
                            "scenario_delta": 0,
                        }
                    ],
                },
                "operator_remediation_execution_loop": {
                    "model": "priority_to_action_trace_closure",
                    "action_count": 1,
                    "open_action_count": 1,
                    "next_action_id": "AP24-ACT-01-RELEASE-GATE-GO",
                    "operator_next_action": "Resolve known gaps in readiness inputs.",
                    "actions": [
                        {
                            "action_id": "AP24-ACT-01-RELEASE-GATE-GO",
                            "priority_rank": 1,
                            "gate_id": "release_gate_go",
                            "current_movement_status": "steady",
                            "execution_status": "next_up",
                            "closure_target": "Clear the gate from the next AP-23 delta snapshot or reduce scenario count.",
                            "closure_evidence_sources": ["operator_failure_drill_delta_ledger", "gate_diagnostics_export"],
                        }
                    ],
                },
                "operator_stale_remediation_closure_drill": {
                    "stale_remediation_gap_injected": {
                        "requires_closure": True,
                        "closure_guarded": False,
                        "actionability_sla_hours": 72.0,
                        "breach_count": 2,
                        "breaches": [
                            {"reason": "non_actionable_priority", "item": {"priority_score": 0, "unresolved_age_hours": 24.0}},
                            {"reason": "sla_breach", "item": {"priority_score": 10, "unresolved_age_hours": 120.0}},
                        ],
                    }
                },
                "operator_stale_remediation_action_plan": {
                    "action_count": 2,
                    "next_action_id": "AP25-STALE-01",
                    "operator_next_action": "Raise stale-remediation priority above zero so the item becomes actionable.",
                    "status_counts": {"next_up": 1, "queued": 1},
                    "actions": [
                        {
                            "action_id": "AP25-STALE-01",
                            "breach_reason": "non_actionable_priority",
                            "action_category": "make_actionable",
                            "execution_status": "next_up",
                            "closure_check": "priority_score > 0",
                        },
                        {
                            "action_id": "AP25-STALE-02",
                            "breach_reason": "sla_breach",
                            "action_category": "close_overdue_action",
                            "execution_status": "queued",
                            "closure_check": "unresolved_age_hours <= 72.0",
                        }
                    ],
                }
            }
        )
    )
    (artifacts_dir / "reports" / "daily_snapshot.json").write_text(
        json.dumps({"report_id": "REP-DAILY-SNAP-RUN-321-v1", "report_type": "daily_snapshot", "format": "json", "payload": {"snapshot_id": "SNAP-RUN-321-v1", "status": "success"}})
    )

    payload = local_app.load_site_payload_from_artifacts(artifacts_dir)

    assert payload["readiness_view_model"]["demo_checks"] == [{"label": "Persisted Demo Check", "ready": True}]
    assert payload["release_gate_view_model"]["gate_verdict"] == "go"
    assert payload["release_failure_drill_report_view_model"]["operator_failure_drill_digest"]["cluster_count"] == 1
    assert payload["stakeholder_functional_closure_view_model"]["focus_gap_cluster"]["covered_count"] == 19
    assert payload["stakeholder_e2e_flow_coverage_view_model"]["summary"]["flow_count"] == 6
    assert payload["stakeholder_e2e_ui_smoke_view_model"]["flow_count"] == 6
    assert payload["release_readiness_index_view_model"]["passed_gates"] == 8
    assert payload["operator_release_summary_view_model"]["failed_gate_count"] == 0
    assert payload["operator_blocker_causality_view_model"]["primary_root_cause_gate_id"] is None
    assert payload["operator_operability_cluster_view_model"]["cluster_status"] == "healthy"
    assert payload["operator_failure_drill_digest_view_model"]["cluster_count"] == 1
    assert payload["operator_failure_drill_trend_baseline_view_model"]["snapshot_count"] == 1
    assert payload["operator_recurrence_aware_remediation_prioritization_view_model"]["priority_count"] == 1
    assert payload["operator_failure_drill_delta_ledger_view_model"]["snapshot_count"] == 1
    assert payload["operator_remediation_execution_loop_view_model"]["action_count"] == 1
    assert payload["operator_stale_remediation_closure_drill_view_model"]["stale_remediation_gap_injected"]["breach_count"] == 2
    assert payload["operator_stale_remediation_action_plan_view_model"]["action_count"] == 2

    pages = build_local_mvp_site(output_dir=tmp_path / "site-with-readiness", **payload)
    readiness_html = (pages.output_dir / "readiness.html").read_text()
    failure_drill_html = (pages.output_dir / "release_failure_drill.html").read_text()
    readiness_json = json.loads((pages.output_dir / "readiness.json").read_text())

    assert "Prioritized items:" in readiness_html
    assert "Primary focus:" in readiness_html
    assert "traceability risk:" in readiness_html
    assert "operability cluster:" in readiness_html
    assert "Persisted Demo Check" in readiness_html
    assert "Persisted Evidence Check" in readiness_html
    assert "Gate Verdict" in readiness_html
    assert "Release Readiness Index" in readiness_html
    assert "stakeholder_e2e_flows_covered" in readiness_html
    assert "Stakeholder E2E Flow Coverage (AP-04/AP-05)" in readiness_html
    assert "Stakeholder E2E UI Smoke Coverage (AP-07/AP-08)" in readiness_html
    assert "Covered Flows: <strong>6/6</strong>" in readiness_html
    assert "Stakeholder Focus Closure" in readiness_html
    assert "Covered IDs: 19 / 19 | Open IDs: 0" in readiness_html
    assert "Analyst Briefing — What matters now?" in readiness_html
    assert "Prioritized items: <strong>1</strong>" in readiness_html
    assert "Primary focus: <strong>Stale remediation action plan: AP25-STALE-01</strong>" in readiness_html
    assert "stale remediation actions: 1" in readiness_html
    assert "Analyst Hotspot Matrix — cross-signal convergence" in readiness_html
    assert "Multi-signal countries: <strong>0</strong> / 0" in readiness_html
    assert "Hotspot Links" in readiness_html
    assert "Coverage</a>" in readiness_html or "Validation</a>" in readiness_html
    assert "Operator Release Steering (AP-16/AP-17/AP-19/AP-20/AP-22/AP-23/AP-24)" in readiness_html
    assert "AP-16 failed gates: <strong>0</strong>" in readiness_html
    assert "AP-26 primary root cause: <strong>none</strong>" in readiness_html
    assert "AP-26 root causes: none | derived effects: none" in readiness_html
    assert "No blocker-chain action required" in readiness_html
    assert "AP-27 cluster status: <strong>healthy</strong>" in readiness_html
    assert "AP-27 covered gates: <strong>5</strong> | failed gates: 0" in readiness_html
    assert "No operability-cluster action required" in readiness_html
    assert "Release / Failure Drill" in failure_drill_html
    assert "Scenario Matrix" in failure_drill_html
    assert "Evidence Pack Markdown" in failure_drill_html
    assert "baseline" in failure_drill_html
    assert "upstream_flow_spec" in readiness_html
    assert "bundle_navigation_acceptance" in readiness_html
    assert "AP-17 cluster count: <strong>1</strong>" in readiness_html
    assert "AP-19 trend snapshots: <strong>1</strong>" in readiness_html
    assert "AP-22 priority rows: <strong>1</strong>" in readiness_html
    assert "AP-23 delta snapshot count: <strong>1</strong>" in readiness_html
    assert "AP-24 open actions: <strong>1</strong>" in readiness_html
    assert "AP-25 stale actions: <strong>2</strong>" in readiness_html
    assert "AP25-STALE-01" in readiness_html
    assert "make_actionable" in readiness_html
    assert "priority_score &gt; 0" in readiness_html
    assert "AP24-ACT-01-RELEASE-GATE-GO" in readiness_html
    assert "next_up" in readiness_html
    assert "No prior AP-23 snapshot available" in readiness_html
    assert "steady" in readiness_html
    assert "AP-22 Rank" in readiness_html
    assert "baseline_established" in readiness_html
    assert "AP-20 requires closure: <strong>yes</strong> | closure guarded: <strong>no</strong>" in readiness_html
    assert "non_actionable_priority" in readiness_html
    assert "sla_breach" in readiness_html
    assert "release_gate_go" in readiness_html
    assert "go" in readiness_html
    assert readiness_json["demo_checks"] == [{"label": "Persisted Demo Check", "ready": True}]


def test_readiness_view_renders_failure_drill_scenarios_with_expected_no_go_signals(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    drill_report = build_release_failure_drill_report(repo_root=repo_root)
    base_payload = local_app._demo_payload()

    for scenario_id, assessment in drill_report["scenarios"].items():
        scenario_dir = tmp_path / "drill-gui" / scenario_id
        pages = build_local_mvp_site(
            output_dir=scenario_dir,
            world_map_read_model=base_payload["world_map_read_model"],
            country_profile_read_models=base_payload["country_profile_read_models"],
            domain_detail_read_models=base_payload["domain_detail_read_models"],
            source_coverage_read_model=base_payload["source_coverage_read_model"],
            report_catalog=base_payload["report_catalog"],
            system_status_read_model=base_payload["system_status_read_model"],
            validation_view_model=base_payload["validation_view_model"],
            annotations_view_model=base_payload["annotations_view_model"],
            readiness_view_model=assessment["readiness"],
            release_gate_view_model=assessment["release_gate"],
            stakeholder_functional_closure_view_model=assessment["stakeholder_functional_closure"],
            stakeholder_e2e_flow_coverage_view_model=assessment["stakeholder_e2e_flow_coverage"],
            release_readiness_index_view_model=assessment["release_readiness_index"],
        )
        readiness_html = (pages.output_dir / "readiness.html").read_text(encoding="utf-8")

        if scenario_id == "baseline":
            assert "go" in readiness_html
            assert "Covered IDs: 19 / 19 | Open IDs: 0" in readiness_html
        if scenario_id == "known_gap_injected":
            assert "no_go" in readiness_html
            assert "known_gaps_clear" in readiness_html
        if scenario_id == "traceability_closure_at_risk_injected":
            assert "no_go" in readiness_html
            assert "traceability_integrity_clean" in readiness_html
        if scenario_id == "stakeholder_focus_cluster_open_injected":
            assert "Covered IDs: 18 / 19 | Open IDs: 1" in readiness_html
            assert "StR-DRILL-001" in readiness_html
        if scenario_id == "stakeholder_e2e_flow_gap_injected":
            assert "Covered Flows: <strong>5/6</strong>" in readiness_html
            assert "stakeholder_e2e_flows_covered" in readiness_html


def test_local_gui_module_runs_without_runtime_warning_and_can_use_artifact_bundle(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    artifacts_dir = tmp_path / "artifacts"
    (artifacts_dir / "readmodels" / "country_profiles").mkdir(parents=True)
    (artifacts_dir / "readmodels" / "domain_details").mkdir(parents=True)
    (artifacts_dir / "reports").mkdir(parents=True)
    (artifacts_dir / "snapshot.json").write_text(
        json.dumps(
            {
                "snapshot_id": "SNAP-RUN-301-v1",
                "run_id": "RUN-301",
                "country_set_id": "MVP-COUNTRIES-v1",
                "active_domains": ["A", "B", "D"],
                "rule_versions": {"domain_status": "rules-2026-05"},
                "source_state": {"SRC-A": "success"},
                "analytical_outputs": {"country_status": {"UKR": "S3"}},
                "status": "success",
                "algorithm_version": "alg-0.1",
                "data_version": "data-0.1",
            }
        )
    )
    (artifacts_dir / "readmodels" / "world_map.json").write_text(
        json.dumps(
            {
                "baseline_mode": "Combined 30/90/365",
                "active_domains": ["A", "B", "D"],
                "countries": [{"country_id": "UKR", "status": "S3", "active_domains": ["A", "B", "D"]}],
            }
        )
    )
    (artifacts_dir / "readmodels" / "country_profiles" / "UKR.json").write_text(
        json.dumps(
            {
                "country_id": "UKR",
                "multi_domain_status": "S3",
                "domain_states": {"A": "D3", "B": "D2", "D": "D1"},
                "trends": {"yearly": ["2026-01"]},
                "drivers": ["A_news_volume"],
                "linked_events": ["EVT-302"],
                "coverage": 0.84,
                "confidence": 0.73,
                "counter_indicators": [],
                "uncertainty": [],
                "annotations": [],
            }
        )
    )
    (artifacts_dir / "readmodels" / "domain_details" / "UKR__A.json").write_text(
        json.dumps(
            {
                "country_id": "UKR",
                "domain": "A",
                "anomaly_state": "D3",
                "time_series": [{"timestamp": "2026-05-11", "value": 0.67}],
                "baseline_comparison": {"delta_to_baseline": 0.36},
                "feature_values": [{"feature_id": "A_article_count", "value": 12.0, "coverage": 0.9}],
                "source_context": [{"source_id": "SRC-A", "freshness_hours": 6, "history_horizon": "3y", "status": "success"}],
                "uncertainty": [],
            }
        )
    )
    (artifacts_dir / "readmodels" / "source_coverage.json").write_text(
        json.dumps({"sources": [{"source_id": "SRC-A", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.9}], "failed_sources": [], "missing_sources": []})
    )
    (artifacts_dir / "readmodels" / "system_status.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-301",
                "run_status": "success",
                "active_domains": ["A", "B", "D"],
                "coverage": {"countries_total": 30, "countries_with_updates": 30},
                "failed_sources": [],
                "available_reports": ["REP-DAILY-SNAP-RUN-301-v1"],
                "snapshot_id": "SNAP-RUN-301-v1",
                "reprocessing_status": "idle",
                "last_run": "2026-05-11T18:00:00Z",
            }
        )
    )
    (artifacts_dir / "readmodels" / "validation_backtest.json").write_text(
        json.dumps(
            {
                "case_id": "VAL-UKR-2022-001",
                "country_id": "UKR",
                "case_name": "Escalation reference case",
                "time_range": {"start": "2022-02-01", "end": "2022-03-01"},
                "expected_domains": ["A", "B", "D"],
                "observed_domains": ["A", "B"],
                "domain_match_ratio": 2 / 3,
                "status_match": True,
                "expected_pattern": "Aligned information, event, and economic stress escalation.",
                "validation_goal": "Check multi-domain alignment detection.",
                "reference_sources": ["SRC-A", "SRC-B"],
                "validation_metrics": ["Domain Match", "Status Match"],
                "known_limitations": ["historical coverage incomplete"],
                "reprocessing_comparison": {"prior_snapshot_id": "SNAP-RUN-001-v1", "new_snapshot_id": "SNAP-RUN-001-v2", "changed_versions": ["rule_version"]},
            }
        )
    )
    (artifacts_dir / "readmodels" / "traceability_lineage.json").write_text(
        json.dumps(
            {
                "lineage_records": [
                    {
                        "source_id": "SRC-A",
                        "raw_record_id": "RAW-SRC-A-1",
                        "normalized_id": "NORM-SRC-A-1",
                        "feature_id": "A_article_count",
                        "domain_status_id": "DST-UKR-A-RUN-301",
                        "multi_domain_status_id": "MST-UKR-RUN-301",
                        "snapshot_id": "SNAP-RUN-301-v1",
                        "report_id": "REP-DAILY-SNAP-RUN-301-v1",
                    }
                ]
            }
        )
    )
    (artifacts_dir / "readmodels" / "annotations.json").write_text(
        json.dumps(
            {
                "annotations": [
                    {
                        "annotation_id": "ANN-401",
                        "created_at": "2026-05-11T18:05:00Z",
                        "author": "analyst",
                        "scope": "country",
                        "annotation_type": "context_note",
                        "severity_assessment": "relevant",
                        "confidence_assessment": "medium",
                        "text": "CLI verification annotation.",
                        "tags": ["cli"],
                        "linked_items": ["UKR"],
                        "review_status": "draft",
                    }
                ],
                "by_scope": {"country": ["ANN-401"]},
                "by_linked_item": {"UKR": ["ANN-401"]},
            }
        )
    )
    (artifacts_dir / "reports" / "daily_snapshot.json").write_text(
        json.dumps(
            {
                "report_id": "REP-DAILY-SNAP-RUN-301-v1",
                "report_type": "daily_snapshot",
                "format": "json",
                "payload": {"snapshot_id": "SNAP-RUN-301-v1", "status": "success"},
            }
        )
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.gui.local_app",
            "--output-dir",
            str(tmp_path / "site"),
            "--artifacts-dir",
            str(artifacts_dir),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "RuntimeWarning" not in result.stderr
    assert (tmp_path / "site" / "index.html").exists()
    assert "SNAP-RUN-301-v1" in (tmp_path / "site" / "runs.html").read_text()
    assert "EVT-302" in (tmp_path / "site" / "events.html").read_text()
    assert "VAL-UKR-2022-001" in (tmp_path / "site" / "validation.html").read_text()
    assert "RAW-SRC-A-1" in (tmp_path / "site" / "traceability.html").read_text()
    assert "CLI verification annotation." in (tmp_path / "site" / "annotations.html").read_text()
    assert "Demo / Release Readiness" in (tmp_path / "site" / "readiness.html").read_text()


def test_build_local_mvp_site_viewer_role_hides_annotation_and_ops_pages(tmp_path: Path) -> None:
    payload = local_app._demo_payload()
    pages = build_local_mvp_site(output_dir=tmp_path / "viewer-site", ui_role="viewer", **payload)

    assert not (pages.output_dir / "annotations.html").exists()
    assert not (pages.output_dir / "reports.html").exists()
    assert not (pages.output_dir / "runs.html").exists()

    index_html = (pages.output_dir / "index.html").read_text()
    assert "📝 Annotations" not in index_html
    assert "📄 Reports" not in index_html
    assert "⚙ System" not in index_html

    country_html = (pages.output_dir / "countries" / "UKR.html").read_text()
    assert "Open Annotation Workflow for this Country" not in country_html

    validation_html = (pages.output_dir / "validation.html").read_text()
    assert "Create Annotation Draft" not in validation_html
    assert "annotations.html?scope=country&annotation_type=review_note" not in validation_html


def test_build_local_mvp_site_rejects_unknown_role(tmp_path: Path) -> None:
    payload = local_app._demo_payload()
    try:
        build_local_mvp_site(output_dir=tmp_path / "invalid-role-site", ui_role="operator", **payload)
    except ValueError as exc:
        assert "Unsupported ui_role" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported ui_role")


def test_build_local_mvp_site_renders_analytics_page_when_view_model_provided(tmp_path: Path) -> None:
    """analytics.html is generated and contains expected section IDs when analytics_view_model is passed.
    Requirement trace: AP-INT-04, AP-F22..F27.
    """
    payload = local_app._demo_payload()
    analytics_vm = {
        'cross_domain_fusion': {
            'UKR': {
                'fused_score': 0.72, 'confidence': 0.85, 'contradiction_detected': True,
                'contradictions': [{'domain_a': 'A', 'domain_b': 'D', 'severity_gap': 3, 'description': 'gap'}],
                'weights': [], 'contributing_domains': ['A', 'D'], 'fusion_method': 'weighted',
            }
        },
        'bayesian_estimates': {
            'UKR': {'A': {'map_status': 'D3', 'confidence': 0.68, 'confidence_interval': ['D2', 'D4'], 'posterior': {}}}
        },
        'uncertainty_budgets': {
            'UKR': {'total_uncertainty': 0.19, 'dominant_stage': 'domain_scoring', 'propagation_factor': 2.1, 'levels': []}
        },
        'rule_evaluations': [
            {'rule_id': 'RULE-D4', 'rule_name': 'D4', 'matched': True, 'country_id': 'UKR',
             'domain': 'A', 'severity': 'critical', 'annotation_text': 'Critical state', 'tags': []}
        ],
        'dependency_graph': {'source_count': 2, 'edge_count': 1, 'clusters': [], 'influence_scores': []},
        'provenance_chain': {'root_sources': ['SRC-A', 'SRC-B'], 'leaf_outputs': ['MST-UKR'], 'depth': 3, 'nodes': [], 'edges': []},
        'info_epidemiology': {
            'spread_paths': [
                {'signal_key': 'signal-alpha', 'source_sequence': ['SRC-A', 'SRC-B', 'SRC-C'], 'total_spread_hours': 12},
            ],
            'amplification_events': [
                {'signal_key': 'signal-beta', 'source_id': 'SRC-D', 'amplification_factor': 2.5, 'lag_hours': 6},
            ],
        },
    }
    result = build_local_mvp_site(
        output_dir=tmp_path / 'analytics-site',
        analytics_view_model=analytics_vm,
        **payload,
    )
    # analytics.html must exist
    analytics_html = result.output_dir / 'analytics.html'
    assert analytics_html.exists(), 'analytics.html not generated'
    content = analytics_html.read_text(encoding='utf-8')
    # Core page title and nav
    assert 'Advanced Analytics' in content
    assert '🔬 Analytics' in content
    # Section headings
    assert 'Cross-Domain Fusion' in content
    assert 'Bayesian' in content
    assert 'Uncertainty' in content
    assert 'Rule Evaluations' in content
    assert 'Dependency Graph' in content
    assert 'Provenance Chain' in content
    assert 'Source Lineage Visualization' in content
    assert 'Source Hotspot Matrix' in content
    assert "id='analytics-source-hotspot-matrix'" in content
    assert 'Dependency cluster' in content or 'Spread path' in content
    assert 'signal-alpha' in content
    assert 'signal-beta' in content
    assert 'Epidemiology' in content
    # Cross-link/filter controls
    assert "id='analytics-controls'" in content
    assert "id='analytics-section-filter'" in content
    assert "id='analytics-text-filter'" in content
    assert "id='analytics-filter-reset'" in content
    assert 'applyAnalyticsSectionFilter' in content
    assert "href='#analytics-cross-domain-fusion'" in content
    assert "href='#analytics-provenance-chain'" in content
    assert "href='#analytics-source-lineage-visualization'" in content
    # Role constraints per analytics section
    assert "id='analytics-rule-evaluations'" in content
    assert "id='analytics-dependency-graph'" in content
    assert "id='analytics-provenance-chain'" in content
    assert "id='analytics-source-lineage-visualization'" in content
    assert "data-role-min='analyst'" in content
    assert "data-role-min='admin'" in content
    # Country data
    assert 'UKR' in content
    # nav link in index
    index_content = (result.output_dir / 'index.html').read_text(encoding='utf-8')
    assert '🔬 Analytics' in index_content
    assert 'analytics.html' in index_content
