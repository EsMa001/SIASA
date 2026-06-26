#!/usr/bin/env python3
"""AP-24 threshold sensitivity analysis (OECD/JRC robustness step, finding F11).

One-at-a-time (OAT) sweep: perturb each governed scoring threshold, recompute the
validation skill metrics over the committed reference fixtures, and rank the
thresholds by how much they move the outcome. This operationalises the OECD/JRC
recommendation to use sensitivity analysis to find which parameters actually
matter -- an INFORM Severity re-audit found only 11 of 35 indicators carried real
numerical signal (docs/research/parameter-initialisierung.md).

It runs offline on the committed fixtures today and gains real discriminating
power once AP-30 supplies genuine historical depth; until then a threshold that
shows zero influence here is "no effect *on these fixtures*", not "irrelevant".

Usage:
    python scripts/threshold_sensitivity.py            # human-readable ranking
    python scripts/threshold_sensitivity.py --json     # full JSON report
    python scripts/threshold_sensitivity.py --repo-root /path/to/SIASA
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from siasa.scoring.scoring_thresholds import override_thresholds
from siasa.validation.cases import load_validation_case_library
from siasa.validation.historical_replay import (
    build_historical_replay_reviews,
    load_historical_replay_inputs,
)
from siasa.validation.skill_metrics import compute_skill_metrics

_CASE_LIBRARY = Path("vmodel/verification/validation_reference_cases.yaml")
_REPLAY_INPUTS = Path("vmodel/verification/validation_replay_inputs.yaml")

# OAT probe grid per governed threshold: name -> ((section, key), candidate values).
# Each grid spans current value -> science-anchored recommendation (governance record).
_PROBES: dict[str, tuple[tuple[str, str], list[float]]] = {
    "domain_status.d1_max": (("domain_status", "d1_max"), [0.1, 0.2, 0.5, 1.0]),
    "domain_status.d2_max": (("domain_status", "d2_max"), [0.35, 0.5, 1.0, 2.0]),
    "domain_status.d3_max": (("domain_status", "d3_max"), [0.65, 1.0, 2.0, 3.0]),
    "anomaly.upper_bound": (("anomaly", "upper_bound"), [1.0, 1.5, 2.0, 3.0]),
    "anomaly.min_series_points": (("anomaly", "min_series_points"), [2, 4, 8, 20]),
}


def _skill_metrics(repo_root: Path) -> dict[str, Any]:
    cases = load_validation_case_library(repo_root / _CASE_LIBRARY)
    inputs = load_historical_replay_inputs(repo_root / _REPLAY_INPUTS)
    reviews = build_historical_replay_reviews(cases, inputs)
    return compute_skill_metrics(reviews)


def run_sensitivity(
    repo_root: Path,
    probes: dict[str, tuple[tuple[str, str], list[float]]] | None = None,
) -> dict[str, Any]:
    """Run the OAT sweep and return a ranked sensitivity report."""
    probes = probes if probes is not None else _PROBES
    baseline = _skill_metrics(repo_root)
    base_score = float(baseline["skill_score"])

    ranked: list[dict[str, Any]] = []
    for name, (key, values) in probes.items():
        sweep: list[dict[str, Any]] = []
        for value in values:
            with override_thresholds({key: value}):
                metrics = _skill_metrics(repo_root)
            score = float(metrics["skill_score"])
            sweep.append(
                {
                    "value": value,
                    "skill_score": round(score, 4),
                    "delta": round(score - base_score, 4),
                    "status_match_count": metrics["status_match_count"],
                }
            )
        influence = round(max(abs(point["delta"]) for point in sweep), 4)
        ranked.append({"threshold": name, "influence": influence, "sweep": sweep})

    ranked.sort(key=lambda row: row["influence"], reverse=True)
    return {
        "baseline_skill_score": round(base_score, 4),
        "baseline_status_match_count": baseline["status_match_count"],
        "case_count": baseline["case_count"],
        "ranked_by_influence": ranked,
    }


def format_report(report: dict[str, Any]) -> str:
    lines = [
        "AP-24 threshold sensitivity (OAT over reference fixtures)",
        f"  baseline skill_score = {report['baseline_skill_score']} "
        f"(status_match {report['baseline_status_match_count']}/{report['case_count']})",
        "  thresholds ranked by influence on skill_score:",
    ]
    for row in report["ranked_by_influence"]:
        flag = "  <- moves the outcome" if row["influence"] > 0 else "  (no effect on these fixtures)"
        lines.append(f"    {row['influence']:>7.4f}  {row['threshold']}{flag}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="AP-24 threshold sensitivity analysis")
    parser.add_argument("--repo-root", default=".", help="repository root (default: current dir)")
    parser.add_argument("--json", action="store_true", help="emit the full JSON report")
    args = parser.parse_args()

    report = run_sensitivity(Path(args.repo_root).resolve())
    print(json.dumps(report, indent=2) if args.json else format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
