from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_ALLOWED_SNAPSHOT_STATUSES = {"success", "partial_success"}


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    run_id: str
    country_set_id: str
    active_domains: list[str]
    rule_versions: dict[str, str]
    source_state: dict[str, str]
    analytical_outputs: dict[str, Any]
    status: str
    algorithm_version: str
    data_version: str

    def __post_init__(self) -> None:
        if self.status not in _ALLOWED_SNAPSHOT_STATUSES:
            raise ValueError("status must be success or partial_success")
        if not self.snapshot_id or not self.run_id:
            raise ValueError("snapshot_id and run_id are required")
