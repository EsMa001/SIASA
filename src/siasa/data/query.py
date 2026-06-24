"""SIASA Archive Query Engine — DuckDB over Parquet (AP-13.4).

Implements:
- SwR-060: Analytical query engine over Hive-partitioned Parquet archive
  - Time-window queries
  - Country/domain/signal filtering
  - Aggregations (count, mean, sum, min, max)
  - Arrow table output for ML pipelines
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import duckdb
import pyarrow as pa


@dataclass
class ArchiveQueryEngine:
    """DuckDB-based analytical query engine over the Parquet archive.

    Reads Hive-partitioned Parquet files via DuckDB for fast analytical queries.
    All results are returned as pyarrow.Table for ML pipeline compatibility.
    """

    archive_root: Path

    def _has_data(self) -> bool:
        """Check if there are any parquet files in the archive."""
        return any(self.archive_root.rglob("*.parquet"))

    def _base_scan(self) -> str:
        """DuckDB scan expression for the Hive-partitioned archive."""
        return f"read_parquet('{self.archive_root}/**/*.parquet', hive_partitioning=false)"

    def _build_where_clause(
        self,
        *,
        country_ids: Optional[list[str]] = None,
        domains: Optional[list[str]] = None,
        signal_keys: Optional[list[str]] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> tuple[str, list]:
        """Build SQL WHERE clause and parameters from filter arguments."""
        conditions: list[str] = []
        params: list = []

        if country_ids:
            placeholders = ", ".join(["?" for _ in country_ids])
            conditions.append(f"country_id IN ({placeholders})")
            params.extend(country_ids)

        if domains:
            placeholders = ", ".join(["?" for _ in domains])
            conditions.append(f"domain IN ({placeholders})")
            params.extend(domains)

        if signal_keys:
            placeholders = ", ".join(["?" for _ in signal_keys])
            conditions.append(f"signal_key IN ({placeholders})")
            params.extend(signal_keys)

        if time_from:
            conditions.append("timestamp_utc >= ?")
            params.append(time_from)

        if time_to:
            conditions.append("timestamp_utc <= ?")
            params.append(time_to)

        where = ""
        if conditions:
            where = " WHERE " + " AND ".join(conditions)

        return where, params

    def query_all(self) -> pa.Table:
        """Return all records in the archive as an Arrow table."""
        if not self._has_data():
            return pa.table({
                "record_id": pa.array([], type=pa.string()),
                "source_id": pa.array([], type=pa.string()),
                "country_id": pa.array([], type=pa.string()),
                "domain": pa.array([], type=pa.string()),
                "signal_key": pa.array([], type=pa.string()),
                "value": pa.array([], type=pa.float64()),
                "timestamp_utc": pa.array([], type=pa.string()),
                "ingestion_utc": pa.array([], type=pa.string()),
                "run_id": pa.array([], type=pa.string()),
                "mapping_id": pa.array([], type=pa.string()),
                "freshness_hours": pa.array([], type=pa.float64()),
                "quality_flag": pa.array([], type=pa.string()),
                "period_start": pa.array([], type=pa.string()),
                "period_end": pa.array([], type=pa.string()),
                "granularity": pa.array([], type=pa.string()),
            })
        con = duckdb.connect(":memory:")
        sql = f"SELECT * FROM {self._base_scan()}"
        return con.execute(sql).to_arrow_table()

    def query(
        self,
        *,
        country_ids: Optional[list[str]] = None,
        domains: Optional[list[str]] = None,
        signal_keys: Optional[list[str]] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> pa.Table:
        """Query the archive with optional filters. Returns Arrow table."""
        if not self._has_data():
            return self.query_all()

        where, params = self._build_where_clause(
            country_ids=country_ids,
            domains=domains,
            signal_keys=signal_keys,
            time_from=time_from,
            time_to=time_to,
        )

        con = duckdb.connect(":memory:")
        sql = f"SELECT * FROM {self._base_scan()}{where}"
        return con.execute(sql, params).to_arrow_table()

    def aggregate(
        self,
        *,
        group_by: list[str],
        func: str,
        country_ids: Optional[list[str]] = None,
        domains: Optional[list[str]] = None,
        signal_keys: Optional[list[str]] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> pa.Table:
        """Aggregate values with grouping. Returns Arrow table.

        Args:
            group_by: Column names to group by (e.g., ["domain"], ["country_id", "domain"])
            func: Aggregation function — "count", "mean", "sum", "min", "max"
            country_ids/domains/signal_keys/time_from/time_to: Optional filters
        """
        if not self._has_data():
            cols = {col: pa.array([], type=pa.string()) for col in group_by}
            if func == "count":
                cols["count"] = pa.array([], type=pa.int64())
            else:
                cols[f"{func}_value"] = pa.array([], type=pa.float64())
            return pa.table(cols)

        where, params = self._build_where_clause(
            country_ids=country_ids,
            domains=domains,
            signal_keys=signal_keys,
            time_from=time_from,
            time_to=time_to,
        )

        group_cols = ", ".join(group_by)

        if func == "count":
            agg_expr = "COUNT(*) AS count"
        elif func == "mean":
            agg_expr = "AVG(value) AS mean_value"
        elif func == "sum":
            agg_expr = "SUM(value) AS sum_value"
        elif func == "min":
            agg_expr = "MIN(value) AS min_value"
        elif func == "max":
            agg_expr = "MAX(value) AS max_value"
        else:
            raise ValueError(f"Unsupported aggregation function: {func}")

        con = duckdb.connect(":memory:")
        sql = f"SELECT {group_cols}, {agg_expr} FROM {self._base_scan()}{where} GROUP BY {group_cols} ORDER BY {group_cols}"
        return con.execute(sql, params).to_arrow_table()
