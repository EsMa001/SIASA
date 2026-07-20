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
_DEFAULTS: dict[str, dict[str, Any]] = {
    "anomaly": {"upper_bound": 1.5, "min_series_points": 4},
    "domain_status": {"d1_max": 0.2, "d2_max": 0.5, "d3_max": 1.0},
    "data_sufficiency": {
        "minimum_coverage": 0.6,
        "maximum_freshness_hours": 168.0,
        "minimum_feature_count": 2,
    },
    "bayesian_status": {
        "centers": {"D0": 0.0, "D1": 0.1, "D2": 0.35, "D3": 0.75, "D4": 1.0},
        "sigma": 0.2,
        "credible_interval_tail": 0.1,
    },
    "cross_domain_fusion": {
        "reliability_sufficient": 1.0,
        "reliability_partial": 0.6,
        "reliability_insufficient": 0.2,
        "contradiction_gap": 2,
        "confidence_floor": 0.3,
        "confidence_discount_per_gap": 0.15,
    },
    "uncertainty_propagation": {
        "ci_z": 1.645,
        "extraction_noise": 0.10,
        "scoring_noise": 0.15,
        "fusion_noise": 0.05,
    },
    "skill_validation_metrics": {
        "detection_weight": 0.6,
        "domain_match_weight": 0.4,
        "alarm_minimum_status": "S1",
        "evidence_status_match_weight": 0.4,
        "evidence_domain_match_weight": 0.3,
        "evidence_source_coverage_weight": 0.2,
        "evidence_provenance_weight": 0.1,
        "tier_verified": 0.95,
        "tier_strong": 0.75,
        "tier_partial": 0.5,
        "regression_score_drop": 0.1,
        "regression_rate_warning": 0.1,
        "regression_rate_fail": 0.3,
    },
    "information_epidemiology": {"amplification_ratio": 1.5},
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


# --- data_sufficiency ---
def data_sufficiency_minimum_coverage(config_path: Optional[Path] = None) -> float:
    return float(_load(config_path)["data_sufficiency"]["minimum_coverage"])


def data_sufficiency_maximum_freshness_hours(config_path: Optional[Path] = None) -> float:
    return float(_load(config_path)["data_sufficiency"]["maximum_freshness_hours"])


def data_sufficiency_minimum_feature_count(config_path: Optional[Path] = None) -> int:
    return int(_load(config_path)["data_sufficiency"]["minimum_feature_count"])


# --- bayesian_status ---
def bayesian_status_centers(config_path: Optional[Path] = None) -> dict[str, float]:
    centers = _load(config_path)["bayesian_status"]["centers"]
    return {str(key): float(value) for key, value in centers.items()}


def bayesian_status_sigma(config_path: Optional[Path] = None) -> float:
    return float(_load(config_path)["bayesian_status"]["sigma"])


def bayesian_status_credible_interval_tail(config_path: Optional[Path] = None) -> float:
    return float(_load(config_path)["bayesian_status"]["credible_interval_tail"])


# --- cross_domain_fusion ---
def cross_domain_reliability_weights(config_path: Optional[Path] = None) -> tuple[float, float, float]:
    """Return (sufficient, partial, insufficient) evidence-reliability weights."""
    fusion = _load(config_path)["cross_domain_fusion"]
    return (
        float(fusion["reliability_sufficient"]),
        float(fusion["reliability_partial"]),
        float(fusion["reliability_insufficient"]),
    )


def cross_domain_contradiction_gap(config_path: Optional[Path] = None) -> int:
    return int(_load(config_path)["cross_domain_fusion"]["contradiction_gap"])


def cross_domain_confidence_floor(config_path: Optional[Path] = None) -> float:
    return float(_load(config_path)["cross_domain_fusion"]["confidence_floor"])


def cross_domain_confidence_discount_per_gap(config_path: Optional[Path] = None) -> float:
    return float(_load(config_path)["cross_domain_fusion"]["confidence_discount_per_gap"])


# --- uncertainty_propagation ---
def uncertainty_ci_z(config_path: Optional[Path] = None) -> float:
    return float(_load(config_path)["uncertainty_propagation"]["ci_z"])


def uncertainty_stage_noise(config_path: Optional[Path] = None) -> tuple[float, float, float]:
    """Return (extraction, scoring, fusion) stage-noise fractions."""
    unc = _load(config_path)["uncertainty_propagation"]
    return (float(unc["extraction_noise"]), float(unc["scoring_noise"]), float(unc["fusion_noise"]))


# --- skill_validation_metrics ---
def skill_score_weights(config_path: Optional[Path] = None) -> tuple[float, float]:
    """Return (detection, domain_match) composite skill weights."""
    skill = _load(config_path)["skill_validation_metrics"]
    return (float(skill["detection_weight"]), float(skill["domain_match_weight"]))


def skill_alarm_minimum_status(config_path: Optional[Path] = None) -> str:
    """Return the minimum S-status that counts as an alarm (SwR-113)."""
    skill = _load(config_path)["skill_validation_metrics"]
    return str(skill["alarm_minimum_status"])


def replay_evidence_weights(config_path: Optional[Path] = None) -> tuple[float, float, float, float]:
    """Return (status_match, domain_match, source_coverage, provenance) replay-evidence weights."""
    skill = _load(config_path)["skill_validation_metrics"]
    return (
        float(skill["evidence_status_match_weight"]),
        float(skill["evidence_domain_match_weight"]),
        float(skill["evidence_source_coverage_weight"]),
        float(skill["evidence_provenance_weight"]),
    )


def replay_evidence_tiers(config_path: Optional[Path] = None) -> tuple[float, float, float]:
    """Return (verified, strong, partial) replay-evidence tier cutpoints."""
    skill = _load(config_path)["skill_validation_metrics"]
    return (float(skill["tier_verified"]), float(skill["tier_strong"]), float(skill["tier_partial"]))


def regression_thresholds(config_path: Optional[Path] = None) -> tuple[float, float, float]:
    """Return (score_drop, rate_warning, rate_fail) backtest regression thresholds."""
    skill = _load(config_path)["skill_validation_metrics"]
    return (
        float(skill["regression_score_drop"]),
        float(skill["regression_rate_warning"]),
        float(skill["regression_rate_fail"]),
    )


# --- information_epidemiology ---
def amplification_ratio(config_path: Optional[Path] = None) -> float:
    return float(_load(config_path)["information_epidemiology"]["amplification_ratio"])


def get_all_scoring_thresholds(config_path: Optional[Path] = None) -> dict[str, dict[str, Any]]:
    """Return the full governed threshold config for inspection/display."""
    return _load(config_path)
