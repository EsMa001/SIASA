#!/usr/bin/env python3
"""AP-24/AP-34 threshold sensitivity analysis (OECD/JRC robustness step, ALGO-SENS-01).

One-at-a-time (OAT) sweep: perturb each governed scoring threshold, recompute the
validation skill metrics over the committed reference fixtures, and rank the
thresholds by how much they move the outcome.

SwR-110 hardening (audit findings A-01/A-02, docs/research/
wissenschaftliches-fundament-audit-2026-07.md):

* The probe grid is DERIVED from the complete governed configuration
  (``get_all_scoring_thresholds``) instead of a hand-maintained subset — a
  parameter family added to the YAML is swept automatically, and anything the
  generator cannot sweep is reported explicitly under ``not_swept`` with a
  reason. No silent coverage gaps.
* Every report carries a hard ``validity_caveat``: as long as the replay status
  derives from the constant fixture table (``_DOMAIN_ANOMALY_SCORES``,
  audit A-01), influence values describe the measurement harness, NOT the
  model. The caveat disappears only when that wiring is replaced (roadmap V-8).
* Requires the per-call threshold resolution of SwR-109 — with the former
  import-time constant binding, most families were mechanically incapable of
  showing any influence.

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

from siasa.scoring.scoring_thresholds import get_all_scoring_thresholds, override_thresholds
from siasa.validation.cases import load_validation_case_library
from siasa.validation.historical_replay import (
    build_historical_replay_reviews,
    load_historical_replay_inputs,
)
from siasa.validation.skill_metrics import compute_skill_metrics

_CASE_LIBRARY = Path("vmodel/verification/validation_reference_cases.yaml")
_REPLAY_INPUTS = Path("vmodel/verification/validation_replay_inputs.yaml")

# Multiplicative OAT grid around the current value (OECD/JRC: perturb, observe).
_SCALE_FACTORS = (0.5, 0.75, 1.5, 2.0)

VALIDITY_CAVEAT = (
    "fixture-bound: the outcome metric runs over committed synthetic fixtures and a "
    "replay status derived from the constant table _DOMAIN_ANOMALY_SCORES "
    "(audit A-01). Influence values describe the measurement harness, NOT the model. "
    "They become model-informative only once the replay path uses the data-driven "
    "anomaly on real historical windows (roadmap V-8, AP-26/AP-30)."
)


def _scaled_candidates(value: float, *, integer: bool) -> list[float | int]:
    """Multiplicative probe values around ``value``, deduplicated, current value excluded."""
    candidates: list[float | int] = []
    for factor in _SCALE_FACTORS:
        candidate: float | int = value * factor
        if integer:
            candidate = max(1, int(round(candidate)))
        else:
            candidate = round(candidate, 6)
        if candidate != value and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def build_probe_grid(
    config: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, tuple[tuple[str, str], list[Any]]], list[dict[str, str]]]:
    """Derive the OAT probe grid from the full governed configuration.

    Returns ``(probes, not_swept)``. ``probes`` maps a display name to
    ``((section, key), candidate_values)``; for dict-valued parameters each
    sub-key becomes its own probe whose candidates are full replacement dicts.
    ``not_swept`` lists every governed parameter the generator cannot sweep,
    with a reason — coverage gaps are reported, never silent.
    """
    config = config if config is not None else get_all_scoring_thresholds()
    probes: dict[str, tuple[tuple[str, str], list[Any]]] = {}
    not_swept: list[dict[str, str]] = []

    for section in sorted(config):
        for key in sorted(config[section]):
            value = config[section][key]
            name = f"{section}.{key}"
            if isinstance(value, bool):
                not_swept.append({"parameter": name, "reason": "boolean — no OAT scale"})
            elif isinstance(value, int) and not isinstance(value, bool):
                probes[name] = ((section, key), _scaled_candidates(value, integer=True))
            elif isinstance(value, float):
                if value == 0.0:
                    not_swept.append({"parameter": name, "reason": "zero-valued — multiplicative grid degenerate"})
                else:
                    probes[name] = ((section, key), _scaled_candidates(value, integer=False))
            elif isinstance(value, dict) and value and all(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in value.values()
            ):
                for sub_key in sorted(value):
                    sub_value = float(value[sub_key])
                    variants: list[Any] = []
                    for candidate in _scaled_candidates(sub_value, integer=False) or [round(sub_value + 0.1, 6)]:
                        replacement = dict(value)
                        replacement[sub_key] = candidate
                        variants.append(replacement)
                    probes[f"{name}.{sub_key}"] = ((section, key), variants)
            else:
                not_swept.append(
                    {"parameter": name, "reason": f"unsupported type {type(value).__name__} — needs a bespoke probe"}
                )

    return probes, not_swept


def _skill_metrics(repo_root: Path) -> dict[str, Any]:
    cases = load_validation_case_library(repo_root / _CASE_LIBRARY)
    inputs = load_historical_replay_inputs(repo_root / _REPLAY_INPUTS)
    reviews = build_historical_replay_reviews(cases, inputs)
    return compute_skill_metrics(reviews)


def run_sensitivity(
    repo_root: Path,
    probes: dict[str, tuple[tuple[str, str], list[Any]]] | None = None,
) -> dict[str, Any]:
    """Run the OAT sweep and return a ranked sensitivity report."""
    if probes is None:
        probes, not_swept = build_probe_grid()
    else:
        not_swept = []
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

    ranked.sort(key=lambda row: (-row["influence"], row["threshold"]))
    return {
        "validity_caveat": VALIDITY_CAVEAT,
        "baseline_skill_score": round(base_score, 4),
        "baseline_status_match_count": baseline["status_match_count"],
        "case_count": baseline["case_count"],
        "probe_coverage": {
            "swept_parameter_count": len(probes),
            "not_swept": not_swept,
        },
        "ranked_by_influence": ranked,
    }


def format_report(report: dict[str, Any]) -> str:
    lines = [
        "AP-24/AP-34 threshold sensitivity (OAT over reference fixtures, ALGO-SENS-01)",
        f"  !! VALIDITY: {report['validity_caveat']}",
        f"  baseline skill_score = {report['baseline_skill_score']} "
        f"(status_match {report['baseline_status_match_count']}/{report['case_count']})",
        f"  probes swept: {report['probe_coverage']['swept_parameter_count']}"
        f" | not swept: {len(report['probe_coverage']['not_swept'])}",
    ]
    for entry in report["probe_coverage"]["not_swept"]:
        lines.append(f"    not swept: {entry['parameter']} ({entry['reason']})")
    lines.append("  thresholds ranked by influence on skill_score:")
    for row in report["ranked_by_influence"]:
        flag = "  <- moves the outcome" if row["influence"] > 0 else "  (no effect on these fixtures)"
        lines.append(f"    {row['influence']:>7.4f}  {row['threshold']}{flag}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="AP-24/AP-34 threshold sensitivity analysis")
    parser.add_argument("--repo-root", default=".", help="repository root (default: current dir)")
    parser.add_argument("--json", action="store_true", help="emit the full JSON report")
    args = parser.parse_args()

    report = run_sensitivity(Path(args.repo_root).resolve())
    print(json.dumps(report, indent=2) if args.json else format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
