"""Governed scoring thresholds for SIASA (AP-24 / finding F11).

Loads the analytical thresholds from the governed YAML config
``vmodel/project/scoring_thresholds.yaml`` so the former hard-coded "magic
numbers" become a single, documented, owner-authority source-of-truth (per
OECD/JRC and INFORM). Mirrors the freshness_config pattern: module-level cache,
graceful fallback to the shipped defaults when the config is missing/unusable,
and an injectable ``config_path`` for tests.

The fallbacks below preserve the behaviour shipped to date, so wiring a module to
this loader is behaviour-neutral until the config values are deliberately changed.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

# Behaviour-preserving fallbacks (the values shipped before this config existed).
_DEFAULTS: dict[str, dict[str, float]] = {
    "anomaly": {"upper_bound": 1.5, "min_series_points": 4},
    "domain_status": {"d1_max": 0.2, "d2_max": 0.5, "d3_max": 1.0},
}

_CONFIG_PATH = Path(__file__).resolve().parents[3] / "vmodel" / "project" / "scoring_thresholds.yaml"

_cached_config: Optional[dict[str, dict[str, float]]] = None


def _load(config_path: Optional[Path] = None) -> dict[str, dict[str, float]]:
    global _cached_config
    if _cached_config is not None and config_path is None:
        return _cached_config

    result: dict[str, dict[str, float]] = {section: dict(values) for section, values in _DEFAULTS.items()}
    path = config_path or _CONFIG_PATH
    if path.exists():
        try:
            import yaml

            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for section in _DEFAULTS:
                for key in _DEFAULTS[section]:
                    raw = (data.get(section) or {}).get(key)
                    if raw is not None:
                        result[section][key] = raw
        except Exception:
            result = {section: dict(values) for section, values in _DEFAULTS.items()}

    if config_path is None:
        _cached_config = result
    return result


def clear_threshold_cache() -> None:
    """Clear the cached config (useful for tests)."""
    global _cached_config
    _cached_config = None


@contextmanager
def override_thresholds(overrides: dict[tuple[str, str], Any]) -> Iterator[None]:
    """Temporarily override governed thresholds, e.g. for sensitivity analysis.

    ``overrides`` maps ``(section, key)`` to a replacement value. Restores the
    previous (cached) config on exit. Not for production scoring — a sweep tool.
    """
    global _cached_config
    saved = _cached_config
    base = {section: dict(values) for section, values in _load().items()}
    for (section, key), value in overrides.items():
        base.setdefault(section, {})[key] = value
    _cached_config = base
    try:
        yield
    finally:
        _cached_config = saved


def anomaly_upper_bound(config_path: Optional[Path] = None) -> float:
    return float(_load(config_path)["anomaly"]["upper_bound"])


def anomaly_min_series_points(config_path: Optional[Path] = None) -> int:
    return int(_load(config_path)["anomaly"]["min_series_points"])


def domain_status_cutpoints(config_path: Optional[Path] = None) -> tuple[float, float, float]:
    """Return the (d1_max, d2_max, d3_max) anomaly cutpoints for D1/D2/D3/D4."""
    domain_status = _load(config_path)["domain_status"]
    return (float(domain_status["d1_max"]), float(domain_status["d2_max"]), float(domain_status["d3_max"]))


def get_all_scoring_thresholds(config_path: Optional[Path] = None) -> dict[str, dict[str, float]]:
    """Return the full governed threshold config for inspection/display."""
    return _load(config_path)
