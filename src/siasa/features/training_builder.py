"""SIASA Training-Set Builder (AP-13.9).

Implements:
- SwR-065: Versioned, ML-ready training dataset generation
  - Temporal train/val/test split (no random, no leakage)
  - Signal-key pivoting (rows → columns)
  - Z-score normalization with saved parameters
  - Metadata with full provenance
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

import pyarrow as pa


@dataclass
class NormalizationParams:
    """Stores mean and std per signal for z-score normalization."""
    mean: dict[str, float] = field(default_factory=dict)
    std: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"mean": self.mean, "std": self.std}


@dataclass
class TrainingSetResult:
    """Result of training set construction."""
    train_table: pa.Table
    val_table: pa.Table
    test_table: pa.Table
    pivoted_train_table: pa.Table
    normalization_params: NormalizationParams
    metadata: dict[str, Any]


def _temporal_split(
    unique_dates: list[str],
    train_ratio: float,
    val_ratio: float,
) -> tuple[list[str], list[str], list[str]]:
    """Split sorted dates into train/val/test by temporal order."""
    n = len(unique_dates)
    if n == 0:
        return [], [], []

    train_end = max(1, int(n * train_ratio))
    val_end = max(train_end + 1, int(n * (train_ratio + val_ratio)))

    train_dates = unique_dates[:train_end]
    val_dates = unique_dates[train_end:val_end]
    test_dates = unique_dates[val_end:]

    return train_dates, val_dates, test_dates


def _filter_by_dates(table: pa.Table, dates_set: set[str]) -> pa.Table:
    """Filter table rows to only those with date in dates_set."""
    if table.num_rows == 0:
        return table
    all_dates = table.column("date").to_pylist()
    mask = [d in dates_set for d in all_dates]
    return table.filter(pa.array(mask, type=pa.bool_()))


def _pivot_table(table: pa.Table) -> pa.Table:
    """Pivot (date, country_id, signal_key, value) → (date, country_id, signal1, signal2, ...)."""
    if table.num_rows == 0:
        return pa.table({
            "date": pa.array([], type=pa.string()),
            "country_id": pa.array([], type=pa.string()),
        })

    dates = table.column("date").to_pylist()
    countries = table.column("country_id").to_pylist()
    signals = table.column("signal_key").to_pylist()
    values = table.column("value").to_pylist()

    # Collect unique signal keys
    signal_keys = sorted(set(signals))

    # Group by (date, country_id)
    groups: dict[tuple[str, str], dict[str, float]] = {}
    for i in range(table.num_rows):
        key = (dates[i], countries[i])
        if key not in groups:
            groups[key] = {}
        groups[key][signals[i]] = values[i]

    # Build pivoted columns
    out_dates: list[str] = []
    out_countries: list[str] = []
    signal_cols: dict[str, list[float]] = {sk: [] for sk in signal_keys}

    for (date, country_id) in sorted(groups.keys()):
        out_dates.append(date)
        out_countries.append(country_id)
        row = groups[(date, country_id)]
        for sk in signal_keys:
            signal_cols[sk].append(row.get(sk, float("nan")))

    cols: dict[str, pa.Array] = {
        "date": pa.array(out_dates, type=pa.string()),
        "country_id": pa.array(out_countries, type=pa.string()),
    }
    for sk in signal_keys:
        cols[sk] = pa.array(signal_cols[sk], type=pa.float64())

    return pa.table(cols)


def _compute_normalization_params(
    pivoted: pa.Table,
    signal_keys: list[str],
) -> NormalizationParams:
    """Compute mean and std from pivoted training data."""
    params = NormalizationParams()
    for sk in signal_keys:
        if sk not in pivoted.column_names:
            continue
        values = [v for v in pivoted.column(sk).to_pylist() if v is not None and not math.isnan(v)]
        if not values:
            params.mean[sk] = 0.0
            params.std[sk] = 1.0
            continue
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / max(len(values) - 1, 1)
        std = math.sqrt(variance)
        params.mean[sk] = mean
        params.std[sk] = std if std > 0 else 1.0
    return params


@dataclass
class TrainingSetBuilder:
    """Builds versioned, ML-ready training datasets from PIT-joined features."""

    version: str = "v1"
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15

    def build(self, *, feature_table: pa.Table) -> TrainingSetResult:
        """Build training set with temporal split, pivoting, normalization.

        Args:
            feature_table: PIT-joined table (date, country_id, signal_key, value)
        """
        if feature_table.num_rows == 0:
            empty = pa.table({
                "date": pa.array([], type=pa.string()),
                "country_id": pa.array([], type=pa.string()),
                "signal_key": pa.array([], type=pa.string()),
                "value": pa.array([], type=pa.float64()),
            })
            empty_pivot = pa.table({
                "date": pa.array([], type=pa.string()),
                "country_id": pa.array([], type=pa.string()),
            })
            return TrainingSetResult(
                train_table=empty,
                val_table=empty,
                test_table=empty,
                pivoted_train_table=empty_pivot,
                normalization_params=NormalizationParams(),
                metadata={
                    "version": self.version,
                    "date_range": [],
                    "signal_keys": [],
                    "train_rows": 0,
                    "val_rows": 0,
                    "test_rows": 0,
                },
            )

        # Get unique dates sorted
        all_dates = feature_table.column("date").to_pylist()
        unique_dates = sorted(set(all_dates))
        signal_keys = sorted(set(feature_table.column("signal_key").to_pylist()))

        # Temporal split
        train_dates, val_dates, test_dates = _temporal_split(
            unique_dates, self.train_ratio, self.val_ratio
        )

        train_table = _filter_by_dates(feature_table, set(train_dates))
        val_table = _filter_by_dates(feature_table, set(val_dates))
        test_table = _filter_by_dates(feature_table, set(test_dates))

        # Pivot train set
        pivoted_train = _pivot_table(train_table)

        # Normalization params from training data only
        norm_params = _compute_normalization_params(pivoted_train, signal_keys)

        metadata = {
            "version": self.version,
            "date_range": [unique_dates[0], unique_dates[-1]] if unique_dates else [],
            "signal_keys": signal_keys,
            "train_rows": train_table.num_rows,
            "val_rows": val_table.num_rows,
            "test_rows": test_table.num_rows,
            "train_dates": len(train_dates),
            "val_dates": len(val_dates),
            "test_dates": len(test_dates),
            "normalization_params": norm_params.to_dict(),
        }

        return TrainingSetResult(
            train_table=train_table,
            val_table=val_table,
            test_table=test_table,
            pivoted_train_table=pivoted_train,
            normalization_params=norm_params,
            metadata=metadata,
        )
