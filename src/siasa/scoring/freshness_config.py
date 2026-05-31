"""Configurable freshness windows for SIASA data sufficiency scoring.

Loads per-domain and per-source freshness thresholds from a governed YAML
config file and resolves the effective threshold for a given domain+source
combination.

Resolution order:
  1. Per-source override (if present in config)
  2. Per-domain default (if present in config)
  3. Global default from config (or 168h fallback)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

_DEFAULT_GLOBAL_HOURS = 168.0

_FRESHNESS_CONFIG_PATH = (
    Path(__file__).resolve().parents[3] / "vmodel" / "project" / "freshness_config.yaml"
)

_cached_config: Optional[dict[str, Any]] = None


def _load_config(config_path: Optional[Path] = None) -> dict[str, Any]:
    """Load and cache freshness config from YAML."""
    global _cached_config
    if _cached_config is not None and config_path is None:
        return _cached_config

    path = config_path or _FRESHNESS_CONFIG_PATH
    if not path.exists():
        return {"global_default_hours": _DEFAULT_GLOBAL_HOURS, "domain_defaults": {}, "source_overrides": {}}

    import yaml
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    result = {
        "global_default_hours": float(data.get("global_default_hours", _DEFAULT_GLOBAL_HOURS)),
        "domain_defaults": {str(k): float(v) for k, v in (data.get("domain_defaults") or {}).items()},
        "source_overrides": {str(k): float(v) for k, v in (data.get("source_overrides") or {}).items()},
    }

    if config_path is None:
        _cached_config = result
    return result


def clear_config_cache() -> None:
    """Clear the cached config (useful for testing)."""
    global _cached_config
    _cached_config = None


def resolve_freshness_threshold(
    *,
    domain: str,
    source_id: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> float:
    """Resolve the effective freshness threshold in hours for a domain+source.

    Returns:
        Freshness threshold in hours.
    """
    config = _load_config(config_path)

    # 1. Per-source override
    if source_id and source_id in config["source_overrides"]:
        return config["source_overrides"][source_id]

    # 2. Per-domain default
    if domain in config["domain_defaults"]:
        return config["domain_defaults"][domain]

    # 3. Global default
    return config["global_default_hours"]


def get_all_freshness_thresholds(
    *,
    config_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Return the full freshness config for inspection/display."""
    return _load_config(config_path)
