"""SIASA PyTorch Time-Series Dataset (AP-13.10).

Implements:
- SwR-066: SIASATimeSeriesDataset with configurable lookback/horizon,
  country/feature filtering, zero-copy Arrow→Tensor conversion,
  and batch collation for variable-length sequences.
"""
from __future__ import annotations

from typing import Optional, Sequence

import pyarrow as pa
import torch
from torch.utils.data import Dataset


class SIASATimeSeriesDataset(Dataset):
    """PyTorch Dataset for SIASA time-series windows.

    Loads data from an Arrow table with columns:
      - country_id: str
      - date: str (ISO date)
      - <feature columns>: float

    Each sample is a (input, target) pair where:
      - input: Tensor of shape (window_size, num_features)
      - target: Tensor of shape (prediction_horizon, num_features)
    """

    _METADATA_COLS = {"country_id", "date"}

    def __init__(
        self,
        table: pa.Table,
        window_size: int = 90,
        prediction_horizon: int = 7,
        countries: Optional[Sequence[str]] = None,
        features: Optional[Sequence[str]] = None,
    ) -> None:
        self.window_size = window_size
        self.prediction_horizon = prediction_horizon

        # Determine feature columns
        all_cols = set(table.column_names) - self._METADATA_COLS
        if features is not None:
            self._feature_cols = [f for f in features if f in all_cols]
        else:
            self._feature_cols = sorted(all_cols)

        # Convert to pandas-like dict for processing
        country_col = table.column("country_id").to_pylist()
        date_col = table.column("date").to_pylist()

        # Filter countries if requested
        if countries is not None:
            country_set = set(countries)
            mask = [c in country_set for c in country_col]
            indices = [i for i, m in enumerate(mask) if m]
            table = table.take(indices)
            country_col = [country_col[i] for i in indices]
            date_col = [date_col[i] for i in indices]

        # Build per-country sorted feature matrices
        self._windows: list[tuple[torch.Tensor, torch.Tensor]] = []

        # Group by country
        country_groups: dict[str, list[int]] = {}
        for i, c in enumerate(country_col):
            country_groups.setdefault(c, []).append(i)

        # Extract feature data as flat lists for speed
        feature_data: dict[str, list[float]] = {}
        for fc in self._feature_cols:
            feature_data[fc] = table.column(fc).to_pylist()

        for country_id, row_indices in country_groups.items():
            # Sort by date
            sorted_indices = sorted(row_indices, key=lambda i: date_col[i])
            n_rows = len(sorted_indices)

            total_needed = window_size + prediction_horizon
            if n_rows < total_needed:
                continue

            # Build feature matrix (n_rows, n_features)
            matrix = torch.zeros(n_rows, len(self._feature_cols))
            for col_idx, fc in enumerate(self._feature_cols):
                col_data = feature_data[fc]
                for row_idx, orig_idx in enumerate(sorted_indices):
                    matrix[row_idx, col_idx] = float(col_data[orig_idx])

            # Generate sliding windows
            num_windows = n_rows - total_needed + 1
            for start in range(num_windows):
                x = matrix[start : start + window_size]
                y = matrix[start + window_size : start + total_needed]
                self._windows.append((x, y))

    def __len__(self) -> int:
        return len(self._windows)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self._windows[idx]

    @property
    def feature_columns(self) -> list[str]:
        """Return the list of feature column names used."""
        return list(self._feature_cols)


def siasa_collate_fn(
    batch: list[tuple[torch.Tensor, torch.Tensor]],
) -> tuple[torch.Tensor, torch.Tensor]:
    """Collate function for batching SIASATimeSeriesDataset samples.

    Stacks (input, target) pairs into batched tensors.
    All samples in a batch must have the same window_size and horizon.

    Returns:
        (x_batch, y_batch) where shapes are:
            x_batch: (batch_size, window_size, num_features)
            y_batch: (batch_size, prediction_horizon, num_features)
    """
    x_list, y_list = zip(*batch)
    return torch.stack(x_list), torch.stack(y_list)
