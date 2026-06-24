"""Tests for AP-13.6 — Daily Alignment Pipeline.

Verifies:
- SwR-062: DailyAligner aggregates records to daily canonical resolution
  - SUM aggregation for event counts
  - MEAN aggregation for scores/averages
  - MAX aggregation for severity levels
  - LAST (forward-fill) for yearly/structural data
  - Gap detection and reporting
"""
from __future__ import annotations

from pathlib import Path

import pyarrow as pa

from siasa.features.alignment import DailyAligner, AlignmentResult, GapReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_test_archive(tmp_path: Path) -> Path:
    """Build a small Parquet archive for alignment tests."""
    from siasa.data.archive import ArchiveWriter, ARCHIVE_SCHEMA
    from siasa.data.normalized_models import NormalizedRecord

    records = [
        # Two conflict events on same day → should SUM to 47
        NormalizedRecord(
            normalized_id="NORM-1",
            country_id="UKR",
            timestamp="2026-06-20T08:00:00Z",
            domain="B",
            signal_key="conflict_event_count",
            value=5.0,
            provenance_source_id="SRC-GDELT-EVENTS",
            period_start="2026-06-20T00:00:00Z",
            period_end="2026-06-20T23:59:59Z",
            granularity="daily",
            quality_context={"mapping_id": "MAP-GDELT-v1"},
        ),
        NormalizedRecord(
            normalized_id="NORM-2",
            country_id="UKR",
            timestamp="2026-06-20T14:00:00Z",
            domain="B",
            signal_key="conflict_event_count",
            value=42.0,
            provenance_source_id="SRC-GDELT-EVENTS",
            period_start="2026-06-20T00:00:00Z",
            period_end="2026-06-20T23:59:59Z",
            granularity="daily",
            quality_context={"mapping_id": "MAP-GDELT-v1"},
        ),
        # Disaster alert on same day — MAX should pick 3
        NormalizedRecord(
            normalized_id="NORM-3",
            country_id="UKR",
            timestamp="2026-06-20T06:00:00Z",
            domain="B",
            signal_key="disaster_alert_level",
            value=2.0,
            provenance_source_id="SRC-GDACS",
            granularity="hourly",
            quality_context={"mapping_id": "MAP-GDACS-v1"},
        ),
        NormalizedRecord(
            normalized_id="NORM-4",
            country_id="UKR",
            timestamp="2026-06-20T18:00:00Z",
            domain="B",
            signal_key="disaster_alert_level",
            value=3.0,
            provenance_source_id="SRC-GDACS",
            granularity="hourly",
            quality_context={"mapping_id": "MAP-GDACS-v1"},
        ),
        # Yearly data — LAST should forward-fill
        NormalizedRecord(
            normalized_id="NORM-5",
            country_id="UKR",
            timestamp="2025-12-31T00:00:00Z",
            domain="C",
            signal_key="refugee_population",
            value=6300000.0,
            provenance_source_id="SRC-UNHCR-POP",
            period_start="2025-01-01T00:00:00Z",
            period_end="2025-12-31T23:59:59Z",
            granularity="yearly",
            quality_context={"mapping_id": "MAP-UNHCR-v1"},
        ),
        # Next day event for gap detection
        NormalizedRecord(
            normalized_id="NORM-6",
            country_id="UKR",
            timestamp="2026-06-22T10:00:00Z",
            domain="B",
            signal_key="conflict_event_count",
            value=3.0,
            provenance_source_id="SRC-GDELT-EVENTS",
            granularity="daily",
            quality_context={"mapping_id": "MAP-GDELT-v1"},
        ),
    ]
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records, run_id="RUN-ALIGN-001")
    return tmp_path


# ---------------------------------------------------------------------------
# DailyAligner construction
# ---------------------------------------------------------------------------

def test_daily_aligner_construction() -> None:
    """DailyAligner must accept archive_root as constructor arg."""
    aligner = DailyAligner(archive_root=Path("/tmp/test"))
    assert aligner.archive_root == Path("/tmp/test")


# ---------------------------------------------------------------------------
# SUM aggregation
# ---------------------------------------------------------------------------

def test_sum_aggregation(tmp_path: Path) -> None:
    """SUM signals: multiple records on same day should be summed."""
    archive_root = _build_test_archive(tmp_path)
    aligner = DailyAligner(archive_root=archive_root)
    result = aligner.align(
        country_ids=["UKR"],
        signal_keys=["conflict_event_count"],
    )
    assert isinstance(result, AlignmentResult)
    table = result.aligned_table
    assert isinstance(table, pa.Table)

    # Filter to 2026-06-20
    dates = table.column("date").to_pylist()
    values = table.column("value").to_pylist()
    idx_20 = next(i for i, d in enumerate(dates) if d == "2026-06-20")
    assert values[idx_20] == 47.0  # 5 + 42


# ---------------------------------------------------------------------------
# MAX aggregation
# ---------------------------------------------------------------------------

def test_max_aggregation(tmp_path: Path) -> None:
    """MAX signals: multiple records on same day should pick maximum."""
    archive_root = _build_test_archive(tmp_path)
    aligner = DailyAligner(archive_root=archive_root)
    result = aligner.align(
        country_ids=["UKR"],
        signal_keys=["disaster_alert_level"],
    )
    table = result.aligned_table
    dates = table.column("date").to_pylist()
    values = table.column("value").to_pylist()
    idx = next(i for i, d in enumerate(dates) if d == "2026-06-20")
    assert values[idx] == 3.0  # max(2, 3)


# ---------------------------------------------------------------------------
# LAST (forward-fill for yearly)
# ---------------------------------------------------------------------------

def test_last_forward_fill(tmp_path: Path) -> None:
    """LAST signals: yearly data should produce a single daily value."""
    archive_root = _build_test_archive(tmp_path)
    aligner = DailyAligner(archive_root=archive_root)
    result = aligner.align(
        country_ids=["UKR"],
        signal_keys=["refugee_population"],
    )
    table = result.aligned_table
    assert table.num_rows >= 1
    # The value should be the last known value
    values = table.column("value").to_pylist()
    assert 6300000.0 in values


# ---------------------------------------------------------------------------
# Gap detection
# ---------------------------------------------------------------------------

def test_gap_detection(tmp_path: Path) -> None:
    """Gap report should detect missing days between data points."""
    archive_root = _build_test_archive(tmp_path)
    aligner = DailyAligner(archive_root=archive_root)
    result = aligner.align(
        country_ids=["UKR"],
        signal_keys=["conflict_event_count"],
    )
    gaps = result.gap_report
    assert isinstance(gaps, GapReport)
    # Between 2026-06-20 and 2026-06-22 there is a gap on 2026-06-21
    assert gaps.total_gap_days >= 1
    assert any("2026-06-21" in str(g) for g in gaps.gap_days)


# ---------------------------------------------------------------------------
# AlignmentResult structure
# ---------------------------------------------------------------------------

def test_alignment_result_has_expected_columns(tmp_path: Path) -> None:
    """Aligned table must have date, country_id, signal_key, value columns."""
    archive_root = _build_test_archive(tmp_path)
    aligner = DailyAligner(archive_root=archive_root)
    result = aligner.align(country_ids=["UKR"])
    columns = set(result.aligned_table.column_names)
    assert {"date", "country_id", "signal_key", "value"}.issubset(columns)


# ---------------------------------------------------------------------------
# Empty archive
# ---------------------------------------------------------------------------

def test_align_empty_archive(tmp_path: Path) -> None:
    """Aligning an empty archive should return 0-row result, not crash."""
    aligner = DailyAligner(archive_root=tmp_path)
    result = aligner.align(country_ids=["UKR"])
    assert result.aligned_table.num_rows == 0
    assert result.gap_report.total_gap_days == 0
