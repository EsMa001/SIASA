from siasa.snapshots.models import Snapshot


def test_snapshot_model_captures_required_reproducibility_fields() -> None:
    snapshot = Snapshot(
        snapshot_id="SNAP-RUN-001-v1",
        run_id="RUN-001",
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B", "D"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        source_state={"SRC-A": "success", "SRC-B": "failed"},
        analytical_outputs={"country_status": {"UKR": "S3"}},
        status="partial_success",
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    assert snapshot.snapshot_id == "SNAP-RUN-001-v1"
    assert snapshot.run_id == "RUN-001"
    assert snapshot.active_domains == ["A", "B", "D"]
    assert snapshot.rule_versions["domain_status"] == "rules-2026-05"
    assert snapshot.source_state["SRC-B"] == "failed"
    assert snapshot.analytical_outputs["country_status"]["UKR"] == "S3"
