"""Tests for information epidemiology."""
from siasa.analysis.info_epidemiology import SpreadObservation, detect_spread_paths, detect_amplification

def test_no_spread():
    assert detect_spread_paths([]) == []

def test_simple_spread():
    obs = [
        SpreadObservation("SRC-A", "conflict", 0.0, 10.0),
        SpreadObservation("SRC-B", "conflict", 2.0, 12.0),
        SpreadObservation("SRC-C", "conflict", 5.0, 15.0),
    ]
    paths = detect_spread_paths(obs)
    assert len(paths) == 1
    assert paths[0].source_sequence == ["SRC-A", "SRC-B", "SRC-C"]
    assert paths[0].total_spread_hours == 5.0

def test_amplification():
    obs = [
        SpreadObservation("SRC-A", "tone", 0.0, 10.0),
        SpreadObservation("SRC-B", "tone", 3.0, 20.0),
    ]
    events = detect_amplification(obs)
    assert len(events) == 1
    assert events[0].amplification_factor == 2.0

def test_no_amplification_below_threshold():
    obs = [
        SpreadObservation("SRC-A", "tone", 0.0, 10.0),
        SpreadObservation("SRC-B", "tone", 3.0, 12.0),
    ]
    events = detect_amplification(obs)
    assert len(events) == 0
