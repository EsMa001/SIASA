"""Tests for AP-13.8 — Point-in-Time Join Engine.

Verifies:
- SwR-064: PointInTimeJoiner provides look-ahead-bias-free feature assembly
  - For each (country, date), pull the last known value per signal
  - Configurable staleness limits (max days since last observation)
  - Explicit missing-value marking (NaN) for stale or absent signals
  - Anti-leakage: no future data leaks into past observations
"""
from __future__ import annotations

import math

import pyarrow as pa

from siasa.features.pit_join import PointInTimeJoiner, PITResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_multi_signal_table() -> pa.Table:
    """Build aligned table with multiple signals at different dates."""
    return pa.table({
        "date": pa.array([
            # conflict_event_count: days 10, 12, 15
            "2026-06-10", "2026-06-12", "2026-06-15",
            # gdp_growth: only day 01 (yearly structural)
            "2026-06-01",
            # disaster_alert_level: days 10, 14
            "2026-06-10", "2026-06-14",
        ], type=pa.string()),
        "country_id": pa.array(["UKR"] * 6, type=pa.string()),
        "signal_key": pa.array([
            "conflict_event_count", "conflict_event_count", "conflict_event_count",
            "gdp_growth",
            "disaster_alert_level", "disaster_alert_level",
        ], type=pa.string()),
        "value": pa.array([10.0, 20.0, 30.0, 1.3, 2.0, 3.0], type=pa.float64()),
    })


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_pit_joiner_construction() -> None:
    """PointInTimeJoiner must accept staleness_limit_days."""
    joiner = PointInTimeJoiner(staleness_limit_days=30)
    assert joiner.staleness_limit_days == 30


# ---------------------------------------------------------------------------
# Last-known-value semantics
# ---------------------------------------------------------------------------

def test_pit_join_uses_last_known_value() -> None:
    """For a query date, the joiner must return the most recent value before/on that date."""
    table = _build_multi_signal_table()
    joiner = PointInTimeJoiner(staleness_limit_days=30)

    result = joiner.join(
        aligned_table=table,
        query_dates=["2026-06-13"],
        country_ids=["UKR"],
        signal_keys=["conflict_event_count"],
    )
    assert isinstance(result, PITResult)
    pit_table = result.feature_table

    # On 2026-06-13, last known conflict_event_count is from 2026-06-12 = 20.0
    values = pit_table.column("value").to_pylist()
    assert len(values) == 1
    assert values[0] == 20.0


# ---------------------------------------------------------------------------
# Anti-leakage
# ---------------------------------------------------------------------------

def test_pit_join_no_future_leakage() -> None:
    """Values from dates after the query date must NOT appear (anti-leakage)."""
    table = _build_multi_signal_table()
    joiner = PointInTimeJoiner(staleness_limit_days=30)

    result = joiner.join(
        aligned_table=table,
        query_dates=["2026-06-11"],
        country_ids=["UKR"],
        signal_keys=["conflict_event_count"],
    )
    pit_table = result.feature_table
    values = pit_table.column("value").to_pylist()
    assert len(values) == 1
    # On 2026-06-11, only 2026-06-10 (10.0) is available, NOT 12 or 15
    assert values[0] == 10.0


# ---------------------------------------------------------------------------
# Staleness limit
# ---------------------------------------------------------------------------

def test_pit_join_staleness_limit_marks_nan() -> None:
    """When last observation is older than staleness_limit_days, value must be NaN."""
    table = _build_multi_signal_table()
    joiner = PointInTimeJoiner(staleness_limit_days=3)

    # Query on 2026-06-20 — last conflict_event_count is on 2026-06-15 (5 days ago)
    result = joiner.join(
        aligned_table=table,
        query_dates=["2026-06-20"],
        country_ids=["UKR"],
        signal_keys=["conflict_event_count"],
    )
    pit_table = result.feature_table
    values = pit_table.column("value").to_pylist()
    assert len(values) == 1
    assert math.isnan(values[0]), f"Expected NaN for stale value, got {values[0]}"


def test_pit_join_within_staleness_limit() -> None:
    """When last observation is within staleness_limit_days, value must be present."""
    table = _build_multi_signal_table()
    joiner = PointInTimeJoiner(staleness_limit_days=5)

    # Query on 2026-06-17 — last conflict_event_count is on 2026-06-15 (2 days ago)
    result = joiner.join(
        aligned_table=table,
        query_dates=["2026-06-17"],
        country_ids=["UKR"],
        signal_keys=["conflict_event_count"],
    )
    pit_table = result.feature_table
    values = pit_table.column("value").to_pylist()
    assert len(values) == 1
    assert values[0] == 30.0


# ---------------------------------------------------------------------------
# Missing signal
# ---------------------------------------------------------------------------

def test_pit_join_missing_signal_is_nan() -> None:
    """Requesting a signal with no data at all must produce NaN."""
    table = _build_multi_signal_table()
    joiner = PointInTimeJoiner(staleness_limit_days=30)

    result = joiner.join(
        aligned_table=table,
        query_dates=["2026-06-15"],
        country_ids=["UKR"],
        signal_keys=["nonexistent_signal"],
    )
    pit_table = result.feature_table
    values = pit_table.column("value").to_pylist()
    assert len(values) == 1
    assert math.isnan(values[0])


# ---------------------------------------------------------------------------
# Multiple query dates
# ---------------------------------------------------------------------------

def test_pit_join_multiple_query_dates() -> None:
    """Joiner must handle multiple query dates correctly."""
    table = _build_multi_signal_table()
    joiner = PointInTimeJoiner(staleness_limit_days=30)

    result = joiner.join(
        aligned_table=table,
        query_dates=["2026-06-10", "2026-06-13", "2026-06-16"],
        country_ids=["UKR"],
        signal_keys=["conflict_event_count"],
    )
    pit_table = result.feature_table
    values = pit_table.column("value").to_pylist()
    assert len(values) == 3
    assert values[0] == 10.0   # 2026-06-10
    assert values[1] == 20.0   # 2026-06-13 (last known from 2026-06-12)
    assert values[2] == 30.0   # 2026-06-16 (last known from 2026-06-15)


# ---------------------------------------------------------------------------
# Multiple signals
# ---------------------------------------------------------------------------

def test_pit_join_multiple_signals() -> None:
    """Joiner must pivot multiple signals per (country, date)."""
    table = _build_multi_signal_table()
    joiner = PointInTimeJoiner(staleness_limit_days=30)

    result = joiner.join(
        aligned_table=table,
        query_dates=["2026-06-14"],
        country_ids=["UKR"],
        signal_keys=["conflict_event_count", "disaster_alert_level"],
    )
    pit_table = result.feature_table
    # Should have 2 rows: one per signal
    assert pit_table.num_rows == 2
    sigs = set(pit_table.column("signal_key").to_pylist())
    assert sigs == {"conflict_event_count", "disaster_alert_level"}


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

def test_pit_result_has_expected_columns() -> None:
    """PITResult.feature_table must have date, country_id, signal_key, value columns."""
    table = _build_multi_signal_table()
    joiner = PointInTimeJoiner(staleness_limit_days=30)
    result = joiner.join(
        aligned_table=table,
        query_dates=["2026-06-14"],
        country_ids=["UKR"],
        signal_keys=["conflict_event_count"],
    )
    columns = set(result.feature_table.column_names)
    assert {"date", "country_id", "signal_key", "value"}.issubset(columns)


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_pit_join_empty_table() -> None:
    """Joining on empty aligned table must return 0-row result, not crash."""
    empty = pa.table({
        "date": pa.array([], type=pa.string()),
        "country_id": pa.array([], type=pa.string()),
        "signal_key": pa.array([], type=pa.string()),
        "value": pa.array([], type=pa.float64()),
    })
    joiner = PointInTimeJoiner(staleness_limit_days=30)
    result = joiner.join(
        aligned_table=empty,
        query_dates=["2026-06-15"],
        country_ids=["UKR"],
        signal_keys=["conflict_event_count"],
    )
    pit_table = result.feature_table
    # 1 row with NaN (requested but missing)
    assert pit_table.num_rows == 1
    assert math.isnan(pit_table.column("value")[0].as_py())
