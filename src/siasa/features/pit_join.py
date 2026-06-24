"""SIASA Point-in-Time Join Engine (AP-13.8).

Implements:
- SwR-064: Look-ahead-bias-free feature assembly
  - For each (country, date), pull the last known value per signal
  - Configurable staleness limits (max days since last observation)
  - Explicit NaN for stale or absent signals
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import pyarrow as pa


@dataclass
class PITResult:
    """Result of point-in-time join — feature table with no future leakage."""
    feature_table: pa.Table


@dataclass
class PointInTimeJoiner:
    """Assembles features at specific query dates using only past data.

    For each (country, query_date, signal_key), finds the most recent
    observation on or before query_date. If the observation is older
    than staleness_limit_days, marks the value as NaN.
    """

    staleness_limit_days: int = 30

    def join(
        self,
        *,
        aligned_table: pa.Table,
        query_dates: list[str],
        country_ids: list[str],
        signal_keys: list[str],
    ) -> PITResult:
        """Join aligned data at specific query dates.

        Args:
            aligned_table: Daily-aligned table (date, country_id, signal_key, value)
            query_dates: Dates at which to assemble features (YYYY-MM-DD)
            country_ids: Countries to include
            signal_keys: Signals to include
        """
        # Build lookup: (country_id, signal_key) -> sorted list of (date, value)
        lookup: dict[tuple[str, str], list[tuple[str, float]]] = {}

        if aligned_table.num_rows > 0:
            all_dates = aligned_table.column("date").to_pylist()
            all_countries = aligned_table.column("country_id").to_pylist()
            all_signals = aligned_table.column("signal_key").to_pylist()
            all_values = aligned_table.column("value").to_pylist()

            for i in range(aligned_table.num_rows):
                key = (all_countries[i], all_signals[i])
                if key not in lookup:
                    lookup[key] = []
                lookup[key].append((all_dates[i], all_values[i]))

            # Sort each series by date
            for key in lookup:
                lookup[key].sort(key=lambda x: x[0])

        # Assemble features
        result_dates: list[str] = []
        result_countries: list[str] = []
        result_signals: list[str] = []
        result_values: list[float] = []

        for query_date in query_dates:
            for country_id in country_ids:
                for signal_key in signal_keys:
                    value = self._find_last_known(
                        lookup=lookup,
                        country_id=country_id,
                        signal_key=signal_key,
                        query_date=query_date,
                    )
                    result_dates.append(query_date)
                    result_countries.append(country_id)
                    result_signals.append(signal_key)
                    result_values.append(value)

        feature_table = pa.table({
            "date": pa.array(result_dates, type=pa.string()),
            "country_id": pa.array(result_countries, type=pa.string()),
            "signal_key": pa.array(result_signals, type=pa.string()),
            "value": pa.array(result_values, type=pa.float64()),
        })

        return PITResult(feature_table=feature_table)

    def _find_last_known(
        self,
        *,
        lookup: dict[tuple[str, str], list[tuple[str, float]]],
        country_id: str,
        signal_key: str,
        query_date: str,
    ) -> float:
        """Find the last known value for (country, signal) on or before query_date.

        Returns NaN if no data exists or if the last observation is stale.
        """
        series = lookup.get((country_id, signal_key))
        if not series:
            return float("nan")

        # Binary search for the latest date <= query_date
        best_date: Optional[str] = None
        best_value: float = float("nan")

        for date, value in series:
            if date <= query_date:
                best_date = date
                best_value = value
            else:
                break  # Series is sorted, no need to continue

        if best_date is None:
            return float("nan")

        # Check staleness
        try:
            query_dt = datetime.strptime(query_date, "%Y-%m-%d")
            best_dt = datetime.strptime(best_date, "%Y-%m-%d")
            days_since = (query_dt - best_dt).days
            if days_since > self.staleness_limit_days:
                return float("nan")
        except ValueError:
            pass  # If dates can't be parsed, skip staleness check

        return best_value
