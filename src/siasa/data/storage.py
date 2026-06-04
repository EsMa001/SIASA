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
    country_set_id: str
    combined_ce_ratio: float | None
    governance_verdict: str
    policy_gate_verdict: str
    release_verdict: str
    readiness_interpretation: str
    known_gap_count: int


@dataclass(frozen=True)
class SourceExecutionEntry:
    run_id: str
    source_id: str
    status: str
    diagnostics: str


@dataclass(frozen=True)
class CountryDomainScoreEntry:
    run_id: str
    country_id: str
    domain: str
    status: str
    score: float
    data_sufficiency: str


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
                failed_sources_json TEXT NOT NULL,
                country_set_id TEXT,
                combined_ce_ratio REAL,
                governance_verdict TEXT,
                policy_gate_verdict TEXT
            )
            """
        )
        existing_run_columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(runs)").fetchall()
        }
        run_column_migrations = {
            "country_set_id": "ALTER TABLE runs ADD COLUMN country_set_id TEXT",
            "combined_ce_ratio": "ALTER TABLE runs ADD COLUMN combined_ce_ratio REAL",
            "governance_verdict": "ALTER TABLE runs ADD COLUMN governance_verdict TEXT",
            "policy_gate_verdict": "ALTER TABLE runs ADD COLUMN policy_gate_verdict TEXT",
            "release_verdict": "ALTER TABLE runs ADD COLUMN release_verdict TEXT",
            "readiness_interpretation": "ALTER TABLE runs ADD COLUMN readiness_interpretation TEXT",
            "known_gap_count": "ALTER TABLE runs ADD COLUMN known_gap_count INTEGER",
        }
        for column_name, statement in run_column_migrations.items():
            if column_name not in existing_run_columns:
                connection.execute(statement)
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS country_domain_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                country_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                status TEXT NOT NULL,
                score REAL NOT NULL,
                data_sufficiency TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_cds_run_id ON country_domain_scores(run_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_cds_country_domain ON country_domain_scores(country_id, domain)")


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
    country_set_id: str | None = None,
    combined_ce_ratio: float | None = None,
    governance_verdict: str | None = None,
    policy_gate_verdict: str | None = None,
    release_verdict: str | None = None,
    readiness_interpretation: str | None = None,
    known_gap_count: int | None = None,
) -> None:
    initialize_run_history_schema(db_path)
    now_utc = datetime.now(timezone.utc).isoformat()
    source_results = source_results or []

    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO runs(
                run_id,
                recorded_at,
                run_status,
                pilot_set,
                artifacts_dir,
                gui_index,
                failed_sources_json,
                country_set_id,
                combined_ce_ratio,
                governance_verdict,
                policy_gate_verdict,
                release_verdict,
                readiness_interpretation,
                known_gap_count
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                recorded_at=excluded.recorded_at,
                run_status=excluded.run_status,
                pilot_set=excluded.pilot_set,
                artifacts_dir=excluded.artifacts_dir,
                gui_index=excluded.gui_index,
                failed_sources_json=excluded.failed_sources_json,
                country_set_id=excluded.country_set_id,
                combined_ce_ratio=excluded.combined_ce_ratio,
                governance_verdict=excluded.governance_verdict,
                policy_gate_verdict=excluded.policy_gate_verdict,
                release_verdict=excluded.release_verdict,
                readiness_interpretation=excluded.readiness_interpretation,
                known_gap_count=excluded.known_gap_count
            """,
            (
                run_id,
                now_utc,
                run_status,
                pilot_set,
                str(artifacts_dir),
                str(gui_index),
                json.dumps(sorted(set(failed_sources))),
                str(country_set_id or "unknown"),
                float(combined_ce_ratio) if combined_ce_ratio is not None else None,
                str(governance_verdict or "unknown"),
                str(policy_gate_verdict or "unknown"),
                str(release_verdict or "unknown"),
                str(readiness_interpretation or "unknown"),
                int(known_gap_count) if known_gap_count is not None else 0,
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
            SELECT
                run_id,
                recorded_at,
                run_status,
                pilot_set,
                artifacts_dir,
                gui_index,
                failed_sources_json,
                country_set_id,
                combined_ce_ratio,
                governance_verdict,
                policy_gate_verdict,
                release_verdict,
                readiness_interpretation,
                known_gap_count
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
            country_set_id=str(row["country_set_id"] or "unknown"),
            combined_ce_ratio=float(row["combined_ce_ratio"]) if row["combined_ce_ratio"] is not None else None,
            governance_verdict=str(row["governance_verdict"] or "unknown"),
            policy_gate_verdict=str(row["policy_gate_verdict"] or "unknown"),
            release_verdict=str(row["release_verdict"] or "unknown"),
            readiness_interpretation=str(row["readiness_interpretation"] or "unknown"),
            known_gap_count=int(row["known_gap_count"] or 0),
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


def persist_country_domain_scores(
    db_path: Path,
    *,
    run_id: str,
    scores: list[dict[str, Any]],
) -> None:
    """Persist per-country per-domain scores for a run.

    Each entry in ``scores`` must have keys:
    ``country_id``, ``domain``, ``status``, ``score``, ``data_sufficiency``.
    """
    initialize_run_history_schema(db_path)
    with _connect(db_path) as connection:
        connection.execute("DELETE FROM country_domain_scores WHERE run_id = ?", (run_id,))
        if scores:
            connection.executemany(
                """
                INSERT INTO country_domain_scores(run_id, country_id, domain, status, score, data_sufficiency)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        str(entry.get("country_id", "")),
                        str(entry.get("domain", "")),
                        str(entry.get("status", "")),
                        float(entry.get("score", 0.0)),
                        str(entry.get("data_sufficiency", "unknown")),
                    )
                    for entry in scores
                ],
            )


def load_country_domain_time_series(
    db_path: Path,
    *,
    country_id: str,
    domain: str,
    limit: int = 50,
) -> list[CountryDomainScoreEntry]:
    """Return score history for one country+domain, most recent first."""
    initialize_run_history_schema(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT cds.run_id, cds.country_id, cds.domain, cds.status, cds.score, cds.data_sufficiency
            FROM country_domain_scores cds
            JOIN runs r ON r.run_id = cds.run_id
            WHERE cds.country_id = ? AND cds.domain = ?
            ORDER BY r.recorded_at DESC
            LIMIT ?
            """,
            (country_id, domain, limit),
        ).fetchall()
    return [
        CountryDomainScoreEntry(
            run_id=str(row["run_id"]),
            country_id=str(row["country_id"]),
            domain=str(row["domain"]),
            status=str(row["status"]),
            score=float(row["score"]),
            data_sufficiency=str(row["data_sufficiency"]),
        )
        for row in rows
    ]


def load_latest_country_scores(
    db_path: Path,
    *,
    country_id: str,
) -> list[CountryDomainScoreEntry]:
    """Return the most recent score per domain for a given country."""
    initialize_run_history_schema(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT cds.run_id, cds.country_id, cds.domain, cds.status, cds.score, cds.data_sufficiency
            FROM country_domain_scores cds
            JOIN runs r ON r.run_id = cds.run_id
            WHERE cds.country_id = ?
              AND r.recorded_at = (
                  SELECT MAX(r2.recorded_at)
                  FROM country_domain_scores cds2
                  JOIN runs r2 ON r2.run_id = cds2.run_id
                  WHERE cds2.country_id = cds.country_id AND cds2.domain = cds.domain
              )
            ORDER BY cds.domain ASC
            """,
            (country_id,),
        ).fetchall()
    return [
        CountryDomainScoreEntry(
            run_id=str(row["run_id"]),
            country_id=str(row["country_id"]),
            domain=str(row["domain"]),
            status=str(row["status"]),
            score=float(row["score"]),
            data_sufficiency=str(row["data_sufficiency"]),
        )
        for row in rows
    ]
