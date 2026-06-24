"""SIASA Archive Manager CLI (AP-13.15).

Implements:
- SwR-071: CLI entry point for archive management with stats, validate,
  compact, and export-training subcommands.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

import pyarrow as pa
import pyarrow.parquet as pq


class ArchiveManager:
    """CLI-oriented archive management tool.

    Provides subcommand-style operations for Parquet archive management:
    - stats: Record counts, file counts, total size
    - validate: Schema and data integrity checks
    - compact: Merge small Parquet files into larger ones
    - export_training: Generate versioned train/val/test splits
    """

    def __init__(
        self,
        archive_dir: Path | str,
        required_columns: Optional[Sequence[str]] = None,
    ) -> None:
        self._archive_dir = Path(archive_dir)
        self._required_columns = list(required_columns) if required_columns else [
            "record_id", "source_id", "country_id", "signal_key", "value", "timestamp_utc",
        ]

    def _parquet_files(self) -> list[Path]:
        """List all Parquet files in the archive directory."""
        if not self._archive_dir.exists():
            return []
        return sorted(self._archive_dir.glob("**/*.parquet"))

    def stats(self) -> dict[str, Any]:
        """Compute archive statistics.

        Returns:
            Dict with total_records, file_count, total_size_bytes.
        """
        files = self._parquet_files()
        total_records = 0
        total_size = 0

        for f in files:
            meta = pq.read_metadata(f)
            total_records += meta.num_rows
            total_size += f.stat().st_size

        return {
            "total_records": total_records,
            "file_count": len(files),
            "total_size_bytes": total_size,
        }

    def validate(self) -> dict[str, Any]:
        """Validate schema and data integrity of all Parquet files.

        Returns:
            Dict with valid flag and list of errors.
        """
        files = self._parquet_files()
        errors: list[str] = []

        for f in files:
            try:
                schema = pq.read_schema(f)
                column_names = set(schema.names)
                for req_col in self._required_columns:
                    if req_col not in column_names:
                        errors.append(f"{f.name}: missing column '{req_col}'")
            except Exception as e:
                errors.append(f"{f.name}: read error: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "files_checked": len(files),
        }

    def compact(self) -> dict[str, Any]:
        """Merge all Parquet files into a single compacted file.

        Returns:
            Dict with files_before, files_after, records_total.
        """
        files = self._parquet_files()
        if not files:
            return {"files_before": 0, "files_after": 0, "records_total": 0}

        # Read all tables
        tables = []
        for f in files:
            tables.append(pq.read_table(f))

        merged = pa.concat_tables(tables)
        total_records = merged.num_rows

        # Remove old files
        for f in files:
            f.unlink()

        # Write compacted file
        output_path = self._archive_dir / "compacted.parquet"
        pq.write_table(merged, output_path)

        return {
            "files_before": len(files),
            "files_after": 1,
            "records_total": total_records,
        }

    def export_training(
        self,
        output_dir: Path | str,
        version: str = "v1",
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
    ) -> dict[str, Any]:
        """Export archive data as versioned train/val/test splits.

        Args:
            output_dir: Directory for output splits.
            version: Version label.
            train_ratio: Fraction for training set.
            val_ratio: Fraction for validation set.

        Returns:
            Dict with version, split sizes, and total_records.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Read all data
        files = self._parquet_files()
        if not files:
            # Write empty splits
            empty = pa.table({c: pa.array([], type=pa.string()) for c in self._required_columns})
            for split in ["train", "val", "test"]:
                pq.write_table(empty, output_dir / f"{split}.parquet")
            return {"version": version, "total_records": 0, "splits": {"train": 0, "val": 0, "test": 0}}

        tables = [pq.read_table(f) for f in files]
        merged = pa.concat_tables(tables)
        n = merged.num_rows

        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)

        train_table = merged.slice(0, train_end)
        val_table = merged.slice(train_end, val_end - train_end)
        test_table = merged.slice(val_end, n - val_end)

        pq.write_table(train_table, output_dir / "train.parquet")
        pq.write_table(val_table, output_dir / "val.parquet")
        pq.write_table(test_table, output_dir / "test.parquet")

        return {
            "version": version,
            "total_records": n,
            "splits": {
                "train": train_table.num_rows,
                "val": val_table.num_rows,
                "test": test_table.num_rows,
            },
        }
