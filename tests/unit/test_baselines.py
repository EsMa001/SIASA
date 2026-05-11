from pytest import approx

from siasa.scoring.baselines import compute_combined_baseline, compute_relative_anomaly, resolve_current_window


def test_combined_baseline_supports_30_90_365_reference_windows() -> None:
    history = {
        30: [10.0, 14.0],
        90: [8.0, 12.0],
        365: [6.0, 10.0],
    }

    baseline = compute_combined_baseline(history)
    anomaly = compute_relative_anomaly(current_value=15.0, baseline_value=baseline)

    assert baseline == 10.0
    assert anomaly == approx(0.5)


def test_current_window_resolution_uses_governed_default_and_allows_detail_windows() -> None:
    assert resolve_current_window(configured_windows=["7d", "30d", "90d", "365d"]) == "7d"
    assert resolve_current_window(configured_windows=["7d", "30d", "90d", "365d"], requested_window="90d") == "90d"
