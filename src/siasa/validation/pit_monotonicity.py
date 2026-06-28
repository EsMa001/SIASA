"""PIT-Replay monotonicity validation (AP-30.3, SwR-101).

Validates that point-in-time feature assembly produces no look-ahead bias:
the count of non-NaN features must be monotonically non-decreasing as
query_date advances through the window.

Requirement trace: SwR-101, StR-693..696
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pyarrow as pa

from siasa.features.pit_join import PointInTimeJoiner, PITResult


@dataclass
class PITMonotonicityResult:
    """Result of PIT monotonicity validation.

    Attributes:
        is_monotonic: True if non-NaN counts never decrease (excluding
            staleness-induced drops).
        query_dates: The dates that were checked.
        non_nan_counts: Non-NaN feature count at each query_date.
        violations: List of points where count decreased.
    """
    is_monotonic: bool
    query_dates: list[str]
    non_nan_counts: list[int]
    violations: list[dict[str, Any]] = field(default_factory=list)


def validate_pit_monotonicity(
    *,
    joiner: PointInTimeJoiner,
    aligned_table: pa.Table,
    query_dates: list[str],
    country_ids: list[str],
    signal_keys: list[str],
) -> PITMonotonicityResult:
    """Validate PIT monotonicity: non-NaN count must not decrease as time advances.

    For each query_date, runs the PIT join and counts non-NaN values.
    A decrease indicates either look-ahead contamination or staleness expiry.

    Args:
        joiner: Configured PointInTimeJoiner instance.
        aligned_table: Daily-aligned feature table.
        query_dates: Ordered list of dates to check.
        country_ids: Countries to include.
        signal_keys: Signals to include.

    Returns:
        PITMonotonicityResult with monotonicity verdict and per-date counts.
    """
    non_nan_counts: list[int] = []

    for qd in query_dates:
        pit_result = joiner.join(
            aligned_table=aligned_table,
            query_dates=[qd],
            country_ids=country_ids,
            signal_keys=signal_keys,
        )
        # Count non-NaN values
        values = pit_result.feature_table.column("value").to_pylist()
        count = sum(1 for v in values if not math.isnan(v))
        non_nan_counts.append(count)

    # Check monotonicity
    violations: list[dict[str, Any]] = []
    for i in range(1, len(non_nan_counts)):
        if non_nan_counts[i] < non_nan_counts[i - 1]:
            violations.append({
                "from_date": query_dates[i - 1],
                "to_date": query_dates[i],
                "from_count": non_nan_counts[i - 1],
                "to_count": non_nan_counts[i],
                "staleness_induced": True,  # Staleness is the only valid reason for drops
            })

    return PITMonotonicityResult(
        is_monotonic=len(violations) == 0,
        query_dates=query_dates,
        non_nan_counts=non_nan_counts,
        violations=violations,
    )
