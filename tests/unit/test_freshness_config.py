from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from siasa.scoring.freshness_config import (
    clear_config_cache,
    get_all_freshness_thresholds,
    resolve_freshness_threshold,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_config_cache()
    yield
    clear_config_cache()


def _write_config(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "freshness_config.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    return p


def test_resolve_domain_default(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, {
        "global_default_hours": 168.0,
        "domain_defaults": {"A": 72.0, "B": 336.0},
        "source_overrides": {},
    })
    assert resolve_freshness_threshold(domain="A", config_path=cfg) == 72.0
    assert resolve_freshness_threshold(domain="B", config_path=cfg) == 336.0


def test_resolve_source_override(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, {
        "global_default_hours": 168.0,
        "domain_defaults": {"D": 168.0},
        "source_overrides": {"WB-INDICATORS": 720.0},
    })
    assert resolve_freshness_threshold(domain="D", source_id="WB-INDICATORS", config_path=cfg) == 720.0
    # Without source_id, falls back to domain
    assert resolve_freshness_threshold(domain="D", config_path=cfg) == 168.0


def test_resolve_global_fallback(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, {
        "global_default_hours": 200.0,
        "domain_defaults": {},
        "source_overrides": {},
    })
    assert resolve_freshness_threshold(domain="X", config_path=cfg) == 200.0


def test_resolve_missing_config_file(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.yaml"
    result = resolve_freshness_threshold(domain="A", config_path=missing)
    assert result == 168.0  # hardcoded fallback


def test_get_all_freshness_thresholds(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, {
        "global_default_hours": 168.0,
        "domain_defaults": {"A": 72.0},
        "source_overrides": {"WB-INDICATORS": 720.0},
    })
    all_cfg = get_all_freshness_thresholds(config_path=cfg)
    assert all_cfg["global_default_hours"] == 168.0
    assert all_cfg["domain_defaults"]["A"] == 72.0
    assert all_cfg["source_overrides"]["WB-INDICATORS"] == 720.0


def test_resolve_priority_source_over_domain(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, {
        "global_default_hours": 168.0,
        "domain_defaults": {"D": 100.0},
        "source_overrides": {"SRC-GDELT-DOC": 48.0},
    })
    # Source override wins over domain
    assert resolve_freshness_threshold(domain="D", source_id="SRC-GDELT-DOC", config_path=cfg) == 48.0
    # Unknown source falls through to domain
    assert resolve_freshness_threshold(domain="D", source_id="UNKNOWN", config_path=cfg) == 100.0


def test_real_config_file_loads() -> None:
    """Smoke test: the governed freshness_config.yaml is valid and parseable."""
    all_cfg = get_all_freshness_thresholds()
    assert all_cfg["global_default_hours"] > 0
    assert "A" in all_cfg["domain_defaults"]
