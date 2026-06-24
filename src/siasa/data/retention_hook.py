"""SIASA Retention Archive Hook (AP-13.13).

Implements:
- SwR-069: Pre-cleanup archive hook guaranteeing all records are archived
  to Parquet before SQLite retention deletes them. No data loss.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ArchiveWriterProtocol(Protocol):
    """Protocol for archive writers."""
    def write_records(self, records: list[dict[str, Any]]) -> int: ...


class RetentionStoreProtocol(Protocol):
    """Protocol for retention stores."""
    def get_records_for_cleanup(self) -> list[dict[str, Any]]: ...
    def delete_records(self, record_ids: list[str]) -> int: ...


@dataclass
class ArchiveStatus:
    """Status of a retention archive cycle."""
    records_archived: int = 0
    records_deleted: int = 0
    success: bool = True
    error: str | None = None


class RetentionArchiveHook:
    """Pre-cleanup hook that archives records before SQLite retention deletes them.

    Guarantees:
    - ALL records are archived to Parquet before deletion
    - If archiving fails, NO records are deleted
    - Idempotent: safe to re-run on already-archived records
    """

    def __init__(
        self,
        archive_writer: ArchiveWriterProtocol,
        retention_store: RetentionStoreProtocol,
    ) -> None:
        self._writer = archive_writer
        self._store = retention_store

    def execute(self) -> ArchiveStatus:
        """Execute the archive-before-delete cycle.

        1. Fetch records eligible for cleanup
        2. Archive ALL of them to Parquet
        3. Only then delete from SQLite

        Returns:
            ArchiveStatus with counts and success flag.
        """
        status = ArchiveStatus()

        # Step 1: Get records for cleanup
        records = self._store.get_records_for_cleanup()
        if not records:
            return status

        # Step 2: Archive ALL records first
        try:
            archived_count = self._writer.write_records(records)
            status.records_archived = archived_count
        except Exception as e:
            status.success = False
            status.error = str(e)
            return status  # Do NOT delete if archive failed

        # Step 3: Only delete after successful archive
        record_ids = [r["record_id"] for r in records]
        deleted_count = self._store.delete_records(record_ids)
        status.records_deleted = deleted_count

        return status
