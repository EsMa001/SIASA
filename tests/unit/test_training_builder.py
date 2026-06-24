"""Tests for AP-13.9 — Training-Set Builder.

Verifies:
- SwR-065: TrainingSetBuilder creates versioned ML-ready datasets
  - Temporal train/val/test split (no random, no leakage)
  - Signal-key pivoting (rows → columns)
  - Z-score normalization with saved parameters
  - Metadata with provenance
"""
from __future__ import annotations

import json
import math

import pyarrow as pa

from siasa.features.training_builder import (
    TrainingSetBuilder,
    TrainingSetResult,
    NormalizationParams,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_pit_feature_table() -> pa.Table:
    """Build a PIT-joined feature table spanning 30 days, 2 signals."""
    dates = []
    countries = []
    signals = []
    values = []

    for day in range(1, 31):
        d = f"2026-06-{day:02d}"
        # conflict_event_count
        dates.append(d)
        countries.append("UKR")
        signals.append("conflict_event_count")
        values.append(float(10 + day))
        # gdp_growth
        dates.append(d)
        countries.append("UKR")
        signals.append("gdp_growth")
        values.append(1.0 + day * 0.01)

    return pa.table({
        "date": pa.array(dates, type=pa.string()),
        "country_id": pa.array(countries, type=pa.string()),
        "signal_key": pa.array(signals, type=pa.string()),
        "value": pa.array(values, type=pa.float64()),
    })


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_training_set_builder_construction() -> None:
    """TrainingSetBuilder must accept version and split ratios."""
    builder = TrainingSetBuilder(
        version="v1",
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15,
    )
    assert builder.version == "v1"


# ---------------------------------------------------------------------------
# Temporal split
# ---------------------------------------------------------------------------

def test_temporal_split_no_leakage() -> None:
    """Train dates must all be before val dates, which must be before test dates."""
    table = _build_pit_feature_table()
    builder = TrainingSetBuilder(version="v1")
    result = builder.build(feature_table=table)

    assert isinstance(result, TrainingSetResult)

    train_dates = set(result.train_table.column("date").to_pylist())
    val_dates = set(result.val_table.column("date").to_pylist())
    test_dates = set(result.test_table.column("date").to_pylist())

    # No overlap
    assert len(train_dates & val_dates) == 0, "Train/val dates overlap!"
    assert len(val_dates & test_dates) == 0, "Val/test dates overlap!"
    assert len(train_dates & test_dates) == 0, "Train/test dates overlap!"

    # Temporal ordering: max(train) < min(val) < min(test)
    if train_dates and val_dates:
        assert max(train_dates) < min(val_dates), "Train dates leak into val!"
    if val_dates and test_dates:
        assert max(val_dates) < min(test_dates), "Val dates leak into test!"


def test_split_ratios_approximate() -> None:
    """Split sizes must approximately match requested ratios."""
    table = _build_pit_feature_table()
    builder = TrainingSetBuilder(version="v1", train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
    result = builder.build(feature_table=table)

    # 30 unique dates × 2 signals = 60 rows
    total = result.train_table.num_rows + result.val_table.num_rows + result.test_table.num_rows
    assert total == 60

    # Approximate ratios (temporal split can't be exact)
    train_frac = result.train_table.num_rows / total
    assert 0.5 <= train_frac <= 0.85, f"Train fraction {train_frac} out of range"


# ---------------------------------------------------------------------------
# Pivoting
# ---------------------------------------------------------------------------

def test_pivoted_table_has_signal_columns() -> None:
    """Pivoted table must have signal keys as columns instead of rows."""
    table = _build_pit_feature_table()
    builder = TrainingSetBuilder(version="v1")
    result = builder.build(feature_table=table)

    pivoted = result.pivoted_train_table
    assert isinstance(pivoted, pa.Table)
    columns = set(pivoted.column_names)
    assert "conflict_event_count" in columns
    assert "gdp_growth" in columns
    assert "date" in columns
    assert "country_id" in columns


def test_pivoted_table_row_count() -> None:
    """Pivoted table must have one row per (date, country) instead of per signal."""
    table = _build_pit_feature_table()
    builder = TrainingSetBuilder(version="v1")
    result = builder.build(feature_table=table)

    # Train split: ~21 dates (70% of 30) × 1 country = ~21 rows
    pivoted = result.pivoted_train_table
    assert pivoted.num_rows < result.train_table.num_rows  # Pivoting reduces rows


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def test_normalization_params_computed() -> None:
    """Builder must compute and store normalization parameters (mean, std)."""
    table = _build_pit_feature_table()
    builder = TrainingSetBuilder(version="v1")
    result = builder.build(feature_table=table)

    params = result.normalization_params
    assert isinstance(params, NormalizationParams)
    assert "conflict_event_count" in params.mean
    assert "conflict_event_count" in params.std
    assert "gdp_growth" in params.mean
    assert params.std["conflict_event_count"] > 0


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def test_metadata_contains_provenance() -> None:
    """Result metadata must contain version, date range, signal keys, split sizes."""
    table = _build_pit_feature_table()
    builder = TrainingSetBuilder(version="v1")
    result = builder.build(feature_table=table)

    meta = result.metadata
    assert meta["version"] == "v1"
    assert "date_range" in meta
    assert "signal_keys" in meta
    assert "train_rows" in meta
    assert "val_rows" in meta
    assert "test_rows" in meta
    assert set(meta["signal_keys"]) == {"conflict_event_count", "gdp_growth"}


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_build_empty_feature_table() -> None:
    """Building from empty table must not crash."""
    empty = pa.table({
        "date": pa.array([], type=pa.string()),
        "country_id": pa.array([], type=pa.string()),
        "signal_key": pa.array([], type=pa.string()),
        "value": pa.array([], type=pa.float64()),
    })
    builder = TrainingSetBuilder(version="v1")
    result = builder.build(feature_table=empty)
    assert result.train_table.num_rows == 0
    assert result.val_table.num_rows == 0
    assert result.test_table.num_rows == 0
