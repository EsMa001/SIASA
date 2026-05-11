from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NormalizedRecord:
    normalized_id: str
    country_id: str
    timestamp: str
    domain: str
    signal_key: str
    value: float
    provenance_source_id: str
    quality_context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.country_id) != 3:
            raise ValueError("country_id must be ISO3-like")
        if not self.provenance_source_id:
            raise ValueError("provenance_source_id is required")
