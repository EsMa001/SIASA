from siasa.runs.reprocessing import ReprocessingRequest, build_reprocessing_comparison


def test_reprocessing_workflow_captures_versioned_rules_mappings_and_configs() -> None:
    request = ReprocessingRequest(
        run_id="RUN-001",
        requested_by="Admin/Developer",
        rule_version="rules-2026-05",
        mapping_version="mapping-v2",
        config_version="config-v3",
        reason="baseline retune",
    )

    assert request.run_id == "RUN-001"
    assert request.rule_version == "rules-2026-05"
    assert request.mapping_version == "mapping-v2"
    assert request.config_version == "config-v3"


def test_reprocessing_comparison_preserves_prior_outputs_and_enables_version_comparison() -> None:
    comparison = build_reprocessing_comparison(
        prior_snapshot_id="SNAP-RUN-001-v1",
        new_snapshot_id="SNAP-RUN-001-v2",
        prior_versions={"rule_version": "rules-2026-04", "mapping_version": "mapping-v1", "config_version": "config-v2"},
        new_versions={"rule_version": "rules-2026-05", "mapping_version": "mapping-v2", "config_version": "config-v3"},
    )

    assert comparison["prior_snapshot_id"] == "SNAP-RUN-001-v1"
    assert comparison["new_snapshot_id"] == "SNAP-RUN-001-v2"
    assert comparison["overwrote_prior_snapshot"] is False
    assert comparison["changed_versions"] == ["config_version", "mapping_version", "rule_version"]
