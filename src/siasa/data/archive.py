"""SIASA Data Archive — Parquet-based permanent storage (AP-13.1).

Implements:
- SwR-055: Parquet archive writer with Hive partitioning
- SwR-056: Archive pipeline hook (invoked after normalization)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from siasa.data.normalized_models import NormalizedRecord


# --- Archive Parquet schema (SwR-055) ---
ARCHIVE_SCHEMA = pa.schema([
    pa.field("record_id", pa.string()),
    pa.field("source_id", pa.string()),
    pa.field("country_id", pa.string()),
    pa.field("domain", pa.string()),
    pa.field("signal_key", pa.string()),
    pa.field("value", pa.float64()),
    pa.field("timestamp_utc", pa.string()),
    pa.field("ingestion_utc", pa.string()),
    pa.field("run_id", pa.string()),
    pa.field("mapping_id", pa.string()),
    pa.field("freshness_hours", pa.float64()),
    pa.field("quality_flag", pa.string()),
])


def _extract_year_month(timestamp_str: str) -> tuple[str, str]:
    """Extract year and month from an ISO timestamp string."""
    # Handle both "2026-06-23T14:00:00Z" and "2025-01-01T00:00:00Z" formats
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return str(dt.year), f"{dt.month:02d}"
    except (ValueError, AttributeError):
        return "unknown", "00"


@dataclass
class ArchiveWriter:
    """Writes NormalizedRecords to Hive-partitioned Parquet files.

    Layout: archive_root/source={source_id}/year={YYYY}/month={MM}/data.parquet
    """

    archive_root: Path

    def write(
        self,
        *,
        records: list[NormalizedRecord],
        run_id: str,
    ) -> int:
        """Write records to partitioned Parquet. Returns count written."""
        if not records:
            return 0

        ingestion_utc = datetime.now(timezone.utc).isoformat()

        # Group records by (source_id, year, month) for Hive partitioning
        partitions: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for rec in records:
            year, month = _extract_year_month(rec.timestamp)
            key = (rec.provenance_source_id, year, month)
            if key not in partitions:
                partitions[key] = []
            partitions[key].append({
                "record_id": rec.normalized_id,
                "source_id": rec.provenance_source_id,
                "country_id": rec.country_id,
                "domain": rec.domain,
                "signal_key": rec.signal_key,
                "value": rec.value,
                "timestamp_utc": rec.timestamp,
                "ingestion_utc": ingestion_utc,
                "run_id": run_id,
                "mapping_id": rec.quality_context.get("mapping_id", ""),
                "freshness_hours": float(rec.quality_context.get("freshness_hours", 0.0)),
                "quality_flag": rec.quality_context.get("quality_flag", ""),
            })

        total_written = 0
        for (source_id, year, month), rows in partitions.items():
            partition_dir = (
                self.archive_root
                / f"source={source_id}"
                / f"year={year}"
                / f"month={month}"
            )
            partition_dir.mkdir(parents=True, exist_ok=True)

            table = pa.Table.from_pylist(rows, schema=ARCHIVE_SCHEMA)

            # Append to existing file or create new one
            out_path = partition_dir / "data.parquet"
            if out_path.exists():
                existing = pq.read_table(out_path, schema=ARCHIVE_SCHEMA)
                table = pa.concat_tables([existing, table])

            pq.write_table(table, out_path)
            total_written += len(rows)

        return total_written
