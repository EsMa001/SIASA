from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunHistoryEntry:
    run_id: str
    recorded_at: str
    run_status: str
    pilot_set: str
    artifacts_dir: str
    gui_index: str
    failed_sources: list[str]


@dataclass(frozen=True)
class SourceExecutionEntry:
    run_id: str
    source_id: str
    status: str
    diagnostics: str


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _connect(db_path: Path) -> sqlite3.Connection:
    _ensure_parent(db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_run_history_schema(db_path: Path) -> None:
    with _connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                recorded_at TEXT NOT NULL,
                run_status TEXT NOT NULL,
                pilot_set TEXT NOT NULL,
                artifacts_dir TEXT NOT NULL,
                gui_index TEXT NOT NULL,
                failed_sources_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                status TEXT NOT NULL,
                diagnostics TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_source_results_run_id ON source_results(run_id)")


def persist_operational_latest_run(
    db_path: Path,
    *,
    run_id: str,
    run_status: str,
    pilot_set: str,
    artifacts_dir: Path,
    gui_index: Path,
    failed_sources: list[str],
    source_results: list[dict[str, str]] | None = None,
) -> None:
    initialize_run_history_schema(db_path)
    now_utc = datetime.now(timezone.utc).isoformat()
    source_results = source_results or []

    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO runs(run_id, recorded_at, run_status, pilot_set, artifacts_dir, gui_index, failed_sources_json)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                recorded_at=excluded.recorded_at,
                run_status=excluded.run_status,
                pilot_set=excluded.pilot_set,
                artifacts_dir=excluded.artifacts_dir,
                gui_index=excluded.gui_index,
                failed_sources_json=excluded.failed_sources_json
            """,
            (
                run_id,
                now_utc,
                run_status,
                pilot_set,
                str(artifacts_dir),
                str(gui_index),
                json.dumps(sorted(set(failed_sources))),
            ),
        )
        connection.execute("DELETE FROM source_results WHERE run_id = ?", (run_id,))
        if source_results:
            connection.executemany(
                """
                INSERT INTO source_results(run_id, source_id, status, diagnostics)
                VALUES(?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        str(entry.get("source_id", "")),
                        str(entry.get("status", "")),
                        str(entry.get("diagnostics", "")),
                    )
                    for entry in source_results
                ],
            )


def load_recent_runs(db_path: Path, *, limit: int = 20) -> list[RunHistoryEntry]:
    initialize_run_history_schema(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT run_id, recorded_at, run_status, pilot_set, artifacts_dir, gui_index, failed_sources_json
            FROM runs
            ORDER BY recorded_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        RunHistoryEntry(
            run_id=str(row["run_id"]),
            recorded_at=str(row["recorded_at"]),
            run_status=str(row["run_status"]),
            pilot_set=str(row["pilot_set"]),
            artifacts_dir=str(row["artifacts_dir"]),
            gui_index=str(row["gui_index"]),
            failed_sources=list(json.loads(str(row["failed_sources_json"]))),
        )
        for row in rows
    ]


def load_source_results_for_run(db_path: Path, *, run_id: str) -> list[SourceExecutionEntry]:
    initialize_run_history_schema(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT run_id, source_id, status, diagnostics
            FROM source_results
            WHERE run_id = ?
            ORDER BY source_id ASC
            """,
            (run_id,),
        ).fetchall()

    return [
        SourceExecutionEntry(
            run_id=str(row["run_id"]),
            source_id=str(row["source_id"]),
            status=str(row["status"]),
            diagnostics=str(row["diagnostics"]),
        )
        for row in rows
    ]


def source_results_from_run_state(run_state: Any) -> list[dict[str, str]]:
    entries = []
    for result in getattr(run_state, "source_results", []) or []:
        entries.append(
            {
                "source_id": str(getattr(result, "source_id", "")),
                "status": str(getattr(result, "status", "")),
                "diagnostics": str(getattr(result, "diagnostics", "")),
            }
        )
    return entries
