import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from siasa.gui import local_app
from siasa.gui.local_app import build_local_mvp_site


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

    assert "Remediation Watchlist" in html
    assert "No remediation priorities recorded." in html



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
    }

    repo_closure_view = {
        "summary": {"slice_count": 4, "requirement_count": 18, "closed": 18, "at_risk": 0},
        "slices": [
            {"slice_id": "governance-and-run-controls", "summary": {"closed": 6, "at_risk": 0}},
            {"slice_id": "reporting-and-export", "summary": {"closed": 4, "at_risk": 0}},
        ],
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
    )

    assert (pages.output_dir / "index.html").exists()
    assert (pages.output_dir / "countries" / "UKR.html").exists()
    assert (pages.output_dir / "domains" / "UKR-A.html").exists()
    assert (pages.output_dir / "coverage.html").exists()
    assert (pages.output_dir / "reports.html").exists()
    assert (pages.output_dir / "runs.html").exists()
    assert (pages.output_dir / "trends.html").exists()
    assert (pages.output_dir / "events.html").exists()
    assert (pages.output_dir / "comparison.html").exists()
    assert (pages.output_dir / "validation.html").exists()
    assert (pages.output_dir / "traceability.html").exists()
    assert (pages.output_dir / "annotations.html").exists()
    assert (pages.output_dir / "readiness.html").exists()

    index_html = (pages.output_dir / "index.html").read_text()
    assert "World Anomaly Map" in index_html
    assert "Map Visualization" in index_html
    assert "Coverage / Confidence Visualization" in index_html
    assert "coverage-visualization-block" in index_html
    assert "Europe / Black Sea" in index_html
    assert "Baseline / View Controls" in index_html
    assert "Domain Filter" in index_html
    assert "Time Window" in index_html
    assert "Baseline Mode" in index_html
    assert "<svg" in index_html
    assert "Global Overview" in index_html
    assert "UKR" in index_html
    assert "countries/UKR.html" in index_html
    assert "Daily Global Review" in index_html
    assert "Priority Class" in index_html
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
    assert "Support Status" in index_html
    assert "supported" in index_html

    country_html = (pages.output_dir / "countries" / "UKR.html").read_text()
    assert "Country Profile" in country_html
    assert "Trust / Uncertainty Summary" in country_html
    assert "Coverage Meter" in country_html
    assert "Confidence Meter" in country_html
    assert "Priority: <strong>P1</strong>" in country_html
    assert "Selection Type: <strong>Core Focus</strong>" in country_html
    assert "Source Depth" in country_html
    assert "SRC-A" in country_html and "SRC-B" in country_html
    assert "Domain Gap Summary" in country_html
    assert "Gap Cause Details" in country_html
    assert "../coverage.html#source-SRC-D" in country_html
    assert "uncertainty-badge" in country_html
    assert "Why this country is in this state" in country_html
    assert "Escalation is primarily driven by Domain A with partial corroboration from Domain B." in country_html
    assert "Explanation Overview" in country_html
    assert "A_news_volume" in country_html
    assert "Domain Deep Dives" in country_html
    assert "../domains/UKR-A.html" in country_html
    assert "B — not available" in country_html
    assert "ANN-001" in country_html
    assert "Analyst Annotations in Context" in country_html
    assert "Replicated agency report likely inflated country-level signal volume." in country_html
    assert "../annotations.html?scope=country&amp;linked_item=UKR&amp;annotation_type=context_note" in country_html
    assert "Open Annotation Workflow for this Country" in country_html

    domain_html = (pages.output_dir / "domains" / "UKR-A.html").read_text()
    assert "Domain Detail" in domain_html
    assert "delta_to_baseline" in domain_html
    assert "Time Series Chart" in domain_html
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
    assert "prepared_adapter" in coverage_html
    assert "Degraded Sources" in coverage_html

    reports_html = (pages.output_dir / "reports.html").read_text()
    assert "Report / Export View" in reports_html
    assert "REP-COVERAGE-001" in reports_html
    assert "Evidence Summary" in reports_html
    assert "partial_success" in reports_html
    assert "SRC-B" in reports_html
    assert "SNAP-RUN-200-v1" in reports_html

    runs_html = (pages.output_dir / "runs.html").read_text()
    assert "System Status / Runs" in runs_html
    assert "partial_success" in runs_html
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

    events_html = (pages.output_dir / "events.html").read_text()
    assert "Current Events Page" in events_html
    assert "EVT-001" in events_html

    comparison_html = (pages.output_dir / "comparison.html").read_text()
    assert "Cross-Country Comparison" in comparison_html
    assert "Coverage / Confidence Comparison" in comparison_html
    assert "Comparison controls" in comparison_html
    assert "UKR" in comparison_html
    assert "S3" in comparison_html

    validation_html = (pages.output_dir / "validation.html").read_text()
    assert "Validation / Backtest View" in validation_html
    assert "VAL-UKR-2022-001" in validation_html
    assert "Domain Match" in validation_html
    assert "Review Summary" in validation_html
    assert "Reference Case Portfolio Summary" in validation_html
    assert "Validation Case Portfolio" in validation_html
    assert "Curated Reference Case Library" in validation_html
    assert "Library Cases" in validation_html
    assert "Historical Reference Review Summary" in validation_html
    assert "Historical Reference Reviews" in validation_html
    assert "Average Evidence Score" in validation_html
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
    assert "Average Replay Evidence Score" in validation_html
    assert "Replay Evidence Tiers" in validation_html
    assert "Replay Input Record Total" in validation_html
    assert "Archival Data Files" in validation_html
    assert "Replay Source Coverage" in validation_html
    assert "Replay Attention Watchlist" in validation_html
    assert "Replay Attention Summary" in validation_html
    assert "Attention Level" in validation_html
    assert "Follow-up Owner" in validation_html
    assert "validation governance" in validation_html
    assert "runtime/source coverage" in validation_html
    assert "Attention by Country" in validation_html
    assert "status_mismatch_and_domain_gap" in validation_html
    assert "domain_coverage_gap" in validation_html
    assert "Review reference-case expectation alignment and archival replay provenance before using this case as a strong validation signal." in validation_html
    assert "Review missing expected domains and source coverage before treating this replay as fully representative." in validation_html
    assert "VAL-ISR-2024-002" in validation_html
    assert "VAL-POL-2024-002" in validation_html
    assert "archival_replay_inputs/VAL-UKR-2022-001.json" in validation_html
    assert "Replay Input Records" in validation_html
    assert "military_escalation" in validation_html
    assert "VAL-POL-2023-001" in validation_html
    assert "2022-02-01 to 2024-05-31" in validation_html
    assert "VAL-POL-2022-001" in validation_html
    assert "POL, UKR" in validation_html

    traceability_html = (pages.output_dir / "traceability.html").read_text()

    assert "Changed Versions" in validation_html

    readiness_html = (pages.output_dir / "readiness.html").read_text()
    assert "Demo / Release Readiness" in readiness_html
    assert "Demo Verdict" in readiness_html
    assert "Release Verdict" in readiness_html
    assert "Artifact Readiness Summary" in readiness_html
    assert "validation_backtest" in readiness_html
    assert "present" in readiness_html
    assert "ready" in readiness_html
    assert "blocked_by_known_gaps" in readiness_html
    assert "failed_source:SRC-B" in readiness_html
    assert "country_without_update:POL" in readiness_html
    assert "Source / Coverage" in readiness_html
    assert "Validation / Backtest" in readiness_html

    traceability_html = (pages.output_dir / "traceability.html").read_text()
    assert "Traceability / Lineage View" in traceability_html
    assert "RAW-SRC-A-1" in traceability_html
    assert "REP-DAILY-RUN-200" in traceability_html
    assert "Source Dependency Groundwork" in traceability_html
    assert "Dependency Cluster Candidates" in traceability_html
    assert "A_article_count" in traceability_html
    assert "SRC-A, SRC-B" in traceability_html
    assert "Source-Origin Groundwork" in traceability_html
    assert "not yet inferable from current lineage artifact" in traceability_html

    annotations_html = (pages.output_dir / "annotations.html").read_text()
    assert "Analyst Annotations View" in annotations_html
    assert "Snapshot review pending source outage assessment." in annotations_html
    assert "UKR:A" in annotations_html
    assert "Create / Edit Annotation Workflow" in annotations_html
    assert "annotation-editor-form" in annotations_html
    assert "annotation-scope-filter" in annotations_html
    assert "annotation-review-filter" in annotations_html
    assert "annotation-linked-item-filter" in annotations_html
    assert "Save Draft Annotation" in annotations_html
    assert "Export Draft Annotations" in annotations_html
    assert "Draft History" in annotations_html
    assert "siasa_annotation_workflow_v1" in annotations_html
    assert "prefillAnnotationFromQuery" in annotations_html
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
    assert "Priority Class" in index_html
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
    assert "data-coverage-band='low'" in comparison_html
    assert "data-confidence-band='low'" in comparison_html
    assert "function applyComparisonFilters()" in comparison_html
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
    assert payload["repo_closure_view_model"]["summary"] == {"slice_count": 9, "requirement_count": 45, "closed": 45, "at_risk": 0}

    pages = build_local_mvp_site(output_dir=tmp_path / "site", **payload)
    readiness_html = (pages.output_dir / "readiness.html").read_text()
    assert "validation_backtest_absent:not_configured" in readiness_html
    assert "Artifact Readiness Summary" in readiness_html
    assert "validation_backtest" in readiness_html
    assert "absent (not_configured)" in readiness_html
    assert "missing_validation_artifact" not in readiness_html
    assert "missing_annotations_artifact" not in readiness_html
    assert "missing_repo_closure_artifact" not in readiness_html


def test_load_site_payload_from_artifacts_uses_persisted_readiness_view_model_when_available(tmp_path: Path) -> None:
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
    (artifacts_dir / "reports" / "daily_snapshot.json").write_text(
        json.dumps({"report_id": "REP-DAILY-SNAP-RUN-321-v1", "report_type": "daily_snapshot", "format": "json", "payload": {"snapshot_id": "SNAP-RUN-321-v1", "status": "success"}})
    )

    payload = local_app.load_site_payload_from_artifacts(artifacts_dir)

    assert payload["readiness_view_model"]["demo_checks"] == [{"label": "Persisted Demo Check", "ready": True}]

    pages = build_local_mvp_site(output_dir=tmp_path / "site-with-readiness", **payload)
    readiness_html = (pages.output_dir / "readiness.html").read_text()
    readiness_json = json.loads((pages.output_dir / "readiness.json").read_text())

    assert "Persisted Demo Check" in readiness_html
    assert "Persisted Evidence Check" in readiness_html
    assert readiness_json["demo_checks"] == [{"label": "Persisted Demo Check", "ready": True}]


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
