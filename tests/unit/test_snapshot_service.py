from siasa.runs.run_state import RunState, SourceExecutionResult
from siasa.snapshots.service import create_snapshot
from siasa.traceability.lineage import build_lineage_record


def test_snapshot_service_creates_versioned_snapshot_for_partial_success_run() -> None:
    run_state = RunState.start("RUN-001")
    run_state.record_source_result(SourceExecutionResult(source_id="SRC-A", status="success"))
    run_state.record_source_result(SourceExecutionResult(source_id="SRC-B", status="failed"))

    snapshot = create_snapshot(
        run_state=run_state,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B", "D"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        analytical_outputs={"country_status": {"UKR": "S3"}},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    assert snapshot.snapshot_id == "SNAP-RUN-001-v1"
    assert snapshot.status == "partial_success"
    assert snapshot.source_state == {"SRC-A": "success", "SRC-B": "failed"}


def test_lineage_record_links_source_to_snapshot_and_report_with_stable_ids() -> None:
    lineage = build_lineage_record(
        source_id="SRC-A",
        raw_record_id="RAW-001",
        normalized_id="NORM-001",
        feature_id="A_news_volume",
        domain_status_id="DST-UKR-A-2026-05-11",
        multi_domain_status_id="MST-UKR-2026-05-11",
        snapshot_id="SNAP-RUN-001-v1",
        report_id="REP-DAILY-001",
    )

    assert lineage.source_id == "SRC-A"
    assert lineage.feature_id == "A_news_volume"
    assert lineage.snapshot_id == "SNAP-RUN-001-v1"
    assert lineage.report_id == "REP-DAILY-001"
