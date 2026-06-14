from siasa.readmodels.readiness import build_readiness_view_model


def _base_inputs(system_status_read_model: dict[str, object]) -> dict[str, object]:
    return {
        "country_profile_read_models": {"UKR": {"country_id": "UKR"}},
        "domain_detail_read_models": {("UKR", "A"): {"country_id": "UKR", "domain": "A"}},
        "report_catalog": {"REP-1": {"id": "REP-1"}},
        "system_status_read_model": system_status_read_model,
        "source_coverage_read_model": {"missing_sources": []},
        "validation_view_model": {"ok": True},
        "traceability_view_model": {"ok": True},
        "annotations_view_model": {"ok": True},
        "repo_closure_view_model": {"ok": True},
        "available_pages": {"index.html", "coverage.html", "reports.html"},
    }


def test_build_readiness_view_model_surfaces_suppressed_known_gaps_for_mvp_outage_signature() -> None:
    system_status = {
        "run_id": "RUN-LIVE-MVP-COMPLETE-014",
        "snapshot_id": "SNAP-RUN-LIVE-MVP-COMPLETE-014-v1",
        "coverage": {"countries_total": 30, "countries_with_updates": 29},
        "failed_sources": ["SRC-GDELT-DOC"],
        "data_gaps": ["failed_source:SRC-GDELT-DOC"],
        "country_coverage_visibility": {
            "country_gap_rows": [
                {
                    "country_id": "AUS",
                    "gap_details": [
                        {"domain": "A", "reason": "source_failed_this_run"},
                        {"domain": "D", "reason": "missing"},
                    ]
                }
            ]
        },
        "artifact_status": {},
    }

    view = build_readiness_view_model(**_base_inputs(system_status))

    assert view["known_gap_suppression_reason"] == "large_pilot_global_gdelt_doc_outage"
    assert "failed_source:SRC-GDELT-DOC" not in view["known_gaps"]
    assert "country_gap:AUS:A:source_failed_this_run" not in view["known_gaps"]
    assert "country_gap:AUS:D:missing" in view["known_gaps"]
    assert "failed_source:SRC-GDELT-DOC" in view["suppressed_known_gaps"]
    assert "country_gap:AUS:A:source_failed_this_run" in view["suppressed_known_gaps"]


def test_build_readiness_view_model_suppresses_gdelt_doc_outage_for_any_pilot_size() -> None:
    """New behaviour: global GDELT-DOC outage (all failed sources are SRC-GDELT-DOC / SRC-GDELT-DOC-E)
    is now suppressed for any pilot size, not only the 30-country mvp-complete set."""
    system_status = {
        "run_id": "RUN-LIVE-REP-001",
        "snapshot_id": "SNAP-RUN-LIVE-REP-001-v1",
        "coverage": {"countries_total": 4, "countries_with_updates": 3},
        "failed_sources": ["SRC-GDELT-DOC"],
        "data_gaps": ["failed_source:SRC-GDELT-DOC"],
        "country_coverage_visibility": {
            "country_gap_rows": [
                {
                    "country_id": "UKR",
                    "gap_details": [{"domain": "A", "reason": "source_failed_this_run"}],
                }
            ]
        },
        "artifact_status": {},
    }

    view = build_readiness_view_model(**_base_inputs(system_status))

    assert view["known_gap_suppression_reason"] == "global_gdelt_doc_outage"
    assert "failed_source:SRC-GDELT-DOC" not in view["known_gaps"]
    assert "country_gap:UKR:A:source_failed_this_run" not in view["known_gaps"]
    assert "failed_source:SRC-GDELT-DOC" in view["suppressed_known_gaps"]
    assert "country_gap:UKR:A:source_failed_this_run" in view["suppressed_known_gaps"]
    assert view["release_verdict"] == "ready"


def test_build_readiness_view_model_suppresses_gdelt_doc_and_doc_e_combined_outage() -> None:
    """Both SRC-GDELT-DOC and SRC-GDELT-DOC-E failing together also triggers suppression."""
    system_status = {
        "run_id": "RUN-LIVE-REP-002",
        "snapshot_id": "SNAP-RUN-LIVE-REP-002-v1",
        "coverage": {"countries_total": 4, "countries_with_updates": 3},
        "failed_sources": ["SRC-GDELT-DOC", "SRC-GDELT-DOC-E"],
        "data_gaps": [],
        "country_coverage_visibility": {
            "country_gap_rows": [
                {
                    "country_id": "POL",
                    "gap_details": [{"domain": "A", "reason": "source_failed_this_run"}],
                }
            ]
        },
        "artifact_status": {},
    }

    view = build_readiness_view_model(**_base_inputs(system_status))

    assert view["known_gap_suppression_reason"] == "global_gdelt_doc_outage"
    assert "failed_source:SRC-GDELT-DOC" in view["suppressed_known_gaps"]
    assert "failed_source:SRC-GDELT-DOC-E" in view["suppressed_known_gaps"]
    assert "country_gap:POL:A:source_failed_this_run" in view["suppressed_known_gaps"]
    assert view["release_verdict"] == "ready"


def test_build_readiness_view_model_no_suppression_when_non_gdelt_source_also_fails() -> None:
    """Suppression must NOT activate when a non-GDELT source also fails."""
    system_status = {
        "run_id": "RUN-LIVE-REP-003",
        "snapshot_id": "SNAP-RUN-LIVE-REP-003-v1",
        "coverage": {"countries_total": 4, "countries_with_updates": 3},
        "failed_sources": ["SRC-GDELT-DOC", "SRC-GDACS"],
        "data_gaps": ["failed_source:SRC-GDELT-DOC", "failed_source:SRC-GDACS"],
        "country_coverage_visibility": {"country_gap_rows": []},
        "artifact_status": {},
    }

    view = build_readiness_view_model(**_base_inputs(system_status))

    assert view["known_gap_suppression_reason"] is None
    assert view["suppressed_known_gaps"] == []
    assert "failed_source:SRC-GDELT-DOC" in view["known_gaps"]
    assert "failed_source:SRC-GDACS" in view["known_gaps"]
    assert view["release_verdict"] == "blocked_by_known_gaps"
