"""Tests for HuggingFace Datasets Export (AP-13.11 / SwR-067).

Verifies:
- Export of Parquet training files to HuggingFace Dataset
- Dataset card generation with schema, description, license
- Schema preservation after round-trip
- Feature column consistency
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

pytest.importorskip("datasets")  # AP-13 HuggingFace export is an optional ml extra; skip cleanly when absent

from siasa.ml.hf_export import HFExporter, DatasetCardInfo


def _make_training_parquet(tmp_dir: Path) -> Path:
    """Create a sample training parquet file."""
    table = pa.table({
        "country_id": ["UKR", "UKR", "DEU", "DEU"],
        "date": ["2025-01-01", "2025-01-02", "2025-01-01", "2025-01-02"],
        "conflict_event_count": [10.0, 12.0, 1.0, 2.0],
        "fx_rate": [0.95, 0.96, 1.0, 1.01],
        "gdp_growth": [2.1, 2.1, 1.5, 1.5],
    })
    path = tmp_dir / "train.parquet"
    pq.write_table(table, path)
    return path


# --- TC-SwR-067-001 ---

def test_export_creates_hf_dataset(tmp_path: Path) -> None:
    parquet_path = _make_training_parquet(tmp_path)
    exporter = HFExporter()
    ds = exporter.from_parquet(parquet_path)
    assert len(ds) == 4
    assert "conflict_event_count" in ds.column_names


def test_export_preserves_schema(tmp_path: Path) -> None:
    parquet_path = _make_training_parquet(tmp_path)
    exporter = HFExporter()
    ds = exporter.from_parquet(parquet_path)
    assert set(ds.column_names) == {"country_id", "date", "conflict_event_count", "fx_rate", "gdp_growth"}


def test_export_with_feature_filter(tmp_path: Path) -> None:
    parquet_path = _make_training_parquet(tmp_path)
    exporter = HFExporter()
    ds = exporter.from_parquet(parquet_path, columns=["country_id", "conflict_event_count"])
    assert set(ds.column_names) == {"country_id", "conflict_event_count"}


def test_dataset_card_generation(tmp_path: Path) -> None:
    card_info = DatasetCardInfo(
        name="siasa-training-v1",
        description="SIASA ML Training Data",
        license="MIT",
        features=["conflict_event_count", "fx_rate", "gdp_growth"],
        num_rows=1000,
        version="v1",
    )
    exporter = HFExporter()
    card_path = exporter.write_dataset_card(tmp_path, card_info)
    assert card_path.exists()
    content = card_path.read_text(encoding="utf-8")
    assert "siasa-training-v1" in content
    assert "conflict_event_count" in content
    assert "MIT" in content


def test_export_directory_creates_complete_structure(tmp_path: Path) -> None:
    """Export a training set directory and verify structure."""
    # Create train/val/test parquet files
    for split in ["train", "val", "test"]:
        table = pa.table({
            "country_id": ["UKR", "DEU"],
            "date": ["2025-01-01", "2025-01-01"],
            "score": [1.0, 2.0],
        })
        pq.write_table(table, tmp_path / f"{split}.parquet")

    card_info = DatasetCardInfo(
        name="test-export",
        description="Test",
        license="MIT",
        features=["score"],
        num_rows=6,
        version="v1",
    )

    exporter = HFExporter()
    output_dir = tmp_path / "hf_output"
    result = exporter.export_training_set(
        source_dir=tmp_path,
        output_dir=output_dir,
        card_info=card_info,
    )

    assert result["splits"] == ["test", "train", "val"]
    assert (output_dir / "README.md").exists()
    assert (output_dir / "train.parquet").exists()
    assert (output_dir / "val.parquet").exists()
    assert (output_dir / "test.parquet").exists()


def test_export_round_trip_data_integrity(tmp_path: Path) -> None:
    """Data values should survive export round-trip."""
    parquet_path = _make_training_parquet(tmp_path)
    exporter = HFExporter()
    ds = exporter.from_parquet(parquet_path)
    assert ds[0]["conflict_event_count"] == 10.0
    assert ds[2]["country_id"] == "DEU"


def test_export_empty_parquet(tmp_path: Path) -> None:
    """Export of empty parquet should produce empty dataset."""
    table = pa.table({
        "country_id": pa.array([], type=pa.string()),
        "score": pa.array([], type=pa.float64()),
    })
    path = tmp_path / "empty.parquet"
    pq.write_table(table, path)
    exporter = HFExporter()
    ds = exporter.from_parquet(path)
    assert len(ds) == 0
