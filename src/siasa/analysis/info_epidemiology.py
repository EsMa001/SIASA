"""SIASA information epidemiology — spread path and amplification detection.

Models how information propagates across sources over time.

Requirement trace: AP-F25, StR-040..044 (Informations-Epidemiologie)
"""
from __future__ import annotations
from dataclasses import dataclass, field

from siasa.scoring.scoring_thresholds import amplification_ratio

# Governed via vmodel/project/scoring_thresholds.yaml (AP-24); resolved PER CALL
# (SwR-109) so overrides and sensitivity sweeps reach this module.


@dataclass(frozen=True)
class SpreadObservation:
    source_id: str
    signal_key: str
    observed_at_hours: float  # hours since epoch or reference
    value: float

@dataclass(frozen=True)
class SpreadPath:
    signal_key: str
    source_sequence: list[str]
    timing_deltas_hours: list[float]
    total_spread_hours: float

@dataclass(frozen=True)
class AmplificationEvent:
    signal_key: str
    source_id: str
    amplification_factor: float  # value ratio vs first observation
    lag_hours: float

def detect_spread_paths(observations: list[SpreadObservation]) -> list[SpreadPath]:
    if not observations:
        return []
    by_signal: dict[str, list[SpreadObservation]] = {}
    for obs in observations:
        by_signal.setdefault(obs.signal_key, []).append(obs)
    paths = []
    for sig, obs_list in sorted(by_signal.items()):
        sorted_obs = sorted(obs_list, key=lambda o: o.observed_at_hours)
        if len(sorted_obs) < 2:
            continue
        sources = [o.source_id for o in sorted_obs]
        deltas = [sorted_obs[i+1].observed_at_hours - sorted_obs[i].observed_at_hours for i in range(len(sorted_obs)-1)]
        paths.append(SpreadPath(
            signal_key=sig, source_sequence=sources,
            timing_deltas_hours=[round(d, 2) for d in deltas],
            total_spread_hours=round(sorted_obs[-1].observed_at_hours - sorted_obs[0].observed_at_hours, 2),
        ))
    return paths

def detect_amplification(observations: list[SpreadObservation]) -> list[AmplificationEvent]:
    if not observations:
        return []
    threshold_ratio = amplification_ratio()
    by_signal: dict[str, list[SpreadObservation]] = {}
    for obs in observations:
        by_signal.setdefault(obs.signal_key, []).append(obs)
    events = []
    for sig, obs_list in sorted(by_signal.items()):
        sorted_obs = sorted(obs_list, key=lambda o: o.observed_at_hours)
        if len(sorted_obs) < 2 or sorted_obs[0].value <= 0:
            continue
        base = sorted_obs[0].value
        for obs in sorted_obs[1:]:
            factor = obs.value / base
            if factor > threshold_ratio:
                events.append(AmplificationEvent(
                    signal_key=sig, source_id=obs.source_id,
                    amplification_factor=round(factor, 3),
                    lag_hours=round(obs.observed_at_hours - sorted_obs[0].observed_at_hours, 2),
                ))
    return events
