"""Tests for PIT-Replay monotonicity validation (AP-30.3, SwR-101).

Validates that point-in-time replay produces no look-ahead: the count of
non-NaN features must be monotonically non-decreasing as query_date advances.
"""
from __future__ import annotations

import math
from datetime import date

import pyarrow as pa
import pytest

from siasa.features.pit_join import PointInTimeJoiner, PITResult
from siasa.validation.pit_monotonicity import (
    validate_pit_monotonicity,
    PITMonotonicityResult,
)


def _build_aligned_table(rows: list[tuple[str, str, str, float]]) -> pa.Table:
    """Build an aligned table from (date, country_id, signal_key, value) tuples."""
    return pa.table({
        "date": pa.array([r[0] for r in rows], type=pa.string()),
        "country_id": pa.array([r[1] for r in rows], type=pa.string()),
        "signal_key": pa.array([r[2] for r in rows], type=pa.string()),
        "value": pa.array([r[3] for r in rows], type=pa.float64()),
    })


def test_pit_monotonicity_passes_for_growing_data():
    """Non-NaN count grows as query_date advances over accumulating data."""
    aligned = _build_aligned_table([
        ("2022-01-01", "UKR", "gdelt_tone", -1.0),
        ("2022-01-05", "UKR", "gdelt_tone", -2.0),
        ("2022-01-10", "UKR", "gdelt_tone", -3.0),
        ("2022-01-01", "UKR", "wb_gdp", 2.5),
        # wb_gdp only has data on day 1 — stale after staleness window
    ])
    joiner = PointInTimeJoiner(staleness_limit_days=30)
    query_dates = ["2022-01-01", "2022-01-05", "2022-01-10"]

    result = validate_pit_monotonicity(
        joiner=joiner,
        aligned_table=aligned,
        query_dates=query_dates,
        country_ids=["UKR"],
        signal_keys=["gdelt_tone", "wb_gdp"],
    )
    assert isinstance(result, PITMonotonicityResult)
    assert result.is_monotonic is True
    assert result.violations == []
    # Non-NaN counts should be non-decreasing
    assert all(
        result.non_nan_counts[i] <= result.non_nan_counts[i + 1]
        for i in range(len(result.non_nan_counts) - 1)
    )


def test_pit_monotonicity_detects_empty_data():
    """With no data, all counts are 0 — monotonic but trivially."""
    aligned = _build_aligned_table([])
    joiner = PointInTimeJoiner(staleness_limit_days=30)
    query_dates = ["2022-01-01", "2022-01-05"]

    result = validate_pit_monotonicity(
        joiner=joiner,
        aligned_table=aligned,
        query_dates=query_dates,
        country_ids=["UKR"],
        signal_keys=["gdelt_tone"],
    )
    assert result.is_monotonic is True
    assert result.non_nan_counts == [0, 0]


def test_pit_monotonicity_counts_increase_with_new_signals():
    """Adding a new signal mid-window increases non-NaN count."""
    aligned = _build_aligned_table([
        ("2022-01-01", "UKR", "gdelt_tone", -1.0),
        ("2022-01-05", "UKR", "wb_gdp", 3.0),  # new signal appears on day 5
    ])
    joiner = PointInTimeJoiner(staleness_limit_days=30)
    query_dates = ["2022-01-01", "2022-01-05", "2022-01-10"]

    result = validate_pit_monotonicity(
        joiner=joiner,
        aligned_table=aligned,
        query_dates=query_dates,
        country_ids=["UKR"],
        signal_keys=["gdelt_tone", "wb_gdp"],
    )
    assert result.is_monotonic is True
    # Day 1: 1 signal, Day 5: 2 signals, Day 10: 2 signals
    assert result.non_nan_counts[0] == 1
    assert result.non_nan_counts[1] == 2
    assert result.non_nan_counts[2] == 2


def test_pit_monotonicity_staleness_can_reduce_count():
    """Staleness expiry reduces non-NaN count — this is expected physics, not look-ahead.

    If a signal goes stale, the count drops. The validator flags this as a
    non-monotonic point but with staleness_induced=True (not a look-ahead violation).
    """
    aligned = _build_aligned_table([
        ("2022-01-01", "UKR", "gdelt_tone", -1.0),
        # No more data for 60 days
    ])
    joiner = PointInTimeJoiner(staleness_limit_days=15)
    query_dates = ["2022-01-01", "2022-01-10", "2022-01-20"]

    result = validate_pit_monotonicity(
        joiner=joiner,
        aligned_table=aligned,
        query_dates=query_dates,
        country_ids=["UKR"],
        signal_keys=["gdelt_tone"],
    )
    # Day 1: 1, Day 10: 1 (within staleness), Day 20: 0 (stale)
    assert result.non_nan_counts[0] == 1
    assert result.non_nan_counts[1] == 1
    assert result.non_nan_counts[2] == 0
    # Staleness-induced drops are flagged separately
    assert result.is_monotonic is False
    assert len(result.violations) == 1
    assert result.violations[0]["staleness_induced"] is True


def test_pit_monotonicity_multi_country():
    """Monotonicity check works across multiple countries."""
    aligned = _build_aligned_table([
        ("2022-01-01", "UKR", "gdelt_tone", -1.0),
        ("2022-01-01", "CHE", "gdelt_tone", 0.5),
        ("2022-01-05", "UKR", "wb_gdp", 2.0),
        ("2022-01-05", "CHE", "wb_gdp", 4.0),
    ])
    joiner = PointInTimeJoiner(staleness_limit_days=30)
    query_dates = ["2022-01-01", "2022-01-05"]

    result = validate_pit_monotonicity(
        joiner=joiner,
        aligned_table=aligned,
        query_dates=query_dates,
        country_ids=["UKR", "CHE"],
        signal_keys=["gdelt_tone", "wb_gdp"],
    )
    assert result.is_monotonic is True
    # Day 1: 2 (one per country for gdelt_tone), Day 5: 4 (all)
    assert result.non_nan_counts[0] == 2
    assert result.non_nan_counts[1] == 4


def test_pit_result_includes_query_dates():
    """Result carries the query dates for traceability."""
    aligned = _build_aligned_table([])
    joiner = PointInTimeJoiner(staleness_limit_days=30)
    query_dates = ["2022-01-01", "2022-01-05"]

    result = validate_pit_monotonicity(
        joiner=joiner,
        aligned_table=aligned,
        query_dates=query_dates,
        country_ids=["UKR"],
        signal_keys=["gdelt_tone"],
    )
    assert result.query_dates == query_dates
