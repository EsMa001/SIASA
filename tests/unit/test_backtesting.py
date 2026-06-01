"""Tests for the automated backtesting pipeline."""

from __future__ import annotations

import sqlite3
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from siasa.data.storage import (
    initialize_run_history_schema,
    persist_country_domain_scores,
    persist_operational_latest_run,
)
from siasa.validation.backtesting import (
    BacktestResult,
    run_backtest,
    generate_backtest_report,
    _compare_scores,
    _SCORE_REGRESSION_THRESHOLD,
)


def _setup_db_with_scores(
    scores: list[tuple[str, str, str, str, float, str]],
) -> Path:
    """Create a temp DB with country_domain_scores.

    Each tuple: (run_id, country_id, domain, status, score, data_sufficiency)
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    db_path = Path(tmp.name)
    tmp.close()

    initialize_run_history_schema(db_path)

    # Collect unique run_ids and persist run entries first
    # Then manually patch recorded_at to ensure deterministic time ordering
    run_ids = sorted({s[0] for s in scores})
    for idx, run_id in enumerate(run_ids):
        persist_operational_latest_run(
            db_path,
            run_id=run_id,
            run_status="success",
            pilot_set="backtest",
            artifacts_dir=Path("/tmp/artifacts"),
            gui_index=Path("/tmp/gui/index.html"),
            failed_sources=[],
        )

    # Patch recorded_at to ensure distinct and ordered timestamps
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    for idx, run_id in enumerate(run_ids):
        # Earlier runs get earlier timestamps
        fake_ts = f"2025-01-01T00:{idx:02d}:00+00:00"
        conn.execute("UPDATE runs SET recorded_at = ? WHERE run_id = ?", (fake_ts, run_id))
    conn.commit()
    conn.close()

    # Group scores by run_id and persist as batch per run
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run_id, country_id, domain, status, score, sufficiency in scores:
        grouped[run_id].append({
            "country_id": country_id,
            "domain": domain,
            "status": status,
            "score": score,
            "data_sufficiency": sufficiency,
        })

    for run_id in sorted(grouped):
        persist_country_domain_scores(
            db_path,
            run_id=run_id,
            scores=grouped[run_id],
        )

    return db_path


class TestRunBacktest:
    """Tests for the main backtest execution."""

    def test_basic_backtest_pass(self):
        """No regression when scores are stable."""
        db_path = _setup_db_with_scores([
            ("run-001", "UKR", "A", "D1", 0.15, "sufficient"),
            ("run-002", "UKR", "A", "D1", 0.16, "sufficient"),
        ])

        result = run_backtest(db_path)

        assert result.verdict == "pass"
        assert result.total_comparisons == 1
        assert result.regressions == 0
        assert result.regression_rate == 0.0

    def test_regression_detected(self):
        """Score drop beyond threshold triggers regression."""
        db_path = _setup_db_with_scores([
            ("run-001", "UKR", "A", "D2", 0.50, "sufficient"),
            ("run-002", "UKR", "A", "D1", 0.10, "sufficient"),
        ])

        result = run_backtest(db_path)

        assert result.verdict == "fail"  # 100% regression rate
        assert result.regressions == 1
        assert result.comparisons[0].regression_detected
        assert result.comparisons[0].score_delta < 0

    def test_status_change_tracked(self):
        """Status changes (D1 -> D3) are tracked."""
        db_path = _setup_db_with_scores([
            ("run-001", "UKR", "B", "D1", 0.15, "sufficient"),
            ("run-002", "UKR", "B", "D3", 0.55, "sufficient"),
        ])

        result = run_backtest(db_path)

        assert result.status_changes == 1
        assert result.comparisons[0].status_changed

    def test_multi_country_multi_domain(self):
        """Backtest across multiple countries and domains."""
        db_path = _setup_db_with_scores([
            ("run-001", "UKR", "A", "D1", 0.15, "sufficient"),
            ("run-001", "UKR", "B", "D2", 0.35, "sufficient"),
            ("run-001", "POL", "A", "D1", 0.10, "sufficient"),
            ("run-002", "UKR", "A", "D1", 0.14, "sufficient"),
            ("run-002", "UKR", "B", "D2", 0.30, "sufficient"),
            ("run-002", "POL", "A", "D1", 0.12, "sufficient"),
        ])

        result = run_backtest(db_path)

        assert result.total_comparisons == 3
        assert result.verdict == "pass"

    def test_country_filter(self):
        """Backtest can be filtered to specific countries."""
        db_path = _setup_db_with_scores([
            ("run-001", "UKR", "A", "D1", 0.15, "sufficient"),
            ("run-001", "POL", "A", "D1", 0.10, "sufficient"),
            ("run-002", "UKR", "A", "D1", 0.16, "sufficient"),
            ("run-002", "POL", "A", "D1", 0.11, "sufficient"),
        ])

        result = run_backtest(db_path, countries=["UKR"])

        assert result.total_comparisons == 1
        assert result.comparisons[0].country_id == "UKR"

    def test_domain_filter(self):
        """Backtest can be filtered to specific domains."""
        db_path = _setup_db_with_scores([
            ("run-001", "UKR", "A", "D1", 0.15, "sufficient"),
            ("run-001", "UKR", "B", "D2", 0.35, "sufficient"),
            ("run-002", "UKR", "A", "D1", 0.16, "sufficient"),
            ("run-002", "UKR", "B", "D2", 0.33, "sufficient"),
        ])

        result = run_backtest(db_path, domains=["B"])

        assert result.total_comparisons == 1
        assert result.comparisons[0].domain == "B"

    def test_insufficient_history(self):
        """Only one run => no comparison possible."""
        db_path = _setup_db_with_scores([
            ("run-001", "UKR", "A", "D1", 0.15, "sufficient"),
        ])

        result = run_backtest(db_path)

        assert result.verdict == "insufficient_history"
        assert result.total_comparisons == 0

    def test_empty_database(self):
        """Empty database returns no_data verdict."""
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        db_path = Path(tmp.name)
        tmp.close()
        initialize_run_history_schema(db_path)

        result = run_backtest(db_path)

        assert result.verdict == "no_data"
        assert result.total_comparisons == 0

    def test_high_regression_rate_fails(self):
        """Many regressions trigger fail verdict."""
        db_path = _setup_db_with_scores([
            ("run-001", "UKR", "A", "D3", 0.60, "sufficient"),
            ("run-001", "UKR", "B", "D3", 0.55, "sufficient"),
            ("run-001", "POL", "A", "D2", 0.40, "sufficient"),
            # All drop significantly
            ("run-002", "UKR", "A", "D1", 0.10, "sufficient"),
            ("run-002", "UKR", "B", "D1", 0.10, "sufficient"),
            ("run-002", "POL", "A", "D1", 0.05, "sufficient"),
        ])

        result = run_backtest(db_path)

        assert result.verdict == "fail"
        assert result.regression_rate > 0.3


class TestGenerateBacktestReport:
    """Tests for markdown report generation."""

    def test_report_contains_summary(self):
        db_path = _setup_db_with_scores([
            ("run-001", "UKR", "A", "D1", 0.15, "sufficient"),
            ("run-002", "UKR", "A", "D1", 0.16, "sufficient"),
        ])
        result = run_backtest(db_path)
        report = generate_backtest_report(result)

        assert "# SIASA Backtest Report" in report
        assert "PASS" in report
        assert "Total comparisons" in report

    def test_report_lists_regressions(self):
        db_path = _setup_db_with_scores([
            ("run-001", "UKR", "A", "D3", 0.60, "sufficient"),
            ("run-002", "UKR", "A", "D1", 0.10, "sufficient"),
        ])
        result = run_backtest(db_path)
        report = generate_backtest_report(result)

        assert "## Regressions" in report
        assert "UKR" in report
        assert "FAIL" in report


class TestCompareScores:
    """Tests for individual score comparison logic."""

    def test_no_regression_when_score_stable(self):
        from siasa.data.storage import CountryDomainScoreEntry

        baseline = CountryDomainScoreEntry("run-001", "UKR", "A", "D1", 0.15, "sufficient")
        current = CountryDomainScoreEntry("run-002", "UKR", "A", "D1", 0.16, "sufficient")

        result = _compare_scores("UKR", "A", baseline, current)

        assert not result.regression_detected
        assert not result.status_changed
        assert result.score_delta == pytest.approx(0.01, abs=0.001)

    def test_regression_on_large_score_drop(self):
        from siasa.data.storage import CountryDomainScoreEntry

        baseline = CountryDomainScoreEntry("run-001", "UKR", "A", "D3", 0.60, "sufficient")
        current = CountryDomainScoreEntry("run-002", "UKR", "A", "D1", 0.10, "sufficient")

        result = _compare_scores("UKR", "A", baseline, current)

        assert result.regression_detected
        assert result.status_changed
        assert result.score_delta < -_SCORE_REGRESSION_THRESHOLD
