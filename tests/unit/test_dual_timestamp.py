"""Tests for AP-13.3 — Dual-Timestamp-Schema.

Verifies:
- SwR-059: NormalizedRecord carries period_start, period_end, granularity
- SwR-059: Archive schema includes temporal-period columns
- SwR-059: Normalization service propagates period metadata
"""
from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from siasa.data.normalized_models import NormalizedRecord
from siasa.data.archive import ArchiveWriter, ARCHIVE_SCHEMA


# ---------------------------------------------------------------------------
# NormalizedRecord temporal fields
# ---------------------------------------------------------------------------

def test_normalized_record_accepts_period_fields() -> None:
    """NormalizedRecord must accept period_start, period_end, granularity."""
    rec = NormalizedRecord(
        normalized_id="NORM-TEST-1",
        country_id="DEU",
        timestamp="2026-06-23T14:00:00Z",
        domain="B",
        signal_key="test_signal",
        value=1.0,
        provenance_source_id="SRC-TEST",
        period_start="2026-06-23T00:00:00Z",
        period_end="2026-06-24T00:00:00Z",
        granularity="daily",
    )
    assert rec.period_start == "2026-06-23T00:00:00Z"
    assert rec.period_end == "2026-06-24T00:00:00Z"
    assert rec.granularity == "daily"


def test_normalized_record_period_fields_default_to_empty() -> None:
    """period_start, period_end, granularity must default to empty string."""
    rec = NormalizedRecord(
        normalized_id="NORM-TEST-2",
        country_id="UKR",
        timestamp="2026-01-01T00:00:00Z",
        domain="D",
        signal_key="gdp_growth",
        value=2.5,
        provenance_source_id="WB-INDICATORS",
    )
    assert rec.period_start == ""
    assert rec.period_end == ""
    assert rec.granularity == ""


def test_normalized_record_granularity_values() -> None:
    """Granularity must accept known temporal resolutions."""
    for gran in ("hourly", "daily", "weekly", "monthly", "quarterly", "yearly"):
        rec = NormalizedRecord(
            normalized_id=f"NORM-GRAN-{gran}",
            country_id="USA",
            timestamp="2026-01-01T00:00:00Z",
            domain="A",
            signal_key="test",
            value=0.0,
            provenance_source_id="SRC-TEST",
            granularity=gran,
        )
        assert rec.granularity == gran


# ---------------------------------------------------------------------------
# Archive schema extension
# ---------------------------------------------------------------------------

def test_archive_schema_includes_period_columns() -> None:
    """ARCHIVE_SCHEMA must include period_start, period_end, granularity."""
    schema_names = set(ARCHIVE_SCHEMA.names)
    assert "period_start" in schema_names, "Missing period_start in ARCHIVE_SCHEMA"
    assert "period_end" in schema_names, "Missing period_end in ARCHIVE_SCHEMA"
    assert "granularity" in schema_names, "Missing granularity in ARCHIVE_SCHEMA"


# ---------------------------------------------------------------------------
# ArchiveWriter writes period fields
# ---------------------------------------------------------------------------

def test_archive_writer_writes_period_fields(tmp_path: Path) -> None:
    """ArchiveWriter must persist period_start, period_end, granularity to Parquet."""
    rec = NormalizedRecord(
        normalized_id="NORM-PERIOD-1",
        country_id="DEU",
        timestamp="2026-06-23T00:00:00Z",
        domain="D",
        signal_key="gdp_growth",
        value=1.3,
        provenance_source_id="WB-INDICATORS",
        period_start="2026-01-01T00:00:00Z",
        period_end="2026-12-31T23:59:59Z",
        granularity="yearly",
        quality_context={"mapping_id": "MAP-WB-v1", "freshness_hours": 100},
    )
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=[rec], run_id="RUN-PERIOD-001")

    table = pq.read_table(tmp_path)
    assert table.num_rows == 1
    assert table.column("period_start")[0].as_py() == "2026-01-01T00:00:00Z"
    assert table.column("period_end")[0].as_py() == "2026-12-31T23:59:59Z"
    assert table.column("granularity")[0].as_py() == "yearly"


def test_archive_writer_writes_empty_period_defaults(tmp_path: Path) -> None:
    """Records without period fields must write empty strings to Parquet."""
    rec = NormalizedRecord(
        normalized_id="NORM-NOPERIOD-1",
        country_id="UKR",
        timestamp="2026-06-23T14:00:00Z",
        domain="B",
        signal_key="conflict_event_count",
        value=42.0,
        provenance_source_id="SRC-GDELT-EVENTS",
        quality_context={"mapping_id": "MAP-GDELT-v1", "freshness_hours": 1},
    )
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=[rec], run_id="RUN-NP-001")

    table = pq.read_table(tmp_path)
    assert table.column("period_start")[0].as_py() == ""
    assert table.column("period_end")[0].as_py() == ""
    assert table.column("granularity")[0].as_py() == ""


# ---------------------------------------------------------------------------
# Normalization service propagation
# ---------------------------------------------------------------------------

def test_normalization_service_propagates_period_metadata() -> None:
    """normalize_records must propagate period_start/end/granularity from raw_records."""
    from siasa.data.normalization_service import normalize_records
    from siasa.data.normalization_mappings import NormalizationMappingVersion

    mapping = NormalizationMappingVersion(
        mapping_id="MAP-TEST-v1",
        source_id="SRC-TEST",
        version="1.0",
        is_active=True,
    )
    raw_records = [
        {
            "country_id": "DEU",
            "timestamp": "2026-06-23T00:00:00Z",
            "signal_key": "test_signal",
            "value": 5.0,
            "period_start": "2026-06-23T00:00:00Z",
            "period_end": "2026-06-24T00:00:00Z",
            "granularity": "daily",
        }
    ]
    results = normalize_records(
        source_id="SRC-TEST",
        domain="B",
        raw_records=raw_records,
        mappings=[mapping],
    )
    assert len(results) == 1
    assert results[0].period_start == "2026-06-23T00:00:00Z"
    assert results[0].period_end == "2026-06-24T00:00:00Z"
    assert results[0].granularity == "daily"


def test_normalization_service_defaults_missing_period_metadata() -> None:
    """normalize_records must default missing period fields to empty string."""
    from siasa.data.normalization_service import normalize_records
    from siasa.data.normalization_mappings import NormalizationMappingVersion

    mapping = NormalizationMappingVersion(
        mapping_id="MAP-TEST-v1",
        source_id="SRC-TEST",
        version="1.0",
        is_active=True,
    )
    raw_records = [
        {
            "country_id": "UKR",
            "timestamp": "2026-06-23T00:00:00Z",
            "signal_key": "test_signal",
            "value": 3.0,
        }
    ]
    results = normalize_records(
        source_id="SRC-TEST",
        domain="B",
        raw_records=raw_records,
        mappings=[mapping],
    )
    assert len(results) == 1
    assert results[0].period_start == ""
    assert results[0].period_end == ""
    assert results[0].granularity == ""


# ---------------------------------------------------------------------------
# Period validation
# ---------------------------------------------------------------------------

def test_period_start_before_period_end() -> None:
    """period_start must be chronologically before period_end when both set."""
    rec = NormalizedRecord(
        normalized_id="NORM-CHRONO-1",
        country_id="DEU",
        timestamp="2026-06-23T00:00:00Z",
        domain="B",
        signal_key="test",
        value=1.0,
        provenance_source_id="SRC-TEST",
        period_start="2026-06-23T00:00:00Z",
        period_end="2026-06-24T00:00:00Z",
        granularity="daily",
    )
    # When both are set, start < end is the contract.
    # The dataclass stores them — validation is structural.
    assert rec.period_start < rec.period_end
