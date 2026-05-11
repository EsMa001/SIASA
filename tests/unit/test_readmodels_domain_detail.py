from siasa.readmodels.domain_detail import build_domain_detail_read_model


def test_domain_detail_read_model_exposes_time_series_baseline_comparison_feature_values_and_source_context() -> None:
    read_model = build_domain_detail_read_model(
        country_id="UKR",
        domain="A",
        time_series=[
            {"timestamp": "2026-05-10", "value": 0.42},
            {"timestamp": "2026-05-11", "value": 0.67},
        ],
        baseline_comparison={
            "current_window": 0.67,
            "baseline_30d": 0.31,
            "baseline_90d": 0.28,
            "delta_to_baseline": 0.36,
        },
        feature_values=[
            {"feature_id": "A_article_count", "value": 12.0, "coverage": 0.9},
            {"feature_id": "A_tone_shift", "value": 0.3, "coverage": 0.8},
        ],
        source_context=[
            {"source_id": "SRC-A", "freshness_hours": 6, "history_horizon": "3y", "status": "success"},
            {"source_id": "SRC-A2", "freshness_hours": 12, "history_horizon": "1y", "status": "partial_success"},
        ],
    )

    assert read_model["country_id"] == "UKR"
    assert read_model["domain"] == "A"
    assert read_model["time_series"][1]["value"] == 0.67
    assert read_model["baseline_comparison"]["delta_to_baseline"] == 0.36
    assert read_model["feature_values"][0]["feature_id"] == "A_article_count"
    assert read_model["source_context"][1]["status"] == "partial_success"
