"""SIASA historical data layer.

Extends the run-history SQLite store with per-source raw-record snapshots
and configurable retention horizons per domain/source, enabling downstream
trend analysis and backtesting against real historical data.

Tables added:
- ``historical_records``: timestamped raw/normalized records per source per run
- ``retention_config``: per-domain or per-source retention horizon in hours

Key APIs:
- ``persist_historical_records(db_path, run_id, records)``
- ``load_historical_records(db_path, source_id, ..., since_hours)``
- ``set_retention_horizon(db_path, domain_or_source, hours)``
- ``get_retention_horizon(db_path, domain_or_source)``
- ``prune_expired_records(db_path)``
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from siasa.data.storage import _connect, initialize_run_history_schema


_DEFAULT_RETENTION_HOURS = 168.0  # 7 days


def _initialize_historical_schema(db_path: Path) -> None:
    """Ensure historical tables exist (idempotent)."""
    initialize_run_history_schema(db_path)
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                country_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                record_type TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hr_source ON historical_records(source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hr_country_domain ON historical_records(country_id, domain)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hr_recorded_at ON historical_records(recorded_at)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS retention_config (
                key TEXT PRIMARY KEY,
                retention_hours REAL NOT NULL
            )
            """
        )


@dataclass(frozen=True)
class HistoricalRecord:
    id: int
    run_id: str
    source_id: str
    country_id: str
    domain: str
    record_type: str
    recorded_at: str
    payload: dict


def persist_historical_records(
    db_path: Path,
    *,
    run_id: str,
    records: list[dict[str, Any]],
) -> int:
    """Persist historical raw/normalized records for a run.

    Each entry in ``records`` should have keys:
    ``source_id``, ``country_id``, ``domain``, ``record_type``, ``payload``.
    Optional ``recorded_at`` (ISO timestamp); defaults to now UTC.

    Returns the number of records inserted.
    """
    _initialize_historical_schema(db_path)
    now_utc = datetime.now(timezone.utc).isoformat()

    rows = []
    for rec in records:
        rows.append((
            run_id,
            str(rec.get("source_id", "")),
            str(rec.get("country_id", "")),
            str(rec.get("domain", "")),
            str(rec.get("record_type", "raw")),
            str(rec.get("recorded_at", now_utc)),
            json.dumps(rec.get("payload", {}), sort_keys=True),
        ))

    with _connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO historical_records(run_id, source_id, country_id, domain, record_type, recorded_at, payload_json)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def load_historical_records(
    db_path: Path,
    *,
    source_id: Optional[str] = None,
    country_id: Optional[str] = None,
    domain: Optional[str] = None,
    since_hours: Optional[float] = None,
    limit: int = 200,
) -> list[HistoricalRecord]:
    """Query historical records with optional filters."""
    _initialize_historical_schema(db_path)

    conditions = []
    params: list[Any] = []

    if source_id is not None:
        conditions.append("source_id = ?")
        params.append(source_id)
    if country_id is not None:
        conditions.append("country_id = ?")
        params.append(country_id)
    if domain is not None:
        conditions.append("domain = ?")
        params.append(domain)
    if since_hours is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - since_hours * 3600
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
        conditions.append("recorded_at >= ?")
        params.append(cutoff_iso)

    where = " AND ".join(conditions) if conditions else "1=1"
    params.append(limit)

    with _connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT id, run_id, source_id, country_id, domain, record_type, recorded_at, payload_json
            FROM historical_records
            WHERE {where}
            ORDER BY recorded_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

    return [
        HistoricalRecord(
            id=int(row["id"]),
            run_id=str(row["run_id"]),
            source_id=str(row["source_id"]),
            country_id=str(row["country_id"]),
            domain=str(row["domain"]),
            record_type=str(row["record_type"]),
            recorded_at=str(row["recorded_at"]),
            payload=json.loads(str(row["payload_json"])),
        )
        for row in rows
    ]


def set_retention_horizon(db_path: Path, *, key: str, hours: float) -> None:
    """Set retention horizon for a domain or source key (e.g. 'A', 'WB-INDICATORS')."""
    _initialize_historical_schema(db_path)
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO retention_config(key, retention_hours) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET retention_hours=excluded.retention_hours
            """,
            (key, hours),
        )


def get_retention_horizon(db_path: Path, *, key: str) -> float:
    """Get retention horizon for a key, falling back to default."""
    _initialize_historical_schema(db_path)
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT retention_hours FROM retention_config WHERE key = ?", (key,)
        ).fetchone()
    if row:
        return float(row["retention_hours"])
    return _DEFAULT_RETENTION_HOURS


def prune_expired_records(db_path: Path) -> int:
    """Delete historical records older than their configured retention horizon.

    Uses per-domain retention if configured, otherwise the global default.
    Returns the number of records deleted.
    """
    _initialize_historical_schema(db_path)

    with _connect(db_path) as conn:
        # Load all configured retention horizons
        config_rows = conn.execute("SELECT key, retention_hours FROM retention_config").fetchall()
        horizons = {str(row["key"]): float(row["retention_hours"]) for row in config_rows}

        now = datetime.now(timezone.utc)
        total_deleted = 0

        # Prune by domain-specific horizons
        for key, hours in horizons.items():
            cutoff = datetime.fromtimestamp(now.timestamp() - hours * 3600, tz=timezone.utc).isoformat()
            cursor = conn.execute(
                "DELETE FROM historical_records WHERE domain = ? AND recorded_at < ?",
                (key, cutoff),
            )
            total_deleted += cursor.rowcount
            # Also try as source_id
            cursor = conn.execute(
                "DELETE FROM historical_records WHERE source_id = ? AND recorded_at < ?",
                (key, cutoff),
            )
            total_deleted += cursor.rowcount

        # Prune remaining records by default horizon
        default_cutoff = datetime.fromtimestamp(
            now.timestamp() - _DEFAULT_RETENTION_HOURS * 3600, tz=timezone.utc
        ).isoformat()
        cursor = conn.execute(
            "DELETE FROM historical_records WHERE recorded_at < ?",
            (default_cutoff,),
        )
        total_deleted += cursor.rowcount

    return total_deleted
