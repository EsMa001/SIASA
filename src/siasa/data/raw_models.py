from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_ALLOWED_STORAGE_MODES = {"payload", "reference"}


@dataclass(frozen=True)
class RawRecord:
    raw_record_id: str
    source_id: str
    fetched_at: str
    storage_mode: str
    raw_payload: dict[str, Any] | None = None
    raw_reference: str | None = None

    def __post_init__(self) -> None:
        if self.storage_mode not in _ALLOWED_STORAGE_MODES:
            raise ValueError("storage_mode must be one of payload, reference")
        if self.storage_mode == "payload" and self.raw_payload is None:
            raise ValueError("raw_payload is required for payload storage mode")
        if self.storage_mode == "reference" and not self.raw_reference:
            raise ValueError("raw_reference is required for reference storage mode")
