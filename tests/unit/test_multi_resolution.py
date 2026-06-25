"""Tests for AP-13.7 — Multi-Resolution Feature-Builder.

Verifies:
- SwR-063: MultiResolutionBuilder creates Fast/Slow/Structural feature layers
  - Fast Layer: daily signals direct from alignment
  - Slow Layer: rolling-window aggregates (7d, 30d, 90d mean/std/trend)
  - Structural Layer: yearly base values (forward-filled)
  - Output as pyarrow.Table with layer metadata
"""
from __future__ import annotations

from pathlib import Path

import pyarrow as pa

from siasa.features.multi_resolution import (
    MultiResolutionBuilder,
    MultiResolutionResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_aligned_table() -> pa.Table:
    """Build a synthetic daily-aligned table for 30+ days."""
    dates = []
    countries = []
    signals = []
    values = []

    # 30 days of conflict_event_count for UKR (daily — Fast layer)
    for day in range(1, 31):
        dates.append(f"2026-06-{day:02d}")
        countries.append("UKR")
        signals.append("conflict_event_count")
        values.append(float(10 + day))  # 11, 12, ..., 40

    # Yearly structural data — refugee_population (Structural layer)
    dates.append("2025-12-31")
    countries.append("UKR")
    signals.append("refugee_population")
    values.append(6300000.0)

    return pa.table({
        "date": pa.array(dates, type=pa.string()),
        "country_id": pa.array(countries, type=pa.string()),
        "signal_key": pa.array(signals, type=pa.string()),
        "value": pa.array(values, type=pa.float64()),
    })


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_multi_resolution_builder_construction() -> None:
    """MultiResolutionBuilder must be constructable."""
    builder = MultiResolutionBuilder()
    assert builder is not None


# ---------------------------------------------------------------------------
# Fast Layer
# ---------------------------------------------------------------------------

def test_fast_layer_contains_daily_signals() -> None:
    """Fast layer must contain daily-granularity signals unchanged."""
    aligned = _seed_aligned_table()
    builder = MultiResolutionBuilder()
    result = builder.build(aligned_table=aligned)
    assert isinstance(result, MultiResolutionResult)

    fast = result.fast_layer
    assert isinstance(fast, pa.Table)
    assert fast.num_rows >= 30  # 30 days of conflict data
    assert "date" in fast.column_names
    assert "value" in fast.column_names
    assert "signal_key" in fast.column_names


# ---------------------------------------------------------------------------
# Slow Layer — rolling windows
# ---------------------------------------------------------------------------

def test_slow_layer_has_rolling_window_features() -> None:
    """Slow layer must contain 7d/30d rolling mean features."""
    aligned = _seed_aligned_table()
    builder = MultiResolutionBuilder()
    result = builder.build(aligned_table=aligned)

    slow = result.slow_layer
    assert isinstance(slow, pa.Table)
    assert slow.num_rows > 0

    columns = set(slow.column_names)
    assert "date" in columns
    assert "country_id" in columns
    assert "signal_key" in columns
    # Must have at least rolling mean columns
    assert any("mean_7d" in c for c in columns), f"Missing 7d mean in {columns}"
    assert any("mean_30d" in c for c in columns), f"Missing 30d mean in {columns}"


def test_slow_layer_rolling_mean_7d_correctness() -> None:
    """7d rolling mean must be mathematically correct."""
    aligned = _seed_aligned_table()
    builder = MultiResolutionBuilder()
    result = builder.build(aligned_table=aligned)

    slow = result.slow_layer
    dates = slow.column("date").to_pylist()
    means_7d = slow.column("mean_7d").to_pylist()
    signal_keys = slow.column("signal_key").to_pylist()

    # Find 2026-06-07 for conflict_event_count
    # Values for days 1-7: 11,12,13,14,15,16,17 → mean = 14.0
    idx = None
    for i, (d, s) in enumerate(zip(dates, signal_keys)):
        if d == "2026-06-07" and s == "conflict_event_count":
            idx = i
            break

    assert idx is not None, "2026-06-07 conflict_event_count not found in slow layer"
    assert abs(means_7d[idx] - 14.0) < 0.01, f"Expected 14.0, got {means_7d[idx]}"


# ---------------------------------------------------------------------------
# Slow Layer — rolling standard deviation (AP-17, extends SwR-063)
# ---------------------------------------------------------------------------

def _slow_index(slow: pa.Table, date: str, signal: str = "conflict_event_count") -> int:
    """Find the slow-layer row index for a (date, signal_key) pair."""
    dates = slow.column("date").to_pylist()
    signals = slow.column("signal_key").to_pylist()
    for i, (d, s) in enumerate(zip(dates, signals)):
        if d == date and s == signal:
            return i
    raise AssertionError(f"{date}/{signal} not found in slow layer")


def _seed_constant_series(value: float = 5.0, days: int = 10) -> pa.Table:
    """Daily-aligned table with a constant signal value over `days` days."""
    dates, countries, signals, values = [], [], [], []
    for day in range(1, days + 1):
        dates.append(f"2026-06-{day:02d}")
        countries.append("UKR")
        signals.append("conflict_event_count")
        values.append(value)
    return pa.table({
        "date": pa.array(dates, type=pa.string()),
        "country_id": pa.array(countries, type=pa.string()),
        "signal_key": pa.array(signals, type=pa.string()),
        "value": pa.array(values, type=pa.float64()),
    })


def test_slow_layer_has_std_features() -> None:
    """Slow layer must contain 7d/30d rolling standard-deviation features."""
    result = MultiResolutionBuilder().build(aligned_table=_seed_aligned_table())
    columns = set(result.slow_layer.column_names)
    assert "std_7d" in columns, f"Missing std_7d in {columns}"
    assert "std_30d" in columns, f"Missing std_30d in {columns}"


def test_slow_layer_rolling_std_7d_correctness() -> None:
    """7d rolling population std must be mathematically correct."""
    result = MultiResolutionBuilder().build(aligned_table=_seed_aligned_table())
    slow = result.slow_layer
    std_7d = slow.column("std_7d").to_pylist()
    # Days 1-7 values 11..17: mean 14, population variance 4.0 -> std 2.0
    idx = _slow_index(slow, "2026-06-07")
    assert abs(std_7d[idx] - 2.0) < 1e-9, f"Expected 2.0, got {std_7d[idx]}"


def test_slow_layer_std_insufficient_points_is_none() -> None:
    """Rows before the window is full must have std None (insufficient data)."""
    result = MultiResolutionBuilder().build(aligned_table=_seed_aligned_table())
    slow = result.slow_layer
    std_7d = slow.column("std_7d").to_pylist()
    # 2026-06-03 is day 3 (< 7) -> not enough points for a 7d std
    assert std_7d[_slow_index(slow, "2026-06-03")] is None


def test_slow_layer_rolling_std_30d_correctness() -> None:
    """30d rolling population std must be correct on the full 30-day window."""
    result = MultiResolutionBuilder().build(aligned_table=_seed_aligned_table())
    slow = result.slow_layer
    std_30d = slow.column("std_30d").to_pylist()
    zscore_30d = slow.column("zscore_30d").to_pylist()
    # Days 1..30 values 11..40: mean 25.5, population variance (30^2-1)/12 = 74.9167,
    # std = 8.65544; day-30 value 40 -> z = (40-25.5)/8.65544 = 1.675 > 0
    idx = _slow_index(slow, "2026-06-30")
    assert abs(std_30d[idx] - 8.65544) < 1e-3, f"Expected ~8.65544, got {std_30d[idx]}"
    assert zscore_30d[idx] is not None and zscore_30d[idx] > 0.0


def test_slow_layer_std_30d_insufficient_is_none() -> None:
    """Before the 30d window is full, std_30d/zscore_30d must be None."""
    result = MultiResolutionBuilder().build(aligned_table=_seed_aligned_table())
    slow = result.slow_layer
    std_30d = slow.column("std_30d").to_pylist()
    zscore_30d = slow.column("zscore_30d").to_pylist()
    # 2026-06-29 is day 29 (< 30) -> insufficient for a 30d window
    idx = _slow_index(slow, "2026-06-29")
    assert std_30d[idx] is None
    assert zscore_30d[idx] is None


# ---------------------------------------------------------------------------
# z-score normalization (AP-17, ALGO-ZSCORE-01)
# ---------------------------------------------------------------------------

def test_slow_layer_has_zscore_features() -> None:
    """Slow layer must contain 7d/30d z-score columns."""
    result = MultiResolutionBuilder().build(aligned_table=_seed_aligned_table())
    columns = set(result.slow_layer.column_names)
    assert "zscore_7d" in columns, f"Missing zscore_7d in {columns}"
    assert "zscore_30d" in columns, f"Missing zscore_30d in {columns}"


def test_zscore_constant_series_is_zero() -> None:
    """A constant series has zero deviation -> z-score 0.0 (not None, not large)."""
    result = MultiResolutionBuilder().build(aligned_table=_seed_constant_series())
    slow = result.slow_layer
    zscore_7d = slow.column("zscore_7d").to_pylist()
    # day 7 (7d window full) on a constant series
    assert zscore_7d[_slow_index(slow, "2026-06-07")] == 0.0


def test_zscore_outlier_is_positive() -> None:
    """An upward deviation produces a positive z-score."""
    result = MultiResolutionBuilder().build(aligned_table=_seed_aligned_table())
    slow = result.slow_layer
    zscore_7d = slow.column("zscore_7d").to_pylist()
    # day 7 value 17, mean 14, std 2 -> z = 1.5 > 0
    z = zscore_7d[_slow_index(slow, "2026-06-07")]
    assert z is not None and z > 0.0, f"Expected positive z-score, got {z}"


def test_compute_zscore_helper() -> None:
    """compute_zscore: None inputs -> None; zero std (constant) -> 0.0; else computed."""
    from siasa.features.multi_resolution import compute_zscore
    assert compute_zscore(17.0, None, None) is None
    assert compute_zscore(17.0, 14.0, None) is None
    assert compute_zscore(5.0, 5.0, 0.0) == 0.0
    assert abs(compute_zscore(17.0, 14.0, 2.0) - 1.5) < 1e-9


# ---------------------------------------------------------------------------
# Structural Layer
# ---------------------------------------------------------------------------

def test_structural_layer_contains_yearly_data() -> None:
    """Structural layer must contain forward-filled yearly base values."""
    aligned = _seed_aligned_table()
    builder = MultiResolutionBuilder()
    result = builder.build(aligned_table=aligned)

    structural = result.structural_layer
    assert isinstance(structural, pa.Table)
    assert structural.num_rows >= 1

    signal_keys = structural.column("signal_key").to_pylist()
    assert "refugee_population" in signal_keys


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

def test_result_has_all_three_layers() -> None:
    """MultiResolutionResult must expose fast, slow, structural layers."""
    aligned = _seed_aligned_table()
    builder = MultiResolutionBuilder()
    result = builder.build(aligned_table=aligned)

    assert hasattr(result, "fast_layer")
    assert hasattr(result, "slow_layer")
    assert hasattr(result, "structural_layer")
    assert isinstance(result.fast_layer, pa.Table)
    assert isinstance(result.slow_layer, pa.Table)
    assert isinstance(result.structural_layer, pa.Table)


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_build_empty_aligned_table() -> None:
    """Building from empty aligned table must return empty layers, not crash."""
    empty = pa.table({
        "date": pa.array([], type=pa.string()),
        "country_id": pa.array([], type=pa.string()),
        "signal_key": pa.array([], type=pa.string()),
        "value": pa.array([], type=pa.float64()),
    })
    builder = MultiResolutionBuilder()
    result = builder.build(aligned_table=empty)
    assert result.fast_layer.num_rows == 0
    assert result.slow_layer.num_rows == 0
    assert result.structural_layer.num_rows == 0
