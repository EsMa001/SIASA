from __future__ import annotations

from dataclasses import dataclass

from siasa.adapters.base import FetchResult, SourceAdapter
from siasa.adapters.fetch_metadata import FetchMetadataRecord


@dataclass
class DummyAdapter(SourceAdapter):
    source_id: str = "SRC-DUMMY"
    domain: str = "A"

    def fetch(self) -> FetchResult:
        return FetchResult(records=[{"value": 1}], diagnostics="ok")


def test_source_adapter_reports_identity() -> None:
    adapter = DummyAdapter()

    assert adapter.source_id == "SRC-DUMMY"
    assert adapter.domain == "A"


def test_source_adapter_fetch_returns_fetch_result() -> None:
    adapter = DummyAdapter()
    result = adapter.fetch()

    assert isinstance(result, FetchResult)
    assert result.records == [{"value": 1}]
    assert result.diagnostics == "ok"
    assert result.is_success is True


def test_fetch_metadata_record_captures_execution_status() -> None:
    record = FetchMetadataRecord(
        source_id="SRC-DUMMY",
        fetch_status="success",
        fetched_at="2026-05-11T14:00:00Z",
        diagnostics="ok",
        record_count=1,
    )

    assert record.source_id == "SRC-DUMMY"
    assert record.fetch_status == "success"
    assert record.record_count == 1


def test_fetch_metadata_record_rejects_unknown_status() -> None:
    try:
        FetchMetadataRecord(
            source_id="SRC-DUMMY",
            fetch_status="unknown",
            fetched_at="2026-05-11T14:00:00Z",
        )
    except ValueError as exc:
        assert "fetch_status" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid fetch_status")
