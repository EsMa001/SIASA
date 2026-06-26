"""Unit tests for AP-24 governed scoring thresholds (F11).

Verifies the threshold loader (graceful fallback + config override) and that the
anomaly / domain-status modules are wired to it behaviour-preservingly.
"""
from __future__ import annotations

from siasa.scoring.data_sufficiency import DataSufficiencyResult
from siasa.scoring.domain_status import derive_domain_status
from siasa.scoring.scoring_thresholds import (
    anomaly_min_series_points,
    anomaly_upper_bound,
    clear_threshold_cache,
    domain_status_cutpoints,
    override_thresholds,
)


def test_loader_falls_back_to_defaults_when_config_missing(tmp_path):
    missing = tmp_path / "nope.yaml"
    assert anomaly_upper_bound(missing) == 1.5
    assert anomaly_min_series_points(missing) == 4
    assert domain_status_cutpoints(missing) == (0.2, 0.5, 1.0)


def test_loader_reads_overridden_values_from_config(tmp_path):
    cfg = tmp_path / "scoring_thresholds.yaml"
    cfg.write_text(
        "anomaly:\n  upper_bound: 3.0\n  min_series_points: 20\n"
        "domain_status:\n  d1_max: 1.0\n  d2_max: 2.0\n  d3_max: 3.0\n",
        encoding="utf-8",
    )
    assert anomaly_upper_bound(cfg) == 3.0
    assert anomaly_min_series_points(cfg) == 20
    assert domain_status_cutpoints(cfg) == (1.0, 2.0, 3.0)


def test_governed_config_preserves_shipped_behaviour():
    # The committed vmodel/project/scoring_thresholds.yaml holds the current values.
    clear_threshold_cache()
    assert anomaly_upper_bound() == 1.5
    assert anomaly_min_series_points() == 4
    assert domain_status_cutpoints() == (0.2, 0.5, 1.0)


def test_override_thresholds_restores_previous_config():
    clear_threshold_cache()
    assert domain_status_cutpoints() == (0.2, 0.5, 1.0)
    with override_thresholds({("domain_status", "d3_max"): 3.0, ("anomaly", "upper_bound"): 3.0}):
        assert domain_status_cutpoints() == (0.2, 0.5, 3.0)
        assert anomaly_upper_bound() == 3.0
    assert domain_status_cutpoints() == (0.2, 0.5, 1.0)
    assert anomaly_upper_bound() == 1.5


def test_anomaly_module_constants_are_wired_to_governed_thresholds():
    from siasa.scoring import anomaly

    assert anomaly.ANOMALY_UPPER_BOUND == anomaly_upper_bound()
    assert anomaly._MIN_SERIES_POINTS == anomaly_min_series_points()


def test_domain_status_uses_governed_cutpoints():
    sufficient = DataSufficiencyResult(is_sufficient=True, coverage=1.0, freshness_hours=None, reasons=[])
    d1_max, d2_max, d3_max = domain_status_cutpoints()

    def status_for(score: float) -> str:
        return derive_domain_status("A", anomaly_score=score, sufficiency=sufficient).status

    assert status_for(d1_max - 0.01) == "D1"
    assert status_for(d1_max) == "D2"
    assert status_for(d2_max - 0.01) == "D2"
    assert status_for(d2_max) == "D3"
    assert status_for(d3_max - 0.01) == "D3"
    assert status_for(d3_max) == "D4"
