from siasa.governance.roles import RoleAssignment
from siasa.runs.reprocessing import ReprocessingRequest, execute_controlled_reprocessing



def test_controlled_reprocessing_requires_authorized_role_and_preserves_prior_snapshot() -> None:
    request = ReprocessingRequest(
        run_id="RUN-001",
        requested_by="max@example.org",
        requested_role="Admin/Developer",
        rule_version="rules-2026-05",
        mapping_version="mapping-v2",
        config_version="config-v3",
        reason="baseline retune",
    )

    result = execute_controlled_reprocessing(
        request=request,
        role_assignment=RoleAssignment(role="Admin/Developer", subject_id="max@example.org"),
        prior_snapshot_id="SNAP-RUN-001-v1",
        new_snapshot_id="SNAP-RUN-001-v2",
        prior_versions={"rule_version": "rules-2026-04", "mapping_version": "mapping-v1", "config_version": "config-v2"},
    )

    assert result.status == "completed"
    assert result.requested_by == "max@example.org"
    assert result.comparison["prior_snapshot_id"] == "SNAP-RUN-001-v1"
    assert result.comparison["new_snapshot_id"] == "SNAP-RUN-001-v2"
    assert result.comparison["overwrote_prior_snapshot"] is False
    assert result.comparison["changed_versions"] == ["config_version", "mapping_version", "rule_version"]



def test_controlled_reprocessing_blocks_unauthorized_roles() -> None:
    request = ReprocessingRequest(
        run_id="RUN-001",
        requested_by="analyst@example.org",
        requested_role="Analyst",
        rule_version="rules-2026-05",
        mapping_version="mapping-v2",
        config_version="config-v3",
        reason="baseline retune",
    )

    try:
        execute_controlled_reprocessing(
            request=request,
            role_assignment=RoleAssignment(role="Analyst", subject_id="analyst@example.org"),
            prior_snapshot_id="SNAP-RUN-001-v1",
            new_snapshot_id="SNAP-RUN-001-v2",
            prior_versions={"rule_version": "rules-2026-04", "mapping_version": "mapping-v1", "config_version": "config-v2"},
        )
    except PermissionError as exc:
        assert "reprocess_runs" in str(exc)
    else:
        raise AssertionError("Expected unauthorized reprocessing request to be blocked")



def test_controlled_reprocessing_rejects_mismatched_requester_identity() -> None:
    request = ReprocessingRequest(
        run_id="RUN-001",
        requested_by="max@example.org",
        requested_role="Admin/Developer",
        rule_version="rules-2026-05",
        mapping_version="mapping-v2",
        config_version="config-v3",
        reason="baseline retune",
    )

    try:
        execute_controlled_reprocessing(
            request=request,
            role_assignment=RoleAssignment(role="Admin/Developer", subject_id="other@example.org"),
            prior_snapshot_id="SNAP-RUN-001-v1",
            new_snapshot_id="SNAP-RUN-001-v2",
            prior_versions={"rule_version": "rules-2026-04", "mapping_version": "mapping-v1", "config_version": "config-v2"},
        )
    except PermissionError as exc:
        assert "requested_by" in str(exc)
    else:
        raise AssertionError("Expected mismatched requester identity to be blocked")



def test_controlled_reprocessing_rejects_missing_governed_version_fields() -> None:
    try:
        ReprocessingRequest(
            run_id="RUN-001",
            requested_by="max@example.org",
            requested_role="Admin/Developer",
            rule_version="",
            mapping_version="mapping-v2",
            config_version="config-v3",
            reason="baseline retune",
        )
    except ValueError as exc:
        assert "rule_version" in str(exc)
    else:
        raise AssertionError("Expected missing governed version field to be rejected")



def test_controlled_reprocessing_comparison_detects_missing_prior_governed_keys() -> None:
    request = ReprocessingRequest(
        run_id="RUN-001",
        requested_by="max@example.org",
        requested_role="Admin/Developer",
        rule_version="rules-2026-05",
        mapping_version="mapping-v2",
        config_version="config-v3",
        reason="baseline retune",
    )

    result = execute_controlled_reprocessing(
        request=request,
        role_assignment=RoleAssignment(role="Admin/Developer", subject_id="max@example.org"),
        prior_snapshot_id="SNAP-RUN-001-v1",
        new_snapshot_id="SNAP-RUN-001-v2",
        prior_versions={"rule_version": "rules-2026-04"},
    )

    assert result.comparison["changed_versions"] == ["config_version", "mapping_version", "rule_version"]



def test_controlled_reprocessing_blocks_prior_snapshot_overwrite() -> None:
    request = ReprocessingRequest(
        run_id="RUN-001",
        requested_by="max@example.org",
        requested_role="Admin/Developer",
        rule_version="rules-2026-05",
        mapping_version="mapping-v2",
        config_version="config-v3",
        reason="baseline retune",
    )

    try:
        execute_controlled_reprocessing(
            request=request,
            role_assignment=RoleAssignment(role="Admin/Developer", subject_id="max@example.org"),
            prior_snapshot_id="SNAP-RUN-001-v1",
            new_snapshot_id="SNAP-RUN-001-v1",
            prior_versions={"rule_version": "rules-2026-04", "mapping_version": "mapping-v1", "config_version": "config-v2"},
        )
    except ValueError as exc:
        assert "new_snapshot_id" in str(exc)
    else:
        raise AssertionError("Expected prior snapshot overwrite to be blocked")



def test_controlled_reprocessing_surfaces_system_status_payload_for_downstream_views() -> None:
    request = ReprocessingRequest(
        run_id="RUN-001",
        requested_by="max@example.org",
        requested_role="Admin/Developer",
        rule_version="rules-2026-05",
        mapping_version="mapping-v2",
        config_version="config-v3",
        reason="baseline retune",
    )

    result = execute_controlled_reprocessing(
        request=request,
        role_assignment=RoleAssignment(role="Admin/Developer", subject_id="max@example.org"),
        prior_snapshot_id="SNAP-RUN-001-v1",
        new_snapshot_id="SNAP-RUN-001-v2",
        prior_versions={"rule_version": "rules-2026-04", "mapping_version": "mapping-v1", "config_version": "config-v2"},
    )

    assert result.system_status_patch == {
        "reprocessing_status": "completed",
        "reprocessing_request": {
            "run_id": "RUN-001",
            "requested_by": "max@example.org",
            "requested_role": "Admin/Developer",
            "rule_version": "rules-2026-05",
            "mapping_version": "mapping-v2",
            "config_version": "config-v3",
            "reason": "baseline retune",
        },
        "reprocessing_comparison": {
            "prior_snapshot_id": "SNAP-RUN-001-v1",
            "new_snapshot_id": "SNAP-RUN-001-v2",
            "overwrote_prior_snapshot": False,
            "changed_versions": ["config_version", "mapping_version", "rule_version"],
        },
    }
