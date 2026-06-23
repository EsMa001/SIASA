"""Tests for SIASA Data Archive — Parquet-based permanent storage (AP-13.1).

Verifies:
- SwR-055: Parquet archive writer produces valid partitioned files
- SwR-056: Archive writer pipeline hook ensures no data loss
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

from siasa.data.normalized_models import NormalizedRecord
from siasa.data.archive import ArchiveWriter, ARCHIVE_SCHEMA


# ---------------------------------------------------------------------------
# SwR-055: Parquet archive writer produces valid partitioned files
# ---------------------------------------------------------------------------

def _make_normalized_records() -> list[NormalizedRecord]:
    """Build a small set of representative normalized records."""
    return [
        NormalizedRecord(
            normalized_id="NORM-SRC-GDELT-EVENTS-1",
            country_id="UKR",
            timestamp="2026-06-23T14:00:00Z",
            domain="B",
            signal_key="conflict_event_count",
            value=42.0,
            provenance_source_id="SRC-GDELT-EVENTS",
            quality_context={"freshness_hours": 1, "quality_flag": "gdelt_events_export",
                             "mapping_id": "MAP-SRC-GDELT-EVENTS-v1", "mapping_version": "1.0"},
        ),
        NormalizedRecord(
            normalized_id="NORM-WB-INDICATORS-1",
            country_id="DEU",
            timestamp="2025-01-01T00:00:00Z",
            domain="D",
            signal_key="gdp_growth",
            value=1.3,
            provenance_source_id="WB-INDICATORS",
            quality_context={"freshness_hours": 4380, "quality_flag": "world_bank_api",
                             "mapping_id": "MAP-WB-INDICATORS-v1", "mapping_version": "1.0"},
        ),
        NormalizedRecord(
            normalized_id="NORM-SRC-CISA-KEV-1",
            country_id="USA",
            timestamp="2026-06-23T00:00:00Z",
            domain="E",
            signal_key="cyber_kev_recent_count",
            value=5.0,
            provenance_source_id="SRC-CISA-KEV",
            quality_context={"freshness_hours": 0, "quality_flag": "cisa_kev_global",
                             "mapping_id": "MAP-SRC-CISA-KEV-v1", "mapping_version": "1.0"},
        ),
    ]


def test_archive_schema_has_required_columns() -> None:
    """ARCHIVE_SCHEMA must contain all fields from SwR-055."""
    required = {
        "record_id", "source_id", "country_id", "domain", "signal_key", "value",
        "timestamp_utc", "ingestion_utc", "run_id", "mapping_id",
        "freshness_hours", "quality_flag",
    }
    schema_names = set(ARCHIVE_SCHEMA.names)
    assert required.issubset(schema_names), f"Missing columns: {required - schema_names}"


def test_archive_writer_creates_partitioned_parquet(tmp_path: Path) -> None:
    """ArchiveWriter must write Hive-partitioned Parquet files (SwR-055)."""
    records = _make_normalized_records()
    writer = ArchiveWriter(archive_root=tmp_path)

    writer.write(records=records, run_id="RUN-TEST-001")

    # Must create source=.../year=.../month=.../ directories
    parquet_files = list(tmp_path.rglob("*.parquet"))
    assert len(parquet_files) >= 1, "No parquet files written"

    # Verify Hive partitioning structure
    all_parts = [str(p.relative_to(tmp_path)) for p in parquet_files]
    assert any("source=" in p for p in all_parts), f"No source= partition: {all_parts}"
    assert any("year=" in p for p in all_parts), f"No year= partition: {all_parts}"
    assert any("month=" in p for p in all_parts), f"No month= partition: {all_parts}"


def test_archive_writer_round_trip_preserves_data(tmp_path: Path) -> None:
    """Written records must be readable and match the input (SwR-055)."""
    records = _make_normalized_records()
    writer = ArchiveWriter(archive_root=tmp_path)

    writer.write(records=records, run_id="RUN-RT-001")

    # Read all parquet files back via pyarrow (no pandas needed)
    table = pq.read_table(tmp_path)

    assert table.num_rows == 3
    source_ids = set(table.column("source_id").to_pylist())
    country_ids = set(table.column("country_id").to_pylist())
    domains = set(table.column("domain").to_pylist())
    assert source_ids == {"SRC-GDELT-EVENTS", "WB-INDICATORS", "SRC-CISA-KEV"}
    assert country_ids == {"UKR", "DEU", "USA"}
    assert domains == {"B", "D", "E"}

    # Check value preservation — find UKR row
    record_ids = table.column("record_id").to_pylist()
    ukr_idx = next(i for i, rid in enumerate(record_ids) if "GDELT-EVENTS" in rid)
    assert table.column("signal_key")[ukr_idx].as_py() == "conflict_event_count"
    assert table.column("value")[ukr_idx].as_py() == 42.0
    assert table.column("run_id")[ukr_idx].as_py() == "RUN-RT-001"


def test_archive_writer_appends_without_overwriting(tmp_path: Path) -> None:
    """Multiple writes must append, not overwrite (SwR-055, StR-143)."""
    records1 = [_make_normalized_records()[0]]  # UKR
    records2 = [_make_normalized_records()[1]]  # DEU
    writer = ArchiveWriter(archive_root=tmp_path)

    writer.write(records=records1, run_id="RUN-A")
    writer.write(records=records2, run_id="RUN-B")

    table = pq.read_table(tmp_path)
    assert table.num_rows == 2
    assert set(table.column("run_id").to_pylist()) == {"RUN-A", "RUN-B"}


def test_archive_writer_sets_ingestion_utc(tmp_path: Path) -> None:
    """Each record must have an ingestion_utc timestamp (SwR-055)."""
    records = _make_normalized_records()[:1]
    writer = ArchiveWriter(archive_root=tmp_path)

    writer.write(records=records, run_id="RUN-ING-001")

    table = pq.read_table(tmp_path)
    ingestion_vals = table.column("ingestion_utc").to_pylist()
    assert all(v is not None and len(v) > 0 for v in ingestion_vals)
    assert "20" in ingestion_vals[0]  # Reasonable year prefix


def test_archive_writer_extracts_mapping_id_from_quality_context(tmp_path: Path) -> None:
    """mapping_id and quality_flag must be extracted from quality_context (SwR-055)."""
    records = _make_normalized_records()[:1]
    writer = ArchiveWriter(archive_root=tmp_path)

    writer.write(records=records, run_id="RUN-MAP-001")

    table = pq.read_table(tmp_path)
    assert table.column("mapping_id")[0].as_py() == "MAP-SRC-GDELT-EVENTS-v1"
    assert table.column("quality_flag")[0].as_py() == "gdelt_events_export"
    assert table.column("freshness_hours")[0].as_py() == 1.0


def test_archive_writer_handles_empty_records(tmp_path: Path) -> None:
    """Writing empty records must be a no-op, not crash (robustness)."""
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=[], run_id="RUN-EMPTY")
    parquet_files = list(tmp_path.rglob("*.parquet"))
    assert len(parquet_files) == 0
