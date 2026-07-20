"""SIASA probabilistic D-status classification.

Bayesian estimation of domain status with confidence intervals.

Requirement trace: AP-F26, StR-057..061 (Probabilistische Zustandsmodellierung)
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math

from siasa.scoring.scoring_thresholds import (
    bayesian_status_centers,
    bayesian_status_credible_interval_tail,
    bayesian_status_sigma,
)

# Governed via vmodel/project/scoring_thresholds.yaml (AP-24); centers/sigma/tail are
# resolved PER CALL (SwR-109) so overrides and sensitivity sweeps reach this module.
_STATUS_LABELS = ["D0", "D1", "D2", "D3", "D4"]

@dataclass(frozen=True)
class BayesianStatusEstimate:
    posterior: dict[str, float]  # status -> probability
    map_status: str  # maximum a posteriori
    confidence: float  # probability of MAP status
    confidence_interval: tuple[str, str]  # 80% credible interval (low, high)

def _gaussian_likelihood(x: float, mu: float, sigma: float) -> float:
    return math.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))

def compute_bayesian_status(
    anomaly_score: float,
    prior: dict[str, float] | None = None,
) -> BayesianStatusEstimate:
    centers = bayesian_status_centers()
    sigma = bayesian_status_sigma()
    credible_interval_tail = bayesian_status_credible_interval_tail()
    if prior is None:
        prior = {s: 1.0 / len(_STATUS_LABELS) for s in _STATUS_LABELS}
    unnormalized = {}
    for status in _STATUS_LABELS:
        likelihood = _gaussian_likelihood(anomaly_score, centers[status], sigma)
        unnormalized[status] = prior.get(status, 0.0) * likelihood
    total = sum(unnormalized.values())
    if total <= 0:
        posterior = {s: 1.0 / len(_STATUS_LABELS) for s in _STATUS_LABELS}
    else:
        posterior = {s: round(v / total, 6) for s, v in unnormalized.items()}
    map_status = max(posterior, key=lambda s: posterior[s])
    confidence = posterior[map_status]
    # 80% credible interval
    cumulative = 0.0
    low = _STATUS_LABELS[0]
    high = _STATUS_LABELS[-1]
    for s in _STATUS_LABELS:
        cumulative += posterior[s]
        if cumulative >= credible_interval_tail:
            low = s
            break
    cumulative = 0.0
    for s in reversed(_STATUS_LABELS):
        cumulative += posterior[s]
        if cumulative >= credible_interval_tail:
            high = s
            break
    return BayesianStatusEstimate(posterior=posterior, map_status=map_status, confidence=round(confidence, 4), confidence_interval=(low, high))

def transition_probability(current_status: str, anomaly_delta: float) -> dict[str, float]:
    idx = _STATUS_LABELS.index(current_status) if current_status in _STATUS_LABELS else 1
    probs = {}
    for i, s in enumerate(_STATUS_LABELS):
        distance = abs(i - idx) - anomaly_delta
        probs[s] = round(max(0.01, math.exp(-0.5 * distance ** 2)), 4)
    total = sum(probs.values())
    return {s: round(v / total, 4) for s, v in probs.items()}
