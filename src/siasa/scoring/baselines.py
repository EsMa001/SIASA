from __future__ import annotations


def compute_combined_baseline(history_by_window_days: dict[int, list[float]]) -> float:
    window_means: list[float] = []
    for window in (30, 90, 365):
        values = history_by_window_days.get(window, [])
        if not values:
            continue
        window_means.append(sum(values) / len(values))
    if not window_means:
        raise ValueError("At least one governed baseline window is required")
    return sum(window_means) / len(window_means)


def compute_relative_anomaly(current_value: float, baseline_value: float) -> float:
    if baseline_value == 0:
        return 0.0 if current_value == 0 else 1.0
    return (current_value - baseline_value) / baseline_value


def resolve_current_window(configured_windows: list[str], requested_window: str | None = None) -> str:
    if not configured_windows:
        raise ValueError("At least one configured window is required")
    if requested_window is None:
        return configured_windows[0]
    if requested_window not in configured_windows:
        raise ValueError(f"Requested window {requested_window} is not governed")
    return requested_window
