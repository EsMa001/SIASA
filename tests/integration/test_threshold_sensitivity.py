"""Integration smoke for the AP-24 threshold sensitivity tool (scripts/threshold_sensitivity.py).

Loads the standalone script as a module and runs a tiny OAT sweep over the committed
reference fixtures, asserting it produces a ranked report and restores the governed
thresholds afterwards.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from siasa.scoring.scoring_thresholds import clear_threshold_cache, domain_status_cutpoints

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_sensitivity_module():
    script = _REPO_ROOT / "scripts" / "threshold_sensitivity.py"
    spec = importlib.util.spec_from_file_location("threshold_sensitivity", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sensitivity_run_produces_ranked_report():
    module = _load_sensitivity_module()
    clear_threshold_cache()

    # Minimal probe keeps the smoke fast; full grid lives in the script's _PROBES.
    probes = {"domain_status.d3_max": (("domain_status", "d3_max"), [1.0, 3.0])}
    report = module.run_sensitivity(_REPO_ROOT, probes)

    assert "baseline_skill_score" in report
    assert report["case_count"] > 0
    assert report["ranked_by_influence"], "expected at least one ranked threshold"

    row = report["ranked_by_influence"][0]
    assert row["threshold"] == "domain_status.d3_max"
    assert row["influence"] >= 0.0
    assert len(row["sweep"]) == 2
    assert {"value", "skill_score", "delta", "status_match_count"} <= set(row["sweep"][0])

    # The sweep must leave the governed thresholds untouched.
    assert domain_status_cutpoints() == (0.2, 0.5, 1.0)


def test_format_report_renders_ranking():
    module = _load_sensitivity_module()
    report = {
        "baseline_skill_score": 0.5,
        "baseline_status_match_count": 20,
        "case_count": 36,
        "ranked_by_influence": [
            {"threshold": "domain_status.d3_max", "influence": 0.12, "sweep": []},
            {"threshold": "anomaly.upper_bound", "influence": 0.0, "sweep": []},
        ],
    }
    text = module.format_report(report)
    assert "baseline skill_score = 0.5" in text
    assert "domain_status.d3_max" in text
    assert "moves the outcome" in text
    assert "no effect on these fixtures" in text
