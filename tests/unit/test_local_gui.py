import os
import subprocess
import sys
from pathlib import Path

from siasa.gui.local_app import build_local_mvp_site


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
            "trends": {"yearly": ["2025-11", "2025-12", "2026-01"]},
            "drivers": ["A_news_volume"],
            "linked_events": ["EVT-001"],
            "coverage": 0.84,
            "confidence": 0.73,
            "counter_indicators": ["D_macro_stability"],
            "uncertainty": ["partial_success"],
            "annotations": ["ANN-001"],
        }
    }
    domain_details = {
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
        "daily_snapshot": {"format": "Markdown + JSON", "report_id": "REP-DAILY-RUN-200", "uncertainty": ["partial_success"]},
        "country_profile": {"format": "Markdown + JSON", "report_id": "REP-COUNTRY-UKR", "country_id": "UKR"},
        "coverage_report": {"format": "Markdown + JSON + CSV", "report_id": "REP-COVERAGE-001"},
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
    }

    pages = build_local_mvp_site(
        output_dir=Path("/tmp/siasa-gui-test"),
        world_map_read_model=world_map,
        country_profile_read_models=country_profiles,
        domain_detail_read_models=domain_details,
        source_coverage_read_model=source_coverage,
        report_catalog=reports,
        system_status_read_model=system_status,
    )

    assert (pages.output_dir / "index.html").exists()
    assert (pages.output_dir / "countries" / "UKR.html").exists()
    assert (pages.output_dir / "domains" / "UKR-A.html").exists()
    assert (pages.output_dir / "coverage.html").exists()
    assert (pages.output_dir / "reports.html").exists()
    assert (pages.output_dir / "runs.html").exists()

    index_html = (pages.output_dir / "index.html").read_text()
    assert "World Anomaly Map" in index_html
    assert "Global Overview" in index_html
    assert "UKR" in index_html
    assert "countries/UKR.html" in index_html

    country_html = (pages.output_dir / "countries" / "UKR.html").read_text()
    assert "Country Profile" in country_html
    assert "A_news_volume" in country_html
    assert "ANN-001" in country_html

    domain_html = (pages.output_dir / "domains" / "UKR-A.html").read_text()
    assert "Domain Detail" in domain_html
    assert "delta_to_baseline" in domain_html
    assert "SRC-A" in domain_html

    reports_html = (pages.output_dir / "reports.html").read_text()
    assert "Report / Export View" in reports_html
    assert "REP-COVERAGE-001" in reports_html

    runs_html = (pages.output_dir / "runs.html").read_text()
    assert "System Status / Runs" in runs_html
    assert "partial_success" in runs_html


def test_local_gui_module_runs_without_runtime_warning(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    result = subprocess.run(
        [sys.executable, "-m", "siasa.gui.local_app", "--output-dir", str(tmp_path / "site")],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "RuntimeWarning" not in result.stderr
    assert (tmp_path / "site" / "index.html").exists()
