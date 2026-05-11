from __future__ import annotations

from dataclasses import dataclass

_ALLOWED_FETCH_STATUSES = {"success", "failed", "partial_success"}


@dataclass(frozen=True)
class FetchMetadataRecord:
    source_id: str
    fetch_status: str
    fetched_at: str
    diagnostics: str = ""
    record_count: int = 0

    def __post_init__(self) -> None:
        if self.fetch_status not in _ALLOWED_FETCH_STATUSES:
            raise ValueError("fetch_status must be one of success, failed, partial_success")
        if not self.source_id:
            raise ValueError("source_id is required")
        if not self.fetched_at:
            raise ValueError("fetched_at is required")
