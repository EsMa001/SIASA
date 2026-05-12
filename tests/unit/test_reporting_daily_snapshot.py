from siasa.snapshots.models import Snapshot
from siasa.reporting.country_report import generate_country_report
from siasa.reporting.daily_snapshot import generate_daily_snapshot_report


def _snapshot() -> Snapshot:
    return Snapshot(
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


def test_daily_snapshot_report_generator_emits_markdown_and_json() -> None:
    report = generate_daily_snapshot_report(_snapshot())

    assert report.report_id == "REP-DAILY-SNAP-RUN-001-v1"
    assert "# Daily Snapshot" in report.markdown
    assert "SNAP-RUN-001-v1" in report.markdown
    assert report.json_payload["snapshot_id"] == "SNAP-RUN-001-v1"
    assert report.json_payload["country_status"] == {"UKR": "S3"}


def test_country_report_generator_includes_status_drivers_counter_indicators_coverage_uncertainty_and_events() -> None:
    report = generate_country_report(
        country_id="UKR",
        multi_domain_status="S3",
        domain_states={"A": "D3", "B": "D2", "D": "D1"},
        drivers=["A_news_volume", "B_event_count"],
        counter_indicators=["D_gdp_growth"],
        coverage=0.75,
        uncertainty=["partial_success", "SRC-B failed"],
        linked_events=["EVT-001", "EVT-002"],
    )

    assert report.report_id == "REP-COUNTRY-UKR"
    assert report.report_type == "country_profile"
    assert report.json_payload["country_id"] == "UKR"
    assert report.json_payload["drivers"] == ["A_news_volume", "B_event_count"]
    assert report.json_payload["linked_events"] == ["EVT-001", "EVT-002"]
    assert "Counter indicators" in report.markdown



def test_country_report_generator_blocks_personal_data_export_payloads() -> None:
    try:
        generate_country_report(
            country_id="UKR",
            multi_domain_status="S3",
            domain_states={"A": "D3", "B": "D2", "D": "D1"},
            drivers=["A_news_volume"],
            counter_indicators=[],
            coverage=0.75,
            uncertainty=[],
            linked_events=["EVT-001"],
            contains_personal_data=True,
        )
    except PermissionError as exc:
        assert "personal data" in str(exc)
    else:
        raise AssertionError("Expected personal-data export to be blocked")



def test_daily_snapshot_report_generator_blocks_targeting_capability_payloads() -> None:
    try:
        generate_daily_snapshot_report(_snapshot(), capability="targeting")
    except PermissionError as exc:
        assert "targeting" in str(exc)
    else:
        raise AssertionError("Expected targeting export to be blocked")



def test_country_report_generator_rejects_unsafe_country_identifier() -> None:
    try:
        generate_country_report(
            country_id="../UKR",
            multi_domain_status="S3",
            domain_states={"A": "D3"},
            drivers=[],
            counter_indicators=[],
            coverage=0.75,
            uncertainty=[],
            linked_events=[],
        )
    except ValueError as exc:
        assert "country_id" in str(exc)
    else:
        raise AssertionError("Expected unsafe country identifier to be rejected")



def test_daily_snapshot_report_generator_rejects_unsafe_snapshot_identifier() -> None:
    unsafe_snapshot = Snapshot(
        snapshot_id="../SNAP-RUN-001-v1",
        run_id="RUN-001",
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A"],
        rule_versions={"domain_status": "rules-2026-05"},
        source_state={"SRC-A": "success"},
        analytical_outputs={"country_status": {"UKR": "S3"}},
        status="success",
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )
    try:
        generate_daily_snapshot_report(unsafe_snapshot)
    except ValueError as exc:
        assert "snapshot_id" in str(exc)
    else:
        raise AssertionError("Expected unsafe snapshot identifier to be rejected")
