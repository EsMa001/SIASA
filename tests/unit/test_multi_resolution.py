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
