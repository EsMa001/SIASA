from __future__ import annotations

from dataclasses import dataclass

_ROLE_ACTIONS = {
    "Admin/Developer": {"reprocess_runs", "manage_sources", "version_rules", "create_annotation"},
    "Analyst": {"create_annotation", "export_report", "view_analysis"},
    "Viewer/Reader": {"view_analysis"},
}

_REQUIRED_SOURCE_METADATA = {"source_id", "status", "access", "license", "history"}


@dataclass(frozen=True)
class RoleAssignment:
    role: str

    def __post_init__(self) -> None:
        if self.role not in _ROLE_ACTIONS:
            raise ValueError("role is not governed")


def assert_role_can_perform(role_assignment: RoleAssignment, action: str) -> None:
    if action not in _ROLE_ACTIONS[role_assignment.role]:
        raise PermissionError(f"{role_assignment.role} may not perform {action}")


def validate_source_governance_metadata(source_record: dict[str, str]) -> None:
    missing = sorted(field for field in _REQUIRED_SOURCE_METADATA if not source_record.get(field))
    if missing:
        raise ValueError(f"Missing governance metadata: {', '.join(missing)}")
