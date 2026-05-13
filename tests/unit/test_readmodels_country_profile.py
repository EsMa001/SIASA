from siasa.readmodels.country_profile import build_country_profile_read_model
from siasa.readmodels.source_coverage import build_source_coverage_read_model
from siasa.readmodels.world_map import build_world_map_read_model


def test_world_map_read_model_exposes_country_status_active_domains_baseline_and_drill_down() -> None:
    read_model = build_world_map_read_model(
        country_statuses={"UKR": "S3", "POL": "S1"},
        active_domains=["A", "B", "D"],
        baseline_mode="Combined 30/90/365",
    )

    assert read_model["countries"][0]["country_id"] == "POL"
    assert read_model["countries"][1]["country_id"] == "UKR"
    assert read_model["countries"][1]["status"] == "S3"
    assert read_model["baseline_mode"] == "Combined 30/90/365"
    assert read_model["countries"][1]["drill_down_target"] == "/countries/UKR"


def test_country_profile_read_model_exposes_status_domain_states_trends_drivers_and_events() -> None:
    read_model = build_country_profile_read_model(
        country_id="UKR",
        multi_domain_status="S3",
        domain_states={"A": "D3", "B": "D2", "D": "D1"},
        trends={"yearly": ["2025-11", "2025-12", "2026-01"]},
        drivers=["A_news_volume"],
        linked_events=["EVT-001"],
        explanation_summary="Escalation is primarily driven by Domain A with partial corroboration from Domain B.",
    )

    assert read_model["country_id"] == "UKR"
    assert read_model["multi_domain_status"] == "S3"
    assert read_model["domain_states"]["A"] == "D3"
    assert read_model["drivers"] == ["A_news_volume"]
    assert read_model["linked_events"] == ["EVT-001"]
    assert read_model["explanation_summary"] == "Escalation is primarily driven by Domain A with partial corroboration from Domain B."


def test_source_coverage_read_model_exposes_status_horizon_freshness_confidence_and_failed_sources() -> None:
    read_model = build_source_coverage_read_model(
        sources=[
            {"source_id": "SRC-A", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.9},
            {"source_id": "SRC-B", "status": "failed", "history_horizon": "1y", "freshness_hours": 48, "confidence": 0.4},
            {"source_id": "ACLED", "status": "prepared_adapter", "history_horizon": "n/a", "freshness_hours": None, "confidence": None},
        ]
    )

    assert read_model["failed_sources"] == ["SRC-B"]
    assert read_model["sources"][1]["history_horizon"] == "1y"
    assert read_model["sources"][1]["freshness_hours"] == 48
    assert read_model["sources"][1]["confidence"] == 0.4
    assert read_model["degraded_sources"] == ["SRC-B", "ACLED"]
    assert read_model["source_status_summary"] == {"success": 1, "failed": 1, "prepared_adapter": 1}
