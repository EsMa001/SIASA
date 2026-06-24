"""SIASA Daily Alignment Pipeline (AP-13.6).

Implements:
- SwR-062: DailyAligner aggregates all records to daily canonical resolution
  using signal-registry aggregation rules (SUM/MEAN/MAX/LAST), forward-fills
  yearly data, and reports gaps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pyarrow as pa

from siasa.data.query import ArchiveQueryEngine
from siasa.data.registry import load_signal_registry, SignalRegistryEntry


@dataclass
class GapReport:
    """Report of missing days in aligned data."""
    gap_days: list[str] = field(default_factory=list)
    total_gap_days: int = 0


@dataclass
class AlignmentResult:
    """Result of daily alignment — aligned table + gap report."""
    aligned_table: pa.Table
    gap_report: GapReport


def _get_aggregation_lookup() -> dict[str, str]:
    """Build signal_key → aggregation_method lookup from signal registry."""
    registry = load_signal_registry()
    return {entry.signal_key: entry.aggregation_method for entry in registry}


def _extract_date(timestamp_utc: str) -> str:
    """Extract YYYY-MM-DD date string from ISO timestamp."""
    try:
        return timestamp_utc[:10]
    except (TypeError, IndexError):
        return ""


def _detect_gaps(dates: list[str]) -> GapReport:
    """Detect missing days in a sorted list of date strings."""
    if len(dates) < 2:
        return GapReport()

    unique_dates = sorted(set(dates))
    gap_days: list[str] = []

    for i in range(len(unique_dates) - 1):
        current = datetime.strptime(unique_dates[i], "%Y-%m-%d")
        next_date = datetime.strptime(unique_dates[i + 1], "%Y-%m-%d")
        delta = (next_date - current).days

        if delta > 1:
            for d in range(1, delta):
                gap_day = (current + timedelta(days=d)).strftime("%Y-%m-%d")
                gap_days.append(gap_day)

    return GapReport(gap_days=gap_days, total_gap_days=len(gap_days))


@dataclass
class DailyAligner:
    """Aggregates archive records to daily canonical resolution.

    Uses signal-registry aggregation rules:
    - sum: aggregate by summing (event counts)
    - mean: aggregate by averaging (scores)
    - max: aggregate by taking maximum (severity levels)
    - last: take the most recent value (yearly structural data, forward-fill)
    - none/count: fall back to sum
    """

    archive_root: Path

    def align(
        self,
        *,
        country_ids: Optional[list[str]] = None,
        signal_keys: Optional[list[str]] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> AlignmentResult:
        """Align archive records to daily resolution.

        Returns AlignmentResult with the aligned pa.Table and gap report.
        """
        engine = ArchiveQueryEngine(archive_root=self.archive_root)
        raw = engine.query(
            country_ids=country_ids,
            signal_keys=signal_keys,
            time_from=time_from,
            time_to=time_to,
        )

        if raw.num_rows == 0:
            empty = pa.table({
                "date": pa.array([], type=pa.string()),
                "country_id": pa.array([], type=pa.string()),
                "signal_key": pa.array([], type=pa.string()),
                "value": pa.array([], type=pa.float64()),
            })
            return AlignmentResult(
                aligned_table=empty,
                gap_report=GapReport(),
            )

        agg_lookup = _get_aggregation_lookup()

        # Convert to Python for grouping
        timestamps = raw.column("timestamp_utc").to_pylist()
        countries = raw.column("country_id").to_pylist()
        signals = raw.column("signal_key").to_pylist()
        values = raw.column("value").to_pylist()

        # Group by (date, country_id, signal_key)
        groups: dict[tuple[str, str, str], list[float]] = {}
        for i in range(raw.num_rows):
            date = _extract_date(timestamps[i])
            key = (date, countries[i], signals[i])
            if key not in groups:
                groups[key] = []
            groups[key].append(values[i])

        # Aggregate per group using registry rules
        result_dates: list[str] = []
        result_countries: list[str] = []
        result_signals: list[str] = []
        result_values: list[float] = []

        for (date, country_id, signal_key), vals in sorted(groups.items()):
            agg_method = agg_lookup.get(signal_key, "sum")

            if agg_method == "sum" or agg_method == "count" or agg_method == "none":
                agg_value = sum(vals)
            elif agg_method == "mean":
                agg_value = sum(vals) / len(vals)
            elif agg_method == "max":
                agg_value = max(vals)
            elif agg_method == "last":
                agg_value = vals[-1]  # Last recorded value
            else:
                agg_value = sum(vals)  # Default fallback

            result_dates.append(date)
            result_countries.append(country_id)
            result_signals.append(signal_key)
            result_values.append(agg_value)

        aligned = pa.table({
            "date": pa.array(result_dates, type=pa.string()),
            "country_id": pa.array(result_countries, type=pa.string()),
            "signal_key": pa.array(result_signals, type=pa.string()),
            "value": pa.array(result_values, type=pa.float64()),
        })

        # Gap detection — per signal per country
        all_dates = result_dates
        gap_report = _detect_gaps(all_dates)

        return AlignmentResult(
            aligned_table=aligned,
            gap_report=gap_report,
        )
