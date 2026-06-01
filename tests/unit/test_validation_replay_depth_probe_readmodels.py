from __future__ import annotations

import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
_PROBE_CANDIDATES = [
    REPO_ROOT / "build" / "run_artifacts" / "_rep_validation_replay_depth_probe_1" / "readmodels",
    REPO_ROOT / "build" / "run_artifacts" / "_rep_ce_probe" / "readmodels",
    REPO_ROOT / "build" / "run_artifacts" / "latest" / "readmodels",
]


def _resolve_probe_root() -> Path:
    for candidate in _PROBE_CANDIDATES:
        if (candidate / "validation_backtest.json").exists():
            return candidate
    raise FileNotFoundError("validation_backtest.json not found in known probe readmodel locations")


def _load_validation_backtest() -> dict[str, object]:
    return json.loads((_resolve_probe_root() / "validation_backtest.json").read_text(encoding="utf-8"))


def test_validation_replay_depth_probe_has_multi_case_portfolio_summary() -> None:
    backtest = _load_validation_backtest()

    portfolio_summary = backtest.get("portfolio_summary")
    assert isinstance(portfolio_summary, dict)
    assert portfolio_summary.get("case_count") == 4
    assert portfolio_summary.get("countries_covered") == ["ISR", "POL", "TWN", "UKR"]


def test_validation_replay_depth_probe_has_reference_library_summary() -> None:
    backtest = _load_validation_backtest()

    summary = backtest.get("reference_case_library_summary")
    assert isinstance(summary, dict)
    assert int(summary.get("case_count", 0)) >= 4
    countries_covered = summary.get("countries_covered")
    assert isinstance(countries_covered, list)
    assert "UKR" in countries_covered


def test_validation_reference_case_library_is_broadened_repo_baseline() -> None:
    library = yaml.safe_load(
        (REPO_ROOT / "vmodel" / "verification" / "validation_reference_cases.yaml").read_text(encoding="utf-8")
    )

    cases = library.get("validation_cases")
    assert isinstance(cases, list)
    assert len(cases) >= 20

    country_ids = {case.get("country_id") for case in cases}
    assert "UKR" in country_ids
    assert "GEO" in country_ids
    assert "PAK" in country_ids


def test_validation_replay_depth_probe_has_replay_evidence_depth_signals() -> None:
    backtest = _load_validation_backtest()

    replay_summary = backtest.get("historical_replay_summary")
    assert isinstance(replay_summary, dict)
    assert int(replay_summary.get("case_count", 0)) >= 4
    assert "replay_evidence_tier_counts" in replay_summary
    assert "average_replay_evidence_score" in replay_summary

    replay_reviews = backtest.get("historical_replay_reviews")
    assert isinstance(replay_reviews, list)
    assert len(replay_reviews) >= 4

    sample = replay_reviews[0]
    assert "replay_evidence_score" in sample
    assert "replay_evidence_tier" in sample
    assert "replay_source_coverage_ratio" in sample
    assert "replay_provenance_completeness_ratio" in sample
