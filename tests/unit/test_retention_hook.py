"""Tests for Retention Archive Hook (AP-13.13 / SwR-069).

Verifies:
- Pre-cleanup hook archives all records before SQLite retention deletes them
- No records are lost during the retention cycle
- Hook is idempotent (re-archiving already archived records is safe)
- Hook reports archive status
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from siasa.data.retention_hook import RetentionArchiveHook, ArchiveStatus


def _make_mock_records(n: int = 5) -> list[dict[str, Any]]:
    """Create mock records for testing."""
    return [
        {
            "record_id": f"REC-{i:03d}",
            "source_id": "SRC-TEST",
            "country_id": "UKR",
            "signal_key": "test_signal",
            "value": float(i),
            "timestamp_utc": f"2025-01-{i+1:02d}T00:00:00Z",
        }
        for i in range(n)
    ]


class MockArchiveWriter:
    """Mock archive writer that tracks archived records."""

    def __init__(self) -> None:
        self.archived: list[dict] = []
        self.write_count = 0

    def write_records(self, records: list[dict]) -> int:
        self.archived.extend(records)
        self.write_count += 1
        return len(records)


class MockRetentionStore:
    """Mock SQLite retention store."""

    def __init__(self, records: list[dict]) -> None:
        self._records = list(records)
        self.deleted: list[str] = []

    def get_records_for_cleanup(self) -> list[dict]:
        return list(self._records)

    def delete_records(self, record_ids: list[str]) -> int:
        self.deleted.extend(record_ids)
        self._records = [r for r in self._records if r["record_id"] not in record_ids]
        return len(record_ids)


# --- TC-SwR-069-001 ---

def test_hook_archives_all_records_before_cleanup() -> None:
    records = _make_mock_records(5)
    writer = MockArchiveWriter()
    store = MockRetentionStore(records)

    hook = RetentionArchiveHook(archive_writer=writer, retention_store=store)
    status = hook.execute()

    assert status.records_archived == 5
    assert status.records_deleted == 5
    assert len(writer.archived) == 5
    assert len(store.deleted) == 5


def test_hook_no_data_loss() -> None:
    records = _make_mock_records(10)
    writer = MockArchiveWriter()
    store = MockRetentionStore(records)

    hook = RetentionArchiveHook(archive_writer=writer, retention_store=store)
    hook.execute()

    archived_ids = {r["record_id"] for r in writer.archived}
    deleted_ids = set(store.deleted)
    original_ids = {r["record_id"] for r in records}

    # Every deleted record must have been archived first
    assert deleted_ids.issubset(archived_ids)
    assert original_ids == archived_ids


def test_hook_empty_store() -> None:
    writer = MockArchiveWriter()
    store = MockRetentionStore([])

    hook = RetentionArchiveHook(archive_writer=writer, retention_store=store)
    status = hook.execute()

    assert status.records_archived == 0
    assert status.records_deleted == 0
    assert writer.write_count == 0


def test_hook_idempotent() -> None:
    records = _make_mock_records(3)
    writer = MockArchiveWriter()
    store = MockRetentionStore(records)

    hook = RetentionArchiveHook(archive_writer=writer, retention_store=store)
    status1 = hook.execute()
    # Second execution with empty store
    status2 = hook.execute()

    assert status1.records_archived == 3
    assert status2.records_archived == 0


def test_hook_returns_archive_status() -> None:
    records = _make_mock_records(7)
    writer = MockArchiveWriter()
    store = MockRetentionStore(records)

    hook = RetentionArchiveHook(archive_writer=writer, retention_store=store)
    status = hook.execute()

    assert isinstance(status, ArchiveStatus)
    assert status.records_archived == 7
    assert status.records_deleted == 7
    assert status.success is True


def test_hook_archive_failure_prevents_deletion() -> None:
    """If archiving fails, records must NOT be deleted."""

    class FailingWriter:
        def write_records(self, records):
            raise RuntimeError("Archive write failed")

    records = _make_mock_records(3)
    store = MockRetentionStore(records)
    hook = RetentionArchiveHook(archive_writer=FailingWriter(), retention_store=store)

    status = hook.execute()

    assert status.success is False
    assert len(store.deleted) == 0  # No deletions on failure
    assert status.records_deleted == 0
