"""TC-SwR-110-001: the sensitivity probe grid derives from the FULL governed config.

Audit finding (docs/research/wissenschaftliches-fundament-audit-2026-07.md, §7):
the previous hand-maintained probe grid covered 5 of ~38 governed parameters,
and the published result ("only d1_max matters") was a coverage/wiring artifact.
SwR-110 requires: full derivation from the governed configuration, explicit
reporting of anything not swept, and a hard fixture-bound validity caveat.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from threshold_sensitivity import (  # noqa: E402
    VALIDITY_CAVEAT,
    build_probe_grid,
    run_sensitivity,
)

from siasa.scoring.scoring_thresholds import get_all_scoring_thresholds  # noqa: E402


class TestProbeGridDerivation:
    def test_every_governed_section_is_covered(self):
        """No governed family may be silently absent from the sweep."""
        probes, not_swept = build_probe_grid()
        config = get_all_scoring_thresholds()

        covered_sections = {name.split(".")[0] for name in probes}
        excused_sections = {entry["parameter"].split(".")[0] for entry in not_swept}
        assert covered_sections | excused_sections == set(config)

    def test_every_governed_parameter_is_swept_or_excused(self):
        probes, not_swept = build_probe_grid()
        config = get_all_scoring_thresholds()

        governed = {f"{section}.{key}" for section in config for key in config[section]}
        # dict-valued parameters appear as section.key.subkey probes.
        swept = {".".join(name.split(".")[:2]) for name in probes}
        excused = {entry["parameter"] for entry in not_swept}
        assert governed == swept | excused, (
            f"unaccounted governed parameters: {sorted(governed - swept - excused)}"
        )

    def test_grid_is_substantially_larger_than_the_old_handmade_one(self):
        """The old grid had 5 entries; the derived grid must dwarf it."""
        probes, _ = build_probe_grid()
        assert len(probes) >= 30

    def test_dict_valued_parameters_probe_each_subkey(self):
        probes, _ = build_probe_grid()
        center_probes = [name for name in probes if name.startswith("bayesian_status.centers.")]
        assert set(center_probes) == {
            f"bayesian_status.centers.{status}" for status in ("D0", "D1", "D2", "D3", "D4")
        }
        # Each candidate is a full replacement dict for the override mechanism.
        (_, candidates) = probes["bayesian_status.centers.D3"]
        assert all(isinstance(candidate, dict) for candidate in candidates)
        assert all(candidate["D3"] != 0.75 for candidate in candidates)

    def test_probe_candidates_exclude_the_current_value(self):
        probes, _ = build_probe_grid()
        (_, candidates) = probes["domain_status.d1_max"]
        assert 0.2 not in candidates
        assert candidates  # never an empty sweep

    def test_zero_or_unsupported_values_are_excused_with_a_reason(self):
        grid_config = {"family": {"dead": 0.0, "label": "text"}}
        probes, not_swept = build_probe_grid(grid_config)
        assert probes == {}
        reasons = {entry["parameter"]: entry["reason"] for entry in not_swept}
        assert "family.dead" in reasons and "degenerate" in reasons["family.dead"]
        assert "family.label" in reasons


class TestReportHonesty:
    def test_report_carries_the_validity_caveat_and_coverage(self):
        # One cheap probe keeps the runtime down; the caveat and coverage
        # structure must be present regardless of grid size.
        probes = {
            "domain_status.d1_max": (("domain_status", "d1_max"), [0.1, 0.5]),
        }
        report = run_sensitivity(_REPO_ROOT, probes=probes)

        assert report["validity_caveat"] == VALIDITY_CAVEAT
        assert "fixture-bound" in report["validity_caveat"]
        assert report["probe_coverage"]["swept_parameter_count"] == 1
        assert report["ranked_by_influence"][0]["threshold"] == "domain_status.d1_max"

    def test_overrides_actually_reach_the_metric(self):
        """End-to-end: an extreme d1_max shift must move the skill score.

        This is the one influence claim the fixtures CAN support: the replay
        constant 0.7 crosses the d1 edge when d1_max sweeps past it.
        """
        probes = {
            "domain_status.d1_max": (("domain_status", "d1_max"), [1.0]),
        }
        report = run_sensitivity(_REPO_ROOT, probes=probes)
        assert report["ranked_by_influence"][0]["influence"] > 0
