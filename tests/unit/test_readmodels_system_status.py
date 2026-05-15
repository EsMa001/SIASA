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
        top_status_changes=[
            {"country_id": "UKR", "from_status": "S2", "to_status": "S3", "direction": "up"},
            {"country_id": "POL", "from_status": "S2", "to_status": "S1", "direction": "down"},
        ],
        data_gaps=["failed_source:SRC-B", "failed_source:SRC-D"],
        country_coverage_visibility={
            "priority_summary": [
                {"priority": "P1", "country_count": 1, "countries": ["UKR"]},
                {"priority": "P2", "country_count": 2, "countries": ["POL", "ISR"]},
            ],
            "source_depth_band_summary": [
                {"band": "minimal", "country_count": 1, "countries": ["ISR"]},
                {"band": "moderate", "country_count": 1, "countries": ["UKR"]},
                {"band": "deep", "country_count": 1, "countries": ["POL"]},
            ],
            "country_gap_rows": [
                {"country_id": "ISR", "priority": "P2", "source_count": 1, "source_depth_band": "minimal", "missing_domains": ["D"], "missing_domain_count": 1},
            ],
            "missing_domain_totals": {"D": 1},
        },
    )

    assert read_model["run_id"] == "RUN-200"
    assert read_model["run_status"] == "partial_success"
    assert read_model["active_domains"] == ["A", "B", "D"]
    assert read_model["coverage"]["countries_total"] == 12
    assert read_model["coverage"]["countries_with_updates"] == 9
    assert read_model["failed_sources"] == ["SRC-B", "SRC-D"]
    assert read_model["available_reports"] == ["REP-DAILY-RUN-200", "REP-COUNTRY-UKR"]
    assert read_model["snapshot_id"] == "SNAP-RUN-200-v1"
    assert read_model["top_status_changes"][0] == {"country_id": "UKR", "from_status": "S2", "to_status": "S3", "direction": "up"}
    assert read_model["data_gaps"] == ["failed_source:SRC-B", "failed_source:SRC-D"]
    assert read_model["country_coverage_visibility"]["priority_summary"][1] == {
        "priority": "P2",
        "country_count": 2,
        "countries": ["POL", "ISR"],
    }
    assert read_model["country_coverage_visibility"]["source_depth_band_summary"][2]["band"] == "deep"
    assert read_model["country_coverage_visibility"]["country_gap_rows"][0]["missing_domains"] == ["D"]
    assert read_model["country_coverage_visibility"]["missing_domain_totals"] == {"D": 1}
