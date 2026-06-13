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


def test_world_map_read_model_supports_country_specific_active_domains() -> None:
    read_model = build_world_map_read_model(
        country_statuses={"UKR": "S3", "TWN": "S1"},
        active_domains=["A", "B", "D"],
        baseline_mode="Combined 30/90/365",
        active_domains_by_country={"TWN": ["A", "B"]},
    )

    assert read_model["countries"] == [
        {"country_id": "TWN", "status": "S1", "active_domains": ["A", "B"], "drill_down_target": "/countries/TWN"},
        {"country_id": "UKR", "status": "S3", "active_domains": ["A", "B", "D"], "drill_down_target": "/countries/UKR"},
    ]


def test_country_profile_read_model_exposes_status_domain_states_trends_drivers_events_and_context() -> None:
    read_model = build_country_profile_read_model(
        country_id="UKR",
        multi_domain_status="S3",
        domain_states={"A": "D3", "B": "D2", "D": "D1"},
        trends={"yearly": ["2025-11", "2025-12", "2026-01"]},
        drivers=["A_news_volume"],
        linked_events=["EVT-001"],
        explanation_summary="Escalation is primarily driven by Domain A with partial corroboration from Domain B.",
        country_context={"priority": "P1", "selection_type": "Core Focus", "region": "Europe / Black Sea"},
        source_depth={"source_ids": ["SRC-A", "SRC-B"], "source_count": 2},
        domain_gap_summary={"expected_domains": ["A", "B", "D"], "observed_domains": ["A", "B"], "missing_domains": ["D"]},
        configured_domains=["A", "B", "D"],
    )

    assert read_model["country_id"] == "UKR"
    assert read_model["multi_domain_status"] == "S3"
    assert read_model["domain_states"]["A"] == "D3"
    assert read_model["drivers"] == ["A_news_volume"]
    assert read_model["linked_events"] == ["EVT-001"]
    assert read_model["explanation_summary"] == "Escalation is primarily driven by Domain A with partial corroboration from Domain B."
    assert read_model["country_context"] == {"priority": "P1", "selection_type": "Core Focus", "region": "Europe / Black Sea"}
    assert read_model["source_depth"] == {"source_ids": ["SRC-A", "SRC-B"], "source_count": 2}
    assert read_model["domain_gap_summary"] == {"expected_domains": ["A", "B", "D"], "observed_domains": ["A", "B"], "missing_domains": ["D"]}
    assert read_model["configured_domains"] == ["A", "B", "D"]


def test_source_coverage_read_model_exposes_status_horizon_freshness_confidence_and_failed_sources() -> None:
    read_model = build_source_coverage_read_model(
        sources=[
            {"source_id": "SRC-A", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.9, "record_count": 12, "diagnostics": "fetch_ok"},
            {"source_id": "SRC-B", "status": "failed", "history_horizon": "1y", "freshness_hours": 48, "confidence": 0.4, "record_count": 0, "diagnostics": "timeout"},
            {"source_id": "ACLED", "status": "prepared_adapter", "history_horizon": "n/a", "freshness_hours": None, "confidence": None, "record_count": 0, "diagnostics": "not_enabled"},
        ]
    )

    assert read_model["failed_sources"] == ["SRC-B"]
    assert read_model["sources"][1]["history_horizon"] == "1y"
    assert read_model["sources"][1]["freshness_hours"] == 48
    assert read_model["sources"][1]["confidence"] == 0.4
    assert read_model["sources"][1]["record_count"] == 0
    assert read_model["sources"][1]["diagnostics"] == "timeout"
    assert read_model["degraded_sources"] == ["SRC-B", "ACLED"]
    assert read_model["source_status_summary"] == {"success": 1, "failed": 1, "prepared_adapter": 1}
    assert read_model["source_activation_readiness_summary"] == {
        "total_sources": 0,
        "blocked_source_count": 0,
        "configured_ready_count": 0,
        "status_counts": {},
        "blocked_sources": [],
        "configured_ready_sources": [],
        "blocked_applicable_country_count": 0,
        "blocked_applicable_countries": [],
        "configured_ready_applicable_country_count": 0,
        "configured_ready_applicable_countries": [],
        "closure_status_counts": {},
        "activated_with_live_evidence_count": 0,
        "activated_with_live_evidence_sources": [],
        "external_blocker_count": 0,
        "external_blocker_sources": [],
        "live_fetch_failed_count": 0,
        "live_fetch_failed_sources": [],
        "pending_evidence_count": 0,
        "pending_evidence_sources": [],
        "out_of_scope_count": 0,
        "out_of_scope_sources": [],
        "overall_closure_status": "no_credential_gated_sources_in_scope",
        "operator_next_step": "No credential-gated source activation is relevant for this governed slice.",
    }


def test_source_coverage_read_model_derives_g2_activation_closure_truth_from_runtime_and_credentials() -> None:
    read_model = build_source_coverage_read_model(
        sources=[
            {"source_id": "SRC-UCDP-GED", "status": "success", "history_horizon": "3y", "freshness_hours": 6, "confidence": 0.9, "record_count": 12, "diagnostics": "fetch_ok"},
            {"source_id": "SRC-RELIEFWEB", "status": "prepared_adapter", "history_horizon": "n/a", "freshness_hours": None, "confidence": None, "record_count": 0, "diagnostics": "not_enabled"},
            {"source_id": "SRC-OTHER", "status": "failed", "history_horizon": "1y", "freshness_hours": 48, "confidence": 0.4, "record_count": 0, "diagnostics": "timeout"},
        ],
        source_activation_readiness=[
            {
                "source_id": "SRC-UCDP-GED",
                "domain": "B",
                "credential_name": "UCDP_API_TOKEN",
                "configured": True,
                "activation_status": "configured_ready",
                "blocked_reason": "none",
                "applicable_country_ids": ["UKR", "POL"],
                "requested_country_count": 2,
                "applicable_country_count": 2,
                "provider_requirement": "api_token",
                "activation_next_step": "Run governed live pipeline to collect first credential-backed source evidence.",
            },
            {
                "source_id": "SRC-RELIEFWEB",
                "domain": "C",
                "credential_name": "RELIEFWEB_APPNAME",
                "configured": False,
                "activation_status": "blocked_missing_credentials",
                "blocked_reason": "missing_credential:RELIEFWEB_APPNAME",
                "applicable_country_ids": ["UKR", "POL"],
                "requested_country_count": 2,
                "applicable_country_count": 2,
                "provider_requirement": "pre_approved_appname",
                "activation_next_step": "Obtain an approved ReliefWeb appname, set RELIEFWEB_APPNAME, and rerun the governed live pipeline.",
            },
        ],
    )

    assert read_model["source_activation_readiness"][0]["runtime_source_status"] == "success"
    assert read_model["source_activation_readiness"][0]["activation_evidence"] == "live_source_success"
    assert read_model["source_activation_readiness"][0]["closure_status"] == "activated_with_live_evidence"
    assert read_model["source_activation_readiness"][1]["runtime_source_status"] == "prepared_adapter"
    assert read_model["source_activation_readiness"][1]["activation_evidence"] == "not_attempted_missing_credentials"
    assert read_model["source_activation_readiness"][1]["closure_status"] == "external_blocker_present"
    assert read_model["source_activation_readiness_summary"]["closure_status_counts"] == {
        "activated_with_live_evidence": 1,
        "external_blocker_present": 1,
    }
    assert read_model["source_activation_readiness_summary"]["activated_with_live_evidence_sources"] == ["SRC-UCDP-GED"]
    assert read_model["source_activation_readiness_summary"]["external_blocker_sources"] == ["SRC-RELIEFWEB"]
    assert read_model["source_activation_readiness_summary"]["overall_closure_status"] == "external_blockers_present"
    assert read_model["source_activation_readiness_summary"]["operator_next_step"] == (
        "Resolve credential/registration blockers for: SRC-RELIEFWEB"
    )
