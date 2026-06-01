"""Tests for uncertainty propagation."""
from siasa.scoring.uncertainty_propagation import propagate_uncertainty

def test_empty():
    b = propagate_uncertainty([])
    assert b.total_uncertainty == 0.0

def test_single_source():
    b = propagate_uncertainty([(0.5, 0.1)])
    assert len(b.levels) == 4
    assert b.levels[0].stage == "source"
    assert b.levels[-1].stage == "multi_domain"
    assert b.total_uncertainty > 0

def test_multi_source_reduces_uncertainty():
    b1 = propagate_uncertainty([(0.5, 0.2)])
    b3 = propagate_uncertainty([(0.5, 0.2), (0.5, 0.2), (0.5, 0.2)])
    # More sources -> lower source-level uncertainty (averaged)
    assert b3.levels[0].uncertainty < b1.levels[0].uncertainty

def test_propagation_increases():
    b = propagate_uncertainty([(0.5, 0.1)])
    # Uncertainty should increase through the chain
    assert b.levels[-1].uncertainty >= b.levels[0].uncertainty

def test_confidence_intervals():
    b = propagate_uncertainty([(0.5, 0.1)])
    for level in b.levels:
        assert level.confidence_low < level.value
        assert level.confidence_high > level.value
