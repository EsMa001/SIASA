"""Tests for Archive Manager CLI (AP-13.15 / SwR-071).

Verifies:
- --stats subcommand produces archive statistics
- --validate subcommand checks schema and data integrity
- --compact subcommand merges small Parquet files
- --export-training subcommand generates versioned training set
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from siasa.data.archive_manager import ArchiveManager


def _create_test_parquet(path: Path, n_rows: int = 10) -> None:
    """Create a test Parquet file."""
    table = pa.table({
        "record_id": [f"REC-{i:03d}" for i in range(n_rows)],
        "source_id": ["SRC-TEST"] * n_rows,
        "country_id": ["UKR"] * n_rows,
        "signal_key": ["test_signal"] * n_rows,
        "value": [float(i) for i in range(n_rows)],
        "timestamp_utc": [f"2025-01-{i+1:02d}T00:00:00Z" for i in range(n_rows)],
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)


# --- TC-SwR-071-001 ---

def test_stats_returns_record_counts(tmp_path: Path) -> None:
    _create_test_parquet(tmp_path / "archive" / "data.parquet", n_rows=20)
    manager = ArchiveManager(archive_dir=tmp_path / "archive")
    stats = manager.stats()
    assert stats["total_records"] == 20
    assert stats["file_count"] == 1


def test_stats_empty_archive(tmp_path: Path) -> None:
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    manager = ArchiveManager(archive_dir=archive_dir)
    stats = manager.stats()
    assert stats["total_records"] == 0
    assert stats["file_count"] == 0


def test_validate_valid_parquet(tmp_path: Path) -> None:
    _create_test_parquet(tmp_path / "archive" / "data.parquet")
    manager = ArchiveManager(archive_dir=tmp_path / "archive")
    result = manager.validate()
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_detects_missing_column(tmp_path: Path) -> None:
    table = pa.table({"x": [1, 2, 3]})
    path = tmp_path / "archive" / "bad.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)

    manager = ArchiveManager(
        archive_dir=tmp_path / "archive",
        required_columns=["record_id", "source_id"],
    )
    result = manager.validate()
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_compact_merges_small_files(tmp_path: Path) -> None:
    archive_dir = tmp_path / "archive"
    for i in range(3):
        _create_test_parquet(archive_dir / f"part_{i}.parquet", n_rows=5)

    manager = ArchiveManager(archive_dir=archive_dir)
    result = manager.compact()

    assert result["files_before"] == 3
    assert result["files_after"] == 1
    assert result["records_total"] == 15


def test_compact_empty_archive(tmp_path: Path) -> None:
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    manager = ArchiveManager(archive_dir=archive_dir)
    result = manager.compact()
    assert result["files_before"] == 0
    assert result["files_after"] == 0


def test_export_training_creates_split_files(tmp_path: Path) -> None:
    _create_test_parquet(tmp_path / "archive" / "data.parquet", n_rows=30)
    manager = ArchiveManager(archive_dir=tmp_path / "archive")

    output_dir = tmp_path / "training" / "v1"
    result = manager.export_training(
        output_dir=output_dir,
        version="v1",
        train_ratio=0.6,
        val_ratio=0.2,
    )

    assert result["version"] == "v1"
    assert (output_dir / "train.parquet").exists()
    assert (output_dir / "val.parquet").exists()
    assert (output_dir / "test.parquet").exists()
    assert result["total_records"] == 30
