"""Tests for AP-13.4 — DuckDB Query-Layer over Parquet archive.

Verifies:
- SwR-060: ArchiveQueryEngine provides analytical queries over Parquet archive
  - Time-window queries
  - Country/domain filtering
  - Aggregations (count, mean, sum, min, max)
  - Arrow table output for ML pipelines
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa

from siasa.data.normalized_models import NormalizedRecord
from siasa.data.archive import ArchiveWriter
from siasa.data.query import ArchiveQueryEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _seed_archive(archive_root: Path) -> None:
    """Seed a small test archive with diverse records."""
    records = [
        NormalizedRecord(
            normalized_id="NORM-1",
            country_id="DEU",
            timestamp="2026-01-15T12:00:00Z",
            domain="D",
            signal_key="gdp_growth",
            value=1.3,
            provenance_source_id="WB-INDICATORS",
            period_start="2026-01-01T00:00:00Z",
            period_end="2026-12-31T23:59:59Z",
            granularity="yearly",
            quality_context={"mapping_id": "MAP-WB-v1", "freshness_hours": 100},
        ),
        NormalizedRecord(
            normalized_id="NORM-2",
            country_id="DEU",
            timestamp="2026-03-10T08:00:00Z",
            domain="B",
            signal_key="conflict_event_count",
            value=5.0,
            provenance_source_id="SRC-GDELT-EVENTS",
            period_start="2026-03-10T00:00:00Z",
            period_end="2026-03-11T00:00:00Z",
            granularity="daily",
            quality_context={"mapping_id": "MAP-GDELT-v1", "freshness_hours": 2},
        ),
        NormalizedRecord(
            normalized_id="NORM-3",
            country_id="UKR",
            timestamp="2026-06-20T14:00:00Z",
            domain="B",
            signal_key="conflict_event_count",
            value=42.0,
            provenance_source_id="SRC-GDELT-EVENTS",
            period_start="2026-06-20T00:00:00Z",
            period_end="2026-06-21T00:00:00Z",
            granularity="daily",
            quality_context={"mapping_id": "MAP-GDELT-v1", "freshness_hours": 1},
        ),
        NormalizedRecord(
            normalized_id="NORM-4",
            country_id="UKR",
            timestamp="2025-12-01T00:00:00Z",
            domain="C",
            signal_key="unhcr_refugees",
            value=6300000.0,
            provenance_source_id="UNHCR-POPULATION",
            period_start="2025-01-01T00:00:00Z",
            period_end="2025-12-31T23:59:59Z",
            granularity="yearly",
            quality_context={"mapping_id": "MAP-UNHCR-v1", "freshness_hours": 4380},
        ),
        NormalizedRecord(
            normalized_id="NORM-5",
            country_id="USA",
            timestamp="2026-06-23T00:00:00Z",
            domain="E",
            signal_key="cyber_kev_recent_count",
            value=5.0,
            provenance_source_id="SRC-CISA-KEV",
            granularity="daily",
            quality_context={"mapping_id": "MAP-CISA-v1", "freshness_hours": 0},
        ),
    ]
    writer = ArchiveWriter(archive_root=archive_root)
    writer.write(records=records, run_id="RUN-SEED-001")


# ---------------------------------------------------------------------------
# Query all
# ---------------------------------------------------------------------------

def test_query_all_returns_all_records(tmp_path: Path) -> None:
    """query_all() must return every record in the archive."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.query_all()
    assert isinstance(result, pa.Table)
    assert result.num_rows == 5


# ---------------------------------------------------------------------------
# Country filter
# ---------------------------------------------------------------------------

def test_query_by_country(tmp_path: Path) -> None:
    """query() with country_ids must filter to those countries only."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.query(country_ids=["UKR"])
    assert result.num_rows == 2
    assert set(result.column("country_id").to_pylist()) == {"UKR"}


def test_query_by_multiple_countries(tmp_path: Path) -> None:
    """query() with multiple country_ids."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.query(country_ids=["DEU", "USA"])
    assert result.num_rows == 3
    assert set(result.column("country_id").to_pylist()) == {"DEU", "USA"}


# ---------------------------------------------------------------------------
# Domain filter
# ---------------------------------------------------------------------------

def test_query_by_domain(tmp_path: Path) -> None:
    """query() with domains must filter to those domains only."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.query(domains=["B"])
    assert result.num_rows == 2
    assert set(result.column("domain").to_pylist()) == {"B"}


# ---------------------------------------------------------------------------
# Time window
# ---------------------------------------------------------------------------

def test_query_by_time_window(tmp_path: Path) -> None:
    """query() with time_from/time_to must filter by timestamp_utc."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.query(time_from="2026-06-01T00:00:00Z", time_to="2026-06-30T23:59:59Z")
    # Should match NORM-3 (UKR June) and NORM-5 (USA June)
    assert result.num_rows == 2
    country_ids = set(result.column("country_id").to_pylist())
    assert country_ids == {"UKR", "USA"}


def test_query_time_from_only(tmp_path: Path) -> None:
    """query() with only time_from must include all records from that point."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.query(time_from="2026-06-01T00:00:00Z")
    assert result.num_rows == 2  # June records only


def test_query_time_to_only(tmp_path: Path) -> None:
    """query() with only time_to must include all records up to that point."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.query(time_to="2026-01-31T23:59:59Z")
    assert result.num_rows == 2  # DEU Jan + UKR Dec 2025


# ---------------------------------------------------------------------------
# Combined filters
# ---------------------------------------------------------------------------

def test_query_combined_country_domain_time(tmp_path: Path) -> None:
    """query() with combined filters must apply AND logic."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.query(
        country_ids=["DEU"],
        domains=["B"],
        time_from="2026-01-01T00:00:00Z",
    )
    assert result.num_rows == 1
    assert result.column("signal_key")[0].as_py() == "conflict_event_count"


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------

def test_aggregate_count(tmp_path: Path) -> None:
    """aggregate() with func='count' must return row count per group."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.aggregate(group_by=["domain"], func="count")
    assert isinstance(result, pa.Table)
    domains = result.column("domain").to_pylist()
    counts = result.column("count").to_pylist()
    domain_counts = dict(zip(domains, counts))
    assert domain_counts["B"] == 2
    assert domain_counts["D"] == 1
    assert domain_counts["E"] == 1
    assert domain_counts["C"] == 1


def test_aggregate_mean(tmp_path: Path) -> None:
    """aggregate() with func='mean' must return mean value per group."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.aggregate(
        group_by=["domain"],
        func="mean",
        domains=["B"],
    )
    assert result.num_rows == 1
    assert result.column("domain")[0].as_py() == "B"
    # mean of 5.0 and 42.0 = 23.5
    assert abs(result.column("mean_value")[0].as_py() - 23.5) < 0.01


def test_aggregate_sum(tmp_path: Path) -> None:
    """aggregate() with func='sum' must return sum of values per group."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.aggregate(group_by=["country_id"], func="sum")
    countries = result.column("country_id").to_pylist()
    sums = result.column("sum_value").to_pylist()
    country_sums = dict(zip(countries, sums))
    assert abs(country_sums["DEU"] - 6.3) < 0.01
    assert abs(country_sums["UKR"] - 6300042.0) < 0.01


# ---------------------------------------------------------------------------
# Arrow output
# ---------------------------------------------------------------------------

def test_query_returns_arrow_table(tmp_path: Path) -> None:
    """All query methods must return pyarrow.Table for ML pipeline compat."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    assert isinstance(engine.query_all(), pa.Table)
    assert isinstance(engine.query(country_ids=["DEU"]), pa.Table)
    assert isinstance(engine.aggregate(group_by=["domain"], func="count"), pa.Table)


# ---------------------------------------------------------------------------
# Signal key filter
# ---------------------------------------------------------------------------

def test_query_by_signal_keys(tmp_path: Path) -> None:
    """query() with signal_keys must filter to those signals only."""
    _seed_archive(tmp_path)
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.query(signal_keys=["gdp_growth"])
    assert result.num_rows == 1
    assert result.column("signal_key")[0].as_py() == "gdp_growth"


# ---------------------------------------------------------------------------
# Empty archive
# ---------------------------------------------------------------------------

def test_query_empty_archive(tmp_path: Path) -> None:
    """query_all() on empty archive must return 0-row Arrow table."""
    engine = ArchiveQueryEngine(archive_root=tmp_path)
    result = engine.query_all()
    assert isinstance(result, pa.Table)
    assert result.num_rows == 0
