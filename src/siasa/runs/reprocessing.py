from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReprocessingRequest:
    run_id: str
    requested_by: str
    rule_version: str
    mapping_version: str
    config_version: str
    reason: str

    def __post_init__(self) -> None:
        if not self.run_id or not self.requested_by:
            raise ValueError("run_id and requested_by are required")


def build_reprocessing_comparison(
    prior_snapshot_id: str,
    new_snapshot_id: str,
    prior_versions: dict[str, str],
    new_versions: dict[str, str],
) -> dict[str, object]:
    changed_versions = sorted(
        key for key, old_value in prior_versions.items() if new_versions.get(key) != old_value
    )
    return {
        "prior_snapshot_id": prior_snapshot_id,
        "new_snapshot_id": new_snapshot_id,
        "overwrote_prior_snapshot": prior_snapshot_id == new_snapshot_id,
        "changed_versions": changed_versions,
    }
