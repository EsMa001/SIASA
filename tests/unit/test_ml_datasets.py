"""Tests for SIASATimeSeriesDataset (AP-13.10 / SwR-066).

Verifies:
- Dataset creation from Arrow table with configurable window and horizon
- __getitem__ returns (input, target) tensor pairs with correct shapes
- Country and feature filtering
- Collate function for variable-length batch assembly
- Edge cases: short sequences, single country, single feature
"""
from __future__ import annotations

import pyarrow as pa
import pytest
import torch

from siasa.ml.datasets import SIASATimeSeriesDataset, siasa_collate_fn


def _make_sample_table(
    countries: list[str] | None = None,
    num_days: int = 120,
    features: list[str] | None = None,
) -> pa.Table:
    """Create a sample Arrow table mimicking pivoted training data."""
    if countries is None:
        countries = ["UKR", "DEU"]
    if features is None:
        features = ["conflict_event_count", "fx_rate", "gdp_growth"]

    rows: list[dict] = []
    for c in countries:
        for d in range(num_days):
            row = {
                "country_id": c,
                "date": f"2025-{1 + d // 30:02d}-{1 + d % 30:02d}",
            }
            for i, f in enumerate(features):
                row[f] = float(d * (i + 1) + hash(c) % 100)
            rows.append(row)

    arrays: dict[str, list] = {k: [] for k in rows[0]}
    for row in rows:
        for k, v in row.items():
            arrays[k].append(v)

    return pa.table(arrays)


# --- TC-SwR-066-001: Dataset creation and basic properties ---

def test_dataset_creation_with_defaults() -> None:
    table = _make_sample_table()
    ds = SIASATimeSeriesDataset(table, window_size=30, prediction_horizon=7)
    assert len(ds) > 0
    assert ds.window_size == 30
    assert ds.prediction_horizon == 7


def test_dataset_getitem_returns_tensor_pair() -> None:
    table = _make_sample_table()
    ds = SIASATimeSeriesDataset(table, window_size=30, prediction_horizon=7)
    x, y = ds[0]
    assert isinstance(x, torch.Tensor)
    assert isinstance(y, torch.Tensor)


def test_dataset_output_shapes() -> None:
    features = ["conflict_event_count", "fx_rate", "gdp_growth"]
    table = _make_sample_table(features=features)
    ds = SIASATimeSeriesDataset(table, window_size=30, prediction_horizon=7)
    x, y = ds[0]
    assert x.shape == (30, 3), f"Expected (30, 3), got {x.shape}"
    assert y.shape == (7, 3), f"Expected (7, 3), got {y.shape}"


def test_dataset_country_filtering() -> None:
    table = _make_sample_table(countries=["UKR", "DEU", "FRA"])
    ds_all = SIASATimeSeriesDataset(table, window_size=30, prediction_horizon=7)
    ds_filtered = SIASATimeSeriesDataset(
        table, window_size=30, prediction_horizon=7, countries=["UKR"]
    )
    assert len(ds_filtered) < len(ds_all)
    assert len(ds_filtered) > 0


def test_dataset_feature_filtering() -> None:
    features = ["conflict_event_count", "fx_rate", "gdp_growth"]
    table = _make_sample_table(features=features)
    ds = SIASATimeSeriesDataset(
        table,
        window_size=30,
        prediction_horizon=7,
        features=["conflict_event_count", "fx_rate"],
    )
    x, y = ds[0]
    assert x.shape[1] == 2
    assert y.shape[1] == 2


def test_collate_fn_batches_correctly() -> None:
    table = _make_sample_table()
    ds = SIASATimeSeriesDataset(table, window_size=30, prediction_horizon=7)
    batch = [ds[i] for i in range(min(4, len(ds)))]
    x_batch, y_batch = siasa_collate_fn(batch)
    assert x_batch.shape[0] == len(batch)
    assert y_batch.shape[0] == len(batch)
    assert x_batch.shape[1] == 30
    assert y_batch.shape[1] == 7


def test_dataset_no_nan_in_valid_window() -> None:
    table = _make_sample_table(num_days=120)
    ds = SIASATimeSeriesDataset(table, window_size=30, prediction_horizon=7)
    x, y = ds[0]
    assert not torch.isnan(x).any(), "Input tensor has NaN"
    assert not torch.isnan(y).any(), "Target tensor has NaN"


def test_dataset_single_country() -> None:
    table = _make_sample_table(countries=["UKR"], num_days=60)
    ds = SIASATimeSeriesDataset(table, window_size=10, prediction_horizon=5)
    assert len(ds) > 0
    x, y = ds[0]
    assert x.shape == (10, 3)
    assert y.shape == (5, 3)


def test_dataset_too_short_raises_or_empty() -> None:
    """If sequence is shorter than window+horizon, dataset should be empty."""
    table = _make_sample_table(countries=["UKR"], num_days=5)
    ds = SIASATimeSeriesDataset(table, window_size=30, prediction_horizon=7)
    assert len(ds) == 0
