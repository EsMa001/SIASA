"""SIASA automated backtesting pipeline.

Runs historical data through the current scoring logic and compares
results against previously recorded scores to detect regressions.

Key APIs:
- ``run_backtest(db_path, domains, countries)`` — execute backtest
- ``compare_backtest_results(current, historical)`` — diff detection
- ``generate_backtest_report(comparison)`` — markdown report

Requirement trace: AP-F10, StR-358..381 (Validation & Backtesting)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from siasa.scoring.scoring_thresholds import regression_thresholds
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from siasa.data.storage import (
    CountryDomainScoreEntry,
    load_country_domain_time_series,
    load_latest_country_scores,
)


@dataclass(frozen=True)
class BacktestScoreSnapshot:
    """A single score point for comparison."""
    country_id: str
    domain: str
    run_id: str
    status: str
    score: float
    data_sufficiency: str


@dataclass(frozen=True)
class BacktestComparison:
    """Comparison between two score snapshots."""
    country_id: str
    domain: str
    baseline_status: str
    baseline_score: float
    current_status: str
    current_score: float
    score_delta: float
    status_changed: bool
    regression_detected: bool


@dataclass(frozen=True)
class BacktestResult:
    """Full backtest result with comparisons and summary."""
    timestamp: str
    baseline_run_id: str
    current_run_id: str
    comparisons: list[BacktestComparison]
    total_comparisons: int
    regressions: int
    improvements: int
    unchanged: int
    status_changes: int
    regression_rate: float
    verdict: str  # "pass", "warning", "fail"


# Thresholds for regression detection, governed via scoring_thresholds.yaml (AP-24);
# resolved PER CALL (SwR-109) so overrides and sensitivity sweeps reach this module.


def run_backtest(
    db_path: str | Path,
    countries: list[str] | None = None,
    domains: list[str] | None = None,
    baseline_offset: int = 1,
) -> BacktestResult:
    """Run a backtest comparing current scores against a baseline.

    Args:
        db_path: Path to the run-history SQLite database.
        countries: ISO-3 country codes to include (None = all available).
        domains: Domain letters to include (None = all available).
        baseline_offset: How many runs back to use as baseline (1 = previous run).

    Returns:
        BacktestResult with comparisons and summary verdict.
    """
    db = Path(db_path) if not isinstance(db_path, Path) else db_path
    now = datetime.now(timezone.utc)

    # Discover available countries/domains from the database
    available = _discover_available_scores(str(db))
    if not available:
        return _empty_result(now, "no_data")

    target_countries = countries or sorted(available.keys())
    target_domains = domains or sorted({d for ds in available.values() for d in ds})

    comparisons: list[BacktestComparison] = []

    for country_id in target_countries:
        if country_id not in available:
            continue
        for domain in target_domains:
            if domain not in available.get(country_id, set()):
                continue

            time_series = load_country_domain_time_series(db, country_id=country_id, domain=domain, limit=baseline_offset + 1)
            if len(time_series) < 2:
                continue  # Need at least baseline + current

            current = time_series[0]  # Most recent
            baseline = time_series[min(baseline_offset, len(time_series) - 1)]

            comparison = _compare_scores(
                country_id=country_id,
                domain=domain,
                baseline=baseline,
                current=current,
            )
            comparisons.append(comparison)

    if not comparisons:
        return _empty_result(now, "insufficient_history")

    # Compute summary
    score_regression_threshold, regression_rate_warning, regression_rate_fail = (
        regression_thresholds()
    )
    regressions = sum(1 for c in comparisons if c.regression_detected)
    improvements = sum(1 for c in comparisons if c.score_delta > score_regression_threshold)
    unchanged = sum(1 for c in comparisons if abs(c.score_delta) <= score_regression_threshold and not c.status_changed)
    status_changes = sum(1 for c in comparisons if c.status_changed)
    regression_rate = regressions / len(comparisons) if comparisons else 0.0

    if regression_rate >= regression_rate_fail:
        verdict = "fail"
    elif regression_rate >= regression_rate_warning or regressions > 0:
        verdict = "warning"
    else:
        verdict = "pass"

    # Determine run IDs
    baseline_run_id = comparisons[0].domain if not comparisons else "unknown"
    current_run_id = "latest"
    if comparisons:
        # Use the first comparison's data to determine run context
        first_ts = load_country_domain_time_series(
            db, country_id=comparisons[0].country_id, domain=comparisons[0].domain, limit=2
        )
        if len(first_ts) >= 2:
            current_run_id = first_ts[0].run_id
            baseline_run_id = first_ts[1].run_id

    return BacktestResult(
        timestamp=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        baseline_run_id=baseline_run_id,
        current_run_id=current_run_id,
        comparisons=comparisons,
        total_comparisons=len(comparisons),
        regressions=regressions,
        improvements=improvements,
        unchanged=unchanged,
        status_changes=status_changes,
        regression_rate=round(regression_rate, 3),
        verdict=verdict,
    )


def generate_backtest_report(result: BacktestResult) -> str:
    """Generate a markdown-formatted backtest report."""
    lines: list[str] = []
    lines.append("# SIASA Backtest Report")
    lines.append("")
    lines.append(f"**Timestamp:** {result.timestamp}")
    lines.append(f"**Baseline run:** {result.baseline_run_id}")
    lines.append(f"**Current run:** {result.current_run_id}")
    lines.append(f"**Verdict:** {result.verdict.upper()}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"| --- | --- |")
    lines.append(f"| Total comparisons | {result.total_comparisons} |")
    lines.append(f"| Regressions | {result.regressions} |")
    lines.append(f"| Improvements | {result.improvements} |")
    lines.append(f"| Unchanged | {result.unchanged} |")
    lines.append(f"| Status changes | {result.status_changes} |")
    lines.append(f"| Regression rate | {result.regression_rate:.1%} |")
    lines.append("")

    if result.regressions > 0:
        lines.append("## Regressions")
        lines.append("")
        lines.append("| Country | Domain | Baseline | Current | Delta |")
        lines.append("| --- | --- | --- | --- | --- |")
        for c in result.comparisons:
            if c.regression_detected:
                lines.append(
                    f"| {c.country_id} | {c.domain} | "
                    f"{c.baseline_status} ({c.baseline_score:.2f}) | "
                    f"{c.current_status} ({c.current_score:.2f}) | "
                    f"{c.score_delta:+.2f} |"
                )
        lines.append("")

    if result.status_changes > 0:
        lines.append("## Status Changes")
        lines.append("")
        lines.append("| Country | Domain | From | To | Delta |")
        lines.append("| --- | --- | --- | --- | --- |")
        for c in result.comparisons:
            if c.status_changed:
                lines.append(
                    f"| {c.country_id} | {c.domain} | "
                    f"{c.baseline_status} | {c.current_status} | "
                    f"{c.score_delta:+.2f} |"
                )
        lines.append("")

    return "\n".join(lines)


def _compare_scores(
    country_id: str,
    domain: str,
    baseline: CountryDomainScoreEntry,
    current: CountryDomainScoreEntry,
) -> BacktestComparison:
    score_delta = current.score - baseline.score
    status_changed = current.status != baseline.status
    # Regression = significant score drop
    score_regression_threshold, _, _ = regression_thresholds()
    regression_detected = score_delta < -score_regression_threshold

    return BacktestComparison(
        country_id=country_id,
        domain=domain,
        baseline_status=baseline.status,
        baseline_score=baseline.score,
        current_status=current.status,
        current_score=current.score,
        score_delta=round(score_delta, 4),
        status_changed=status_changed,
        regression_detected=regression_detected,
    )


def _discover_available_scores(db_path: str) -> dict[str, set[str]]:
    """Discover which country/domain combinations have score history."""
    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT DISTINCT country_id, domain FROM country_domain_scores"
        )
        result: dict[str, set[str]] = {}
        for country_id, domain in cursor.fetchall():
            result.setdefault(country_id, set()).add(domain)
        conn.close()
        return result
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return {}


def _empty_result(now: datetime, verdict: str) -> BacktestResult:
    return BacktestResult(
        timestamp=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        baseline_run_id="none",
        current_run_id="none",
        comparisons=[],
        total_comparisons=0,
        regressions=0,
        improvements=0,
        unchanged=0,
        status_changes=0,
        regression_rate=0.0,
        verdict=verdict,
    )
