"""AP-13 End-to-End Integration Tests.

Tests the complete ML-Training Data Lake pipeline on real Parquet files:

1. NormalizedRecords → ArchiveWriter → Parquet on disk (Hive-partitioned)
2. Parquet → DuckDB ArchiveQueryEngine → Arrow Table
3. Arrow → DailyAligner → aligned daily table
4. Aligned → MultiResolutionBuilder → Fast/Slow/Structural layers
5. Layers → PointInTimeJoiner → feature table without look-ahead bias
6. Features → TrainingSetBuilder → versioned train/val/test splits
7. Splits → SIASATimeSeriesDataset → PyTorch tensors
8. Splits → HFExporter → HuggingFace Dataset

Also validates:
- Hive partitioning layout (source=X/year=Y/month=Z)
- Parquet metadata (compression, schema columns)
- Round-trip data integrity at each stage
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import torch

from siasa.data.archive import ArchiveWriter, ARCHIVE_SCHEMA
from siasa.data.normalized_models import NormalizedRecord
from siasa.data.query import ArchiveQueryEngine
from siasa.features.alignment import DailyAligner
from siasa.features.multi_resolution import MultiResolutionBuilder
from siasa.features.pit_join import PointInTimeJoiner
from siasa.features.training_builder import TrainingSetBuilder
from siasa.ml.datasets import SIASATimeSeriesDataset, siasa_collate_fn
from siasa.ml.hf_export import HFExporter, DatasetCardInfo
from siasa.ml.encoding import DomainOneHotEncoder, QualityFlagOrdinalEncoder
from siasa.data.archive_health import ArchiveHealthMonitor
from siasa.data.archive_manager import ArchiveManager
from siasa.data.retention_hook import RetentionArchiveHook, ArchiveStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_records(
    country: str = "UKR",
    domain: str = "A",
    source: str = "SRC-GDELT-EVENTS",
    signal: str = "conflict_event_count",
    n_days: int = 90,
    base_date: str = "2025-01-01",
    granularity: str = "daily",
) -> list[NormalizedRecord]:
    """Generate n_days of NormalizedRecords for one country/signal."""
    base = datetime.fromisoformat(base_date)
    records = []
    for i in range(n_days):
        day = base + timedelta(days=i)
        ts = day.strftime("%Y-%m-%dT00:00:00Z")
        next_day = (day + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        records.append(NormalizedRecord(
            normalized_id=f"NORM-{country}-{signal}-{i:04d}",
            country_id=country,
            timestamp=ts,
            domain=domain,
            signal_key=signal,
            value=float(10 + i % 20 + (hash(country) % 5)),
            provenance_source_id=source,
            period_start=ts,
            period_end=next_day,
            granularity=granularity,
            quality_context={"mapping_id": "MAP-TEST-v1", "freshness_hours": 1.0},
        ))
    return records


# ---------------------------------------------------------------------------
# 1. Hive Partitioning Layout
# ---------------------------------------------------------------------------

def test_hive_partitioning_creates_source_year_month_structure(tmp_path: Path) -> None:
    """ArchiveWriter must produce source=X/year=Y/month=Z directories."""
    records = _make_records(n_days=45, base_date="2025-02-15")
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records, run_id="RUN-INTEGRATION-TEST")

    parquet_files = list(tmp_path.rglob("*.parquet"))
    assert len(parquet_files) >= 1, "No Parquet files written"

    # Check directory structure contains Hive-style partitioning keys
    all_paths = [str(p.relative_to(tmp_path)) for p in parquet_files]
    assert any("source=" in p for p in all_paths), f"No source= partition: {all_paths}"
    assert any("year=" in p for p in all_paths), f"No year= partition: {all_paths}"
    assert any("month=" in p for p in all_paths), f"No month= partition: {all_paths}"


def test_hive_partitioning_separates_sources(tmp_path: Path) -> None:
    """Different sources must land in different partition directories."""
    records_a = _make_records(source="SRC-A", signal="signal_a", n_days=10)
    records_b = _make_records(source="SRC-B", signal="signal_b", n_days=10)
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records_a, run_id="RUN-INTEGRATION-TEST")
    writer.write(records=records_b, run_id="RUN-INTEGRATION-TEST")

    dirs = [d.name for d in tmp_path.iterdir() if d.is_dir()]
    assert "source=SRC-A" in dirs, f"Missing SRC-A partition: {dirs}"
    assert "source=SRC-B" in dirs, f"Missing SRC-B partition: {dirs}"


# ---------------------------------------------------------------------------
# 2. Parquet Schema & Metadata
# ---------------------------------------------------------------------------

def test_parquet_schema_matches_archive_schema(tmp_path: Path) -> None:
    """Written Parquet files must match ARCHIVE_SCHEMA column names."""
    records = _make_records(n_days=10)
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records, run_id="RUN-INTEGRATION-TEST")

    parquet_files = list(tmp_path.rglob("*.parquet"))
    for pf in parquet_files:
        schema = pq.read_schema(pf)
        expected_cols = set(ARCHIVE_SCHEMA.names)
        actual_cols = set(schema.names)
        # Partition columns may be excluded from file schema
        assert actual_cols.issubset(expected_cols) or expected_cols.issubset(
            actual_cols | {"source_id", "year", "month"}
        ), f"Schema mismatch: expected {expected_cols}, got {actual_cols}"


def test_parquet_file_is_snappy_or_uncompressed(tmp_path: Path) -> None:
    """Parquet files should use snappy or no compression (not gzip/zstd)."""
    records = _make_records(n_days=10)
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records, run_id="RUN-INTEGRATION-TEST")

    parquet_files = list(tmp_path.rglob("*.parquet"))
    for pf in parquet_files:
        meta = pq.read_metadata(pf)
        for rg_idx in range(meta.num_row_groups):
            rg = meta.row_group(rg_idx)
            for col_idx in range(rg.num_columns):
                compression = rg.column(col_idx).compression
                assert compression in ("SNAPPY", "UNCOMPRESSED", "NONE"), (
                    f"Unexpected compression: {compression}"
                )


# ---------------------------------------------------------------------------
# 3. Archive → Query Round-Trip
# ---------------------------------------------------------------------------

def test_archive_query_roundtrip_preserves_record_count(tmp_path: Path) -> None:
    """Write N records, query back, get N records."""
    n = 30
    records = _make_records(n_days=n)
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records, run_id="RUN-INTEGRATION-TEST")

    engine = ArchiveQueryEngine(archive_root=tmp_path)
    table = engine.query_all()
    assert table.num_rows == n, f"Expected {n} rows, got {table.num_rows}"


def test_archive_query_roundtrip_preserves_values(tmp_path: Path) -> None:
    """Written values must survive write→query round-trip."""
    records = _make_records(n_days=5)
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records, run_id="RUN-INTEGRATION-TEST")

    engine = ArchiveQueryEngine(archive_root=tmp_path)
    table = engine.query_all()

    original_values = sorted(r.value for r in records)
    queried_values = sorted(table.column("value").to_pylist())
    assert original_values == queried_values


# ---------------------------------------------------------------------------
# 4. DailyAligner on Real Parquet
# ---------------------------------------------------------------------------

def test_daily_aligner_on_real_parquet(tmp_path: Path) -> None:
    """DailyAligner reads from real Parquet archive on disk."""
    records = _make_records(n_days=60, signal="conflict_event_count")
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records, run_id="RUN-INTEGRATION-TEST")

    aligner = DailyAligner(archive_root=tmp_path)
    result = aligner.align(country_ids=["UKR"], signal_keys=["conflict_event_count"])

    assert result.aligned_table.num_rows > 0
    cols = set(result.aligned_table.column_names)
    assert "date" in cols
    assert "country_id" in cols
    assert "signal_key" in cols
    assert "value" in cols


# ---------------------------------------------------------------------------
# 5. Full Feature Pipeline: Align → MultiRes → PIT → Training
# ---------------------------------------------------------------------------

def test_full_feature_pipeline_from_parquet(tmp_path: Path) -> None:
    """End-to-end: Parquet → Align → MultiRes → PITJoin → TrainingBuilder."""
    # Write 90 days of data for 2 signals
    records = []
    records.extend(_make_records(
        n_days=90, signal="conflict_event_count", source="SRC-GDELT-EVENTS",
    ))
    records.extend(_make_records(
        n_days=90, signal="fx_rate", source="SRC-FRANKFURTER",
        domain="D",
    ))
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records, run_id="RUN-INTEGRATION-TEST")

    # Align
    aligner = DailyAligner(archive_root=tmp_path)
    aligned = aligner.align(
        country_ids=["UKR"],
        signal_keys=["conflict_event_count", "fx_rate"],
    )
    assert aligned.aligned_table.num_rows > 0

    # Multi-resolution
    builder = MultiResolutionBuilder()
    multi_res = builder.build(aligned_table=aligned.aligned_table)
    assert multi_res.fast_layer.num_rows > 0

    # PIT Join
    dates = sorted(set(aligned.aligned_table.column("date").to_pylist()))
    query_dates = dates[30:]  # Use dates from day 30 onwards
    if len(query_dates) > 0:
        joiner = PointInTimeJoiner(staleness_limit_days=10)
        pit_result = joiner.join(
            aligned_table=aligned.aligned_table,
            query_dates=query_dates,
            country_ids=["UKR"],
            signal_keys=["conflict_event_count", "fx_rate"],
        )
        assert pit_result.feature_table.num_rows > 0

        # Training builder
        tsb = TrainingSetBuilder()
        training = tsb.build(feature_table=pit_result.feature_table)
        assert training.train_table.num_rows > 0
        assert training.metadata["version"] is not None


# ---------------------------------------------------------------------------
# 6. Training Splits → PyTorch Dataset
# ---------------------------------------------------------------------------

def test_pytorch_dataset_from_training_splits() -> None:
    """TrainingSetBuilder output feeds directly into SIASATimeSeriesDataset."""
    # Build a synthetic pivoted table (what TrainingSetBuilder produces)
    rows = 60
    table = pa.table({
        "country_id": ["UKR"] * rows,
        "date": [f"2025-{1 + d // 30:02d}-{1 + d % 30:02d}" for d in range(rows)],
        "conflict_event_count": [float(10 + d % 15) for d in range(rows)],
        "fx_rate": [0.9 + d * 0.001 for d in range(rows)],
    })

    ds = SIASATimeSeriesDataset(
        table, window_size=20, prediction_horizon=5,
        features=["conflict_event_count", "fx_rate"],
    )

    assert len(ds) > 0
    x, y = ds[0]
    assert x.shape == (20, 2)
    assert y.shape == (5, 2)
    assert x.dtype == torch.float32

    # Batch collation
    batch = [ds[i] for i in range(min(4, len(ds)))]
    x_b, y_b = siasa_collate_fn(batch)
    assert x_b.shape[0] == len(batch)


# ---------------------------------------------------------------------------
# 7. Training Splits → HuggingFace Export
# ---------------------------------------------------------------------------

def test_hf_export_from_parquet_on_disk(tmp_path: Path) -> None:
    """HFExporter reads real Parquet files from disk."""
    # Write a training parquet
    table = pa.table({
        "country_id": ["UKR", "DEU", "FRA"],
        "date": ["2025-01-01", "2025-01-01", "2025-01-01"],
        "score": [1.0, 2.0, 3.0],
    })
    parquet_path = tmp_path / "train.parquet"
    pq.write_table(table, parquet_path)

    exporter = HFExporter()
    ds = exporter.from_parquet(parquet_path)

    assert len(ds) == 3
    assert ds[0]["country_id"] == "UKR"
    assert set(ds.column_names) == {"country_id", "date", "score"}


def test_hf_export_directory_round_trip(tmp_path: Path) -> None:
    """Full export directory: Parquet splits → HF directory with README."""
    for split in ["train", "val", "test"]:
        table = pa.table({
            "country_id": ["UKR"] * 5,
            "value": [float(i) for i in range(5)],
        })
        pq.write_table(table, tmp_path / f"{split}.parquet")

    card_info = DatasetCardInfo(
        name="siasa-integration-test",
        description="Integration test dataset",
        license="MIT",
        features=["value"],
        num_rows=15,
        version="v1",
    )
    exporter = HFExporter()
    output_dir = tmp_path / "hf_output"
    result = exporter.export_training_set(
        source_dir=tmp_path, output_dir=output_dir, card_info=card_info,
    )

    assert (output_dir / "README.md").exists()
    readme = (output_dir / "README.md").read_text()
    assert "siasa-integration-test" in readme
    assert "MIT" in readme
    assert result["num_splits"] == 3


# ---------------------------------------------------------------------------
# 8. Encoding Utilities Integration
# ---------------------------------------------------------------------------

def test_encoding_utilities_on_real_domain_values() -> None:
    """DomainOneHotEncoder handles all SIASA domains consistently."""
    enc = DomainOneHotEncoder()
    for domain in ["A", "B", "C", "D", "E"]:
        vec = enc.encode(domain)
        assert sum(vec) == 1.0
        assert len(vec) == 5

    qual = QualityFlagOrdinalEncoder()
    assert qual.encode("high") > qual.encode("low")


# ---------------------------------------------------------------------------
# 9. Archive Manager Validates Real Parquet
# ---------------------------------------------------------------------------

def test_archive_manager_stats_on_real_archive(tmp_path: Path) -> None:
    """ArchiveManager.stats reads real Parquet files written by ArchiveWriter."""
    records = _make_records(n_days=20)
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records, run_id="RUN-INTEGRATION-TEST")

    manager = ArchiveManager(archive_dir=tmp_path)
    stats = manager.stats()
    assert stats["total_records"] == 20
    assert stats["file_count"] >= 1
    assert stats["total_size_bytes"] > 0


def test_archive_manager_validates_real_archive_schema(tmp_path: Path) -> None:
    """ArchiveManager.validate checks schema of real ArchiveWriter output."""
    records = _make_records(n_days=10)
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records, run_id="RUN-INTEGRATION-TEST")

    manager = ArchiveManager(
        archive_dir=tmp_path,
        required_columns=["value", "country_id", "signal_key"],
    )
    result = manager.validate()
    assert result["valid"] is True, f"Validation errors: {result['errors']}"


# ---------------------------------------------------------------------------
# 10. Archive Health on Real Data
# ---------------------------------------------------------------------------

def test_archive_health_report_on_real_data(tmp_path: Path) -> None:
    """ArchiveHealthMonitor produces a report from real archive stats."""
    records = _make_records(n_days=30)
    writer = ArchiveWriter(archive_root=tmp_path)
    writer.write(records=records, run_id="RUN-INTEGRATION-TEST")

    manager = ArchiveManager(archive_dir=tmp_path)
    stats = manager.stats()

    monitor = ArchiveHealthMonitor(archive_stats={
        "sources": {"SRC-GDELT-EVENTS": {"record_count": stats["total_records"]}},
        "domains": {"A": {"record_count": stats["total_records"]}},
        "years": {2025: {"record_count": stats["total_records"]}},
        "total_records": stats["total_records"],
        "total_size_bytes": stats["total_size_bytes"],
        "last_archive_utc": "2025-01-30T00:00:00Z",
    })
    report = monitor.build_report()
    assert report.is_healthy is True
    assert report.total_records == 30
