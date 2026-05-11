from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FetchResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: str = ""
    is_success: bool = True


class SourceAdapter(ABC):
    source_id: str
    domain: str

    @abstractmethod
    def fetch(self) -> FetchResult:
        """Fetch data for one source execution."""
