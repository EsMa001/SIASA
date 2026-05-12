from siasa.reporting.manual_reports import (
    generate_coverage_report,
    generate_domain_report,
    generate_event_report,
)


def test_domain_report_generator_emits_governed_markdown_json_and_source_state() -> None:
    report = generate_domain_report(
        country_id="UKR",
        domain="A",
        anomaly_state="D3",
        feature_values=[{"feature_id": "A_article_count", "value": 3.0, "coverage": 1.0}],
        source_state={"SRC-A": "success"},
        uncertainty=["partial_success"],
        linked_event_ids=["EVT-001"],
    )

    assert report.report_id == "REP-DOMAIN-UKR-A"
    assert report.report_type == "domain_report"
    assert report.json_payload["country_id"] == "UKR"
    assert report.json_payload["source_state"] == {"SRC-A": "success"}
    assert report.json_payload["linked_event_ids"] == ["EVT-001"]
    assert "Source state" in report.markdown



def test_event_report_generator_emits_governed_markdown_json_and_source_state() -> None:
    report = generate_event_report(
        country_id="UKR",
        event_id="EVT-001",
        title="Escalation spike",
        summary="Structured event context for analyst review.",
        related_domains=["A", "B"],
        source_state={"SRC-A": "success", "SRC-B": "failed"},
    )

    assert report.report_id == "REP-EVENT-EVT-001"
    assert report.report_type == "event_report"
    assert report.json_payload["event_id"] == "EVT-001"
    assert report.json_payload["related_domains"] == ["A", "B"]
    assert report.json_payload["source_state"] == {"SRC-A": "success", "SRC-B": "failed"}
    assert "Escalation spike" in report.markdown



def test_coverage_report_generator_emits_governed_markdown_json_and_source_state_context() -> None:
    report = generate_coverage_report(
        run_id="RUN-200",
        source_rows=[
            {"source_id": "SRC-A", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.8},
            {"source_id": "SRC-B", "status": "failed", "history_horizon": "2y", "freshness_hours": 24, "confidence": 0.2},
        ],
        failed_sources=["SRC-B"],
        missing_sources=["SRC-C"],
        source_state={"SRC-A": "success", "SRC-B": "failed"},
    )

    assert report.report_id == "REP-COVERAGE-RUN-200"
    assert report.report_type == "coverage_report"
    assert report.json_payload["failed_sources"] == ["SRC-B"]
    assert report.json_payload["missing_sources"] == ["SRC-C"]
    assert report.json_payload["source_state"] == {"SRC-A": "success", "SRC-B": "failed"}
    assert "Coverage report" in report.markdown



def test_coverage_report_generator_blocks_governance_violating_capabilities() -> None:
    try:
        generate_coverage_report(
            run_id="RUN-200",
            source_rows=[],
            failed_sources=[],
            missing_sources=[],
            source_state={},
            capability="operational_recommendation",
        )
    except PermissionError as exc:
        assert "operational_recommendation" in str(exc)
    else:
        raise AssertionError("Expected governance-violating coverage export to be blocked")



def test_manual_report_generators_reject_unsafe_identifiers() -> None:
    for call in [
        lambda: generate_domain_report(
            country_id="UKR",
            domain="../A",
            anomaly_state="D3",
            feature_values=[],
            source_state={},
            uncertainty=[],
            linked_event_ids=[],
        ),
        lambda: generate_event_report(
            country_id="UKR",
            event_id="../EVT-001",
            title="Escalation spike",
            summary="Structured event context for analyst review.",
            related_domains=["B"],
            source_state={},
        ),
        lambda: generate_coverage_report(
            run_id="../RUN-200",
            source_rows=[],
            failed_sources=[],
            missing_sources=[],
            source_state={},
        ),
    ]:
        try:
            call()
        except ValueError as exc:
            assert "identifier" in str(exc) or "run_id" in str(exc) or "event_id" in str(exc) or "domain" in str(exc)
        else:
            raise AssertionError("Expected unsafe identifier to be rejected")
