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
            {"source_id": "SRC-A", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.9},
            {"source_id": "ACLED", "status": "prepared_adapter", "history_horizon": "n/a", "freshness_hours": None, "confidence": None},
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
            }
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
    assert (pages.output_dir / "validation.html").exists()
    assert (pages.output_dir / "traceability.html").exists()
    assert (pages.output_dir / "annotations.html").exists()
    assert (pages.output_dir / "readiness.html").exists()

    index_html = (pages.output_dir / "index.html").read_text()
    assert "World Anomaly Map" in index_html
    assert "Global Overview" in index_html
    assert "UKR" in index_html
    assert "countries/UKR.html" in index_html
    assert "Daily Global Review" in index_html
    assert "Top Status Changes" in index_html
    assert "S2 → S3" in index_html
    assert "Data Gaps / Trust Limits" in index_html
    assert "failed_source:SRC-B" in index_html
    assert "country_without_update:POL" in index_html
    assert "Support Status" in index_html
    assert "supported" in index_html

    country_html = (pages.output_dir / "countries" / "UKR.html").read_text()
    assert "Country Profile" in country_html
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

    domain_html = (pages.output_dir / "domains" / "UKR-A.html").read_text()
    assert "Domain Detail" in domain_html
    assert "delta_to_baseline" in domain_html
    assert "Time Series Chart" in domain_html
    assert "2026-05-09" in domain_html
    assert "<svg" in domain_html
    assert "SRC-A" in domain_html
    assert "Domain A spike is traceable to two closely coupled source clusters." in domain_html

    coverage_html = (pages.output_dir / "coverage.html").read_text()
    assert "Source / Coverage View" in coverage_html
    assert "Trust Summary" in coverage_html
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
    assert "2026-01" in trends_html
    assert "<svg" in trends_html

    events_html = (pages.output_dir / "events.html").read_text()
    assert "Current Events Page" in events_html
    assert "EVT-001" in events_html

    validation_html = (pages.output_dir / "validation.html").read_text()
    assert "Validation / Backtest View" in validation_html
    assert "VAL-UKR-2022-001" in validation_html
    assert "Domain Match" in validation_html
    assert "Review Summary" in validation_html
    assert "match_with_gaps" in validation_html
    assert "Missing Expected Domains" in validation_html
    assert "D" in validation_html
    assert "Changed Versions" in validation_html

    readiness_html = (pages.output_dir / "readiness.html").read_text()
    assert "Demo / Release Readiness" in readiness_html
    assert "Demo Verdict" in readiness_html
    assert "Release Verdict" in readiness_html
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

    annotations_html = (pages.output_dir / "annotations.html").read_text()
    assert "Analyst Annotations View" in annotations_html
    assert "Snapshot review pending source outage assessment." in annotations_html
    assert "UKR:A" in annotations_html


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
            if Path(href).suffix and not (html_file.parent / href).resolve().exists():
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
    for country_id, event_id, trend in (("POL", "EVT-POL-350", ["2026-02"]), ("UKR", "EVT-UKR-350", ["2026-01"])):
        (artifacts_dir / "readmodels" / "country_profiles" / f"{country_id}.json").write_text(
            json.dumps(
                {
                    "country_id": country_id,
                    "multi_domain_status": "S3",
                    "domain_states": {"A": "D3", "B": "D2"},
                    "trends": {"yearly": trend},
                    "drivers": ["A_news_volume"],
                    "linked_events": [event_id],
                    "coverage": 0.8,
                    "confidence": 0.7,
                    "counter_indicators": [],
                    "uncertainty": [],
                    "annotations": [],
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
                    {"source_id": "SRC-A", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.9},
                    {"source_id": "SRC-B", "status": "success", "history_horizon": "3y", "freshness_hours": 12, "confidence": 0.8},
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
    assert "countries/POL.html" in index_html
    assert "countries/UKR.html" in index_html
    assert "POL" in trends_html and "UKR" in trends_html
    assert "EVT-POL-350" in events_html and "EVT-UKR-350" in events_html



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
        json.dumps({"run_id": "RUN-320", "run_status": "success", "active_domains": ["A", "B", "D"], "coverage": {"countries_total": 1, "countries_with_updates": 1}, "failed_sources": [], "available_reports": ["REP-DAILY-SNAP-RUN-320-v1"], "snapshot_id": "SNAP-RUN-320-v1", "reprocessing_status": "idle", "last_run": "2026-05-11T18:00:00Z"})
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
    assert "missing_validation_artifact" in readiness_html
    assert "missing_annotations_artifact" not in readiness_html
    assert "missing_repo_closure_artifact" not in readiness_html


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
