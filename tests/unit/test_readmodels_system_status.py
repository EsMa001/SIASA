from siasa.readmodels.system_status import build_system_status_read_model


def test_system_status_read_model_exposes_run_status_operational_scope_and_available_outputs() -> None:
    read_model = build_system_status_read_model(
        run_id="RUN-200",
        run_status="partial_success",
        active_domains=["A", "B", "D"],
        countries_total=12,
        countries_with_updates=9,
        failed_sources=["SRC-B", "SRC-D"],
        available_reports=["REP-DAILY-RUN-200", "REP-COUNTRY-UKR"],
        snapshot_id="SNAP-RUN-200-v1",
    )

    assert read_model["run_id"] == "RUN-200"
    assert read_model["run_status"] == "partial_success"
    assert read_model["active_domains"] == ["A", "B", "D"]
    assert read_model["coverage"]["countries_total"] == 12
    assert read_model["coverage"]["countries_with_updates"] == 9
    assert read_model["failed_sources"] == ["SRC-B", "SRC-D"]
    assert read_model["available_reports"] == ["REP-DAILY-RUN-200", "REP-COUNTRY-UKR"]
    assert read_model["snapshot_id"] == "SNAP-RUN-200-v1"
