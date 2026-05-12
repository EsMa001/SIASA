from __future__ import annotations

from dataclasses import asdict, dataclass

from siasa.governance.roles import RoleAssignment, assert_role_can_perform


@dataclass(frozen=True)
class ReprocessingRequest:
    run_id: str
    requested_by: str
    requested_role: str
    rule_version: str
    mapping_version: str
    config_version: str
    reason: str

    def __post_init__(self) -> None:
        missing = [
            name
            for name, value in (
                ("run_id", self.run_id),
                ("requested_by", self.requested_by),
                ("requested_role", self.requested_role),
                ("rule_version", self.rule_version),
                ("mapping_version", self.mapping_version),
                ("config_version", self.config_version),
                ("reason", self.reason),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required reprocessing fields: {', '.join(missing)}")


@dataclass(frozen=True)
class ReprocessingResult:
    status: str
    requested_by: str
    comparison: dict[str, object]
    system_status_patch: dict[str, object]


def build_reprocessing_comparison(
    prior_snapshot_id: str,
    new_snapshot_id: str,
    prior_versions: dict[str, str],
    new_versions: dict[str, str],
) -> dict[str, object]:
    governed_keys = sorted(set(prior_versions) | set(new_versions) | {"rule_version", "mapping_version", "config_version"})
    changed_versions = sorted(
        key for key in governed_keys if new_versions.get(key) != prior_versions.get(key)
    )
    return {
        "prior_snapshot_id": prior_snapshot_id,
        "new_snapshot_id": new_snapshot_id,
        "overwrote_prior_snapshot": prior_snapshot_id == new_snapshot_id,
        "changed_versions": changed_versions,
    }



def execute_controlled_reprocessing(
    *,
    request: ReprocessingRequest,
    role_assignment: RoleAssignment,
    prior_snapshot_id: str,
    new_snapshot_id: str,
    prior_versions: dict[str, str],
) -> ReprocessingResult:
    if role_assignment.role != request.requested_role:
        raise PermissionError("requested_role does not match the authorized role assignment")
    if role_assignment.subject_id != request.requested_by:
        raise PermissionError("requested_by does not match the authorized subject identity")
    assert_role_can_perform(role_assignment, "reprocess_runs")
    if prior_snapshot_id == new_snapshot_id:
        raise ValueError("new_snapshot_id must differ from prior_snapshot_id to preserve prior outputs")

    new_versions = {
        "rule_version": request.rule_version,
        "mapping_version": request.mapping_version,
        "config_version": request.config_version,
    }
    comparison = build_reprocessing_comparison(
        prior_snapshot_id=prior_snapshot_id,
        new_snapshot_id=new_snapshot_id,
        prior_versions=prior_versions,
        new_versions=new_versions,
    )
    system_status_patch = {
        "reprocessing_status": "completed",
        "reprocessing_request": asdict(request),
        "reprocessing_comparison": comparison,
    }
    return ReprocessingResult(
        status="completed",
        requested_by=request.requested_by,
        comparison=comparison,
        system_status_patch=system_status_patch,
    )
