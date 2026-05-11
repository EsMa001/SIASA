from siasa.governance.export_policy import enforce_export_policy
from siasa.governance.roles import RoleAssignment, assert_role_can_perform, validate_source_governance_metadata


def test_role_model_and_authorization_hooks_cover_admin_and_analyst_boundaries() -> None:
    admin = RoleAssignment(role="Admin/Developer")
    analyst = RoleAssignment(role="Analyst")

    assert_role_can_perform(admin, "reprocess_runs")
    assert_role_can_perform(analyst, "create_annotation")

    try:
        assert_role_can_perform(analyst, "override_generated_status")
    except PermissionError as exc:
        assert "override_generated_status" in str(exc)
    else:
        raise AssertionError("Expected analyst override to be blocked")


def test_source_governance_metadata_checks_require_governed_fields_before_activation() -> None:
    source_record = {
        "source_id": "SRC-A",
        "status": "active",
        "access": "api",
        "license": "cc-by",
        "history": "3y",
    }

    validate_source_governance_metadata(source_record)

    try:
        validate_source_governance_metadata({"source_id": "SRC-B", "status": "active", "access": "api"})
    except ValueError as exc:
        assert "license" in str(exc)
    else:
        raise AssertionError("Expected missing governance metadata to be blocked")


def test_export_policy_and_misuse_guards_block_targeting_and_personal_content_exports() -> None:
    safe_payload = {"report_type": "country_profile", "contains_personal_data": False, "capability": "analysis"}
    enforce_export_policy(safe_payload)

    for payload in [
        {"report_type": "country_profile", "contains_personal_data": True, "capability": "analysis"},
        {"report_type": "country_profile", "contains_personal_data": False, "capability": "targeting"},
        {"report_type": "country_profile", "contains_personal_data": False, "capability": "disinformation_optimization"},
    ]:
        try:
            enforce_export_policy(payload)
        except PermissionError:
            pass
        else:
            raise AssertionError("Expected governed export to be blocked")
