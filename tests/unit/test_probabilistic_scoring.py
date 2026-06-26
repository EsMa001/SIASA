"""Tests for probabilistic scoring."""
from siasa.scoring.probabilistic import compute_bayesian_status, transition_probability

def test_uniform_prior():
    est = compute_bayesian_status(0.5)
    assert sum(est.posterior.values()) > 0.99
    assert est.map_status in ["D0","D1","D2","D3","D4"]

def test_high_anomaly_favors_d4():
    est = compute_bayesian_status(1.0)
    assert est.map_status == "D4"
    assert est.confidence > 0.3

def test_low_anomaly_favors_d1():
    est = compute_bayesian_status(0.1)
    assert est.map_status == "D1"

def test_d3_center_is_band_midpoint():
    # AP-24/SHELF: likelihood centers = midpoints of the D-status anomaly bands.
    # D3 band is [0.5, 1.0); its midpoint 0.75 must map cleanly to D3.
    est = compute_bayesian_status(0.75)
    assert est.map_status == "D3"


def test_confidence_interval():
    est = compute_bayesian_status(0.5)
    assert est.confidence_interval[0] in ["D0","D1","D2","D3","D4"]
    assert est.confidence_interval[1] in ["D0","D1","D2","D3","D4"]

def test_transition_probability():
    probs = transition_probability("D2", 0.5)
    assert sum(probs.values()) > 0.99
    assert len(probs) == 5
