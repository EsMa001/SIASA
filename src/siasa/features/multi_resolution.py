"""SIASA Multi-Resolution Feature-Builder (AP-13.7).

Implements:
- SwR-063: Fast/Slow/Structural feature layers from daily-aligned data
  - Fast Layer: daily signals (pass-through from alignment)
  - Slow Layer: rolling-window aggregates (7d, 30d mean/std) plus
    z-score normalization (AP-17, ALGO-ZSCORE-01) as the basis for a
    sigma-grounded anomaly definition consumed downstream (AP-18)
  - Structural Layer: yearly/structural base values (forward-filled)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import pyarrow as pa

from siasa.data.registry import load_signal_registry

# Granularities considered "structural" (yearly or slower)
_STRUCTURAL_GRANULARITIES = {"yearly", "quarterly"}

# Rolling window sizes in days
_ROLLING_WINDOWS = [7, 30]


@dataclass
class MultiResolutionResult:
    """Three-layer feature decomposition."""
    fast_layer: pa.Table
    slow_layer: pa.Table
    structural_layer: pa.Table


def _classify_signals() -> tuple[set[str], set[str]]:
    """Classify signal keys into daily (fast) vs structural sets."""
    registry = load_signal_registry()
    structural_keys: set[str] = set()
    daily_keys: set[str] = set()
    for entry in registry:
        if entry.native_granularity in _STRUCTURAL_GRANULARITIES:
            structural_keys.add(entry.signal_key)
        else:
            daily_keys.add(entry.signal_key)
    return daily_keys, structural_keys


def compute_zscore(
    value: float,
    mean: Optional[float],
    std: Optional[float],
) -> Optional[float]:
    """z-score normalization (ALGO-ZSCORE-01): ``(value - mean) / std``.

    Returns None when the rolling mean/std are unavailable (insufficient data in
    the window). A zero rolling std (a constant window) yields 0.0 — there is no
    deviation, which must read as "unauffaellig", not as an undefined anomaly.
    """
    if mean is None or std is None:
        return None
    if std == 0.0:
        return 0.0
    return (value - mean) / std


def _compute_rolling_features(
    dates: list[str],
    values: list[float],
) -> dict[str, list[Optional[float]]]:
    """Compute rolling mean, population std and z-score per window size.

    Returns dict mapping column name (``mean_Nd`` / ``std_Nd`` / ``zscore_Nd``) to a
    list of values, with None for rows where the window is not yet full
    (insufficient data).
    """
    n = len(dates)
    result: dict[str, list[Optional[float]]] = {}

    for window in _ROLLING_WINDOWS:
        means: list[Optional[float]] = []
        stds: list[Optional[float]] = []
        zscores: list[Optional[float]] = []
        for i in range(n):
            if i + 1 < window:
                means.append(None)
                stds.append(None)
                zscores.append(None)
            else:
                window_vals = values[i - window + 1: i + 1]
                mean = sum(window_vals) / len(window_vals)
                variance = sum((v - mean) ** 2 for v in window_vals) / len(window_vals)
                std = math.sqrt(variance)
                means.append(mean)
                stds.append(std)
                zscores.append(compute_zscore(values[i], mean, std))
        result[f"mean_{window}d"] = means
        result[f"std_{window}d"] = stds
        result[f"zscore_{window}d"] = zscores

    return result


@dataclass
class MultiResolutionBuilder:
    """Builds multi-resolution feature layers from daily-aligned data."""

    def build(self, *, aligned_table: pa.Table) -> MultiResolutionResult:
        """Split aligned data into Fast/Slow/Structural layers.

        Args:
            aligned_table: Daily-aligned table from DailyAligner
                with columns: date, country_id, signal_key, value
        """
        if aligned_table.num_rows == 0:
            empty_fast = pa.table({
                "date": pa.array([], type=pa.string()),
                "country_id": pa.array([], type=pa.string()),
                "signal_key": pa.array([], type=pa.string()),
                "value": pa.array([], type=pa.float64()),
            })
            empty_slow = pa.table({
                "date": pa.array([], type=pa.string()),
                "country_id": pa.array([], type=pa.string()),
                "signal_key": pa.array([], type=pa.string()),
                "value": pa.array([], type=pa.float64()),
                "mean_7d": pa.array([], type=pa.float64()),
                "mean_30d": pa.array([], type=pa.float64()),
                "std_7d": pa.array([], type=pa.float64()),
                "std_30d": pa.array([], type=pa.float64()),
                "zscore_7d": pa.array([], type=pa.float64()),
                "zscore_30d": pa.array([], type=pa.float64()),
            })
            empty_structural = pa.table({
                "date": pa.array([], type=pa.string()),
                "country_id": pa.array([], type=pa.string()),
                "signal_key": pa.array([], type=pa.string()),
                "value": pa.array([], type=pa.float64()),
            })
            return MultiResolutionResult(
                fast_layer=empty_fast,
                slow_layer=empty_slow,
                structural_layer=empty_structural,
            )

        daily_keys, structural_keys = _classify_signals()

        # Extract columns
        all_dates = aligned_table.column("date").to_pylist()
        all_countries = aligned_table.column("country_id").to_pylist()
        all_signals = aligned_table.column("signal_key").to_pylist()
        all_values = aligned_table.column("value").to_pylist()

        # --- Fast Layer: daily signals only ---
        fast_dates, fast_countries, fast_signals, fast_values = [], [], [], []
        # --- Structural Layer: yearly/quarterly signals ---
        struct_dates, struct_countries, struct_signals, struct_values = [], [], [], []

        for i in range(aligned_table.num_rows):
            sk = all_signals[i]
            if sk in structural_keys:
                struct_dates.append(all_dates[i])
                struct_countries.append(all_countries[i])
                struct_signals.append(sk)
                struct_values.append(all_values[i])
            else:
                fast_dates.append(all_dates[i])
                fast_countries.append(all_countries[i])
                fast_signals.append(sk)
                fast_values.append(all_values[i])

        fast_layer = pa.table({
            "date": pa.array(fast_dates, type=pa.string()),
            "country_id": pa.array(fast_countries, type=pa.string()),
            "signal_key": pa.array(fast_signals, type=pa.string()),
            "value": pa.array(fast_values, type=pa.float64()),
        })

        structural_layer = pa.table({
            "date": pa.array(struct_dates, type=pa.string()),
            "country_id": pa.array(struct_countries, type=pa.string()),
            "signal_key": pa.array(struct_signals, type=pa.string()),
            "value": pa.array(struct_values, type=pa.float64()),
        })

        # --- Slow Layer: rolling-window features per (country, signal) ---
        # Group fast data by (country_id, signal_key), sorted by date
        groups: dict[tuple[str, str], list[tuple[str, float]]] = {}
        for i in range(len(fast_dates)):
            key = (fast_countries[i], fast_signals[i])
            if key not in groups:
                groups[key] = []
            groups[key].append((fast_dates[i], fast_values[i]))

        slow_dates: list[str] = []
        slow_countries: list[str] = []
        slow_signals: list[str] = []
        slow_values: list[float] = []
        slow_rolling: dict[str, list[Optional[float]]] = {}
        for w in _ROLLING_WINDOWS:
            for metric in ("mean", "std", "zscore"):
                slow_rolling[f"{metric}_{w}d"] = []

        for (country_id, signal_key), entries in sorted(groups.items()):
            entries.sort(key=lambda x: x[0])  # sort by date
            dates = [e[0] for e in entries]
            vals = [e[1] for e in entries]

            rolling = _compute_rolling_features(dates, vals)

            for i in range(len(dates)):
                slow_dates.append(dates[i])
                slow_countries.append(country_id)
                slow_signals.append(signal_key)
                slow_values.append(vals[i])
                for col_name in slow_rolling:
                    slow_rolling[col_name].append(rolling[col_name][i])

        slow_cols: dict[str, pa.Array] = {
            "date": pa.array(slow_dates, type=pa.string()),
            "country_id": pa.array(slow_countries, type=pa.string()),
            "signal_key": pa.array(slow_signals, type=pa.string()),
            "value": pa.array(slow_values, type=pa.float64()),
        }
        for col_name, col_values in slow_rolling.items():
            slow_cols[col_name] = pa.array(col_values, type=pa.float64())

        slow_layer = pa.table(slow_cols)

        return MultiResolutionResult(
            fast_layer=fast_layer,
            slow_layer=slow_layer,
            structural_layer=structural_layer,
        )
