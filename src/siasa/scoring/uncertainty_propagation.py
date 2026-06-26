"""SIASA uncertainty propagation.

Propagates uncertainty from source -> feature -> domain -> multi-domain
with explicit confidence intervals at each level.

Requirement trace: AP-F27, StR-051..056 (Unsicherheit und Explainability)
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math

from siasa.scoring.scoring_thresholds import uncertainty_ci_z, uncertainty_stage_noise

@dataclass(frozen=True)
class UncertaintyLevel:
    stage: str  # "source", "feature", "domain", "multi_domain"
    value: float  # point estimate
    uncertainty: float  # standard deviation
    confidence_low: float  # 90% CI lower
    confidence_high: float  # 90% CI upper
    sources_contributing: int

@dataclass(frozen=True)
class UncertaintyBudget:
    levels: list[UncertaintyLevel]
    total_uncertainty: float
    dominant_stage: str
    propagation_factor: float  # ratio of output to input uncertainty

def propagate_uncertainty(source_uncertainties: list[tuple[float, float]]) -> UncertaintyBudget:
    """Propagate uncertainty through the processing chain.

    Args:
        source_uncertainties: list of (value, uncertainty_stddev) per source.
    """
    if not source_uncertainties:
        return UncertaintyBudget([], 0.0, "none", 1.0)

    levels: list[UncertaintyLevel] = []
    n = len(source_uncertainties)
    values = [v for v, _ in source_uncertainties]
    uncertainties = [u for _, u in source_uncertainties]

    # Source level: individual uncertainties
    source_mean = sum(values) / max(n, 1)
    source_unc = math.sqrt(sum(u**2 for u in uncertainties)) / max(n, 1)
    z90 = uncertainty_ci_z()
    extraction_noise, scoring_noise, fusion_noise = uncertainty_stage_noise()
    levels.append(UncertaintyLevel(
        "source", round(source_mean, 4), round(source_unc, 4),
        round(source_mean - z90 * source_unc, 4), round(source_mean + z90 * source_unc, 4), n,
    ))

    # Feature level: adds extraction noise (~10%)
    feat_unc = math.sqrt(source_unc**2 + (extraction_noise * source_mean)**2)
    levels.append(UncertaintyLevel(
        "feature", round(source_mean, 4), round(feat_unc, 4),
        round(source_mean - z90 * feat_unc, 4), round(source_mean + z90 * feat_unc, 4), n,
    ))

    # Domain level: adds scoring model uncertainty (~15%)
    dom_unc = math.sqrt(feat_unc**2 + (scoring_noise * source_mean)**2)
    levels.append(UncertaintyLevel(
        "domain", round(source_mean, 4), round(dom_unc, 4),
        round(source_mean - z90 * dom_unc, 4), round(source_mean + z90 * dom_unc, 4), n,
    ))

    # Multi-domain: adds fusion uncertainty (~5%)
    multi_unc = math.sqrt(dom_unc**2 + (fusion_noise * source_mean)**2)
    levels.append(UncertaintyLevel(
        "multi_domain", round(source_mean, 4), round(multi_unc, 4),
        round(source_mean - z90 * multi_unc, 4), round(source_mean + z90 * multi_unc, 4), n,
    ))

    # Dominant stage
    stage_contributions = {
        "source": source_unc**2,
        "feature_extraction": (extraction_noise * source_mean)**2,
        "domain_scoring": (scoring_noise * source_mean)**2,
        "fusion": (fusion_noise * source_mean)**2,
    }
    dominant = max(stage_contributions, key=lambda k: stage_contributions[k])
    prop_factor = multi_unc / max(source_unc, 1e-9)

    return UncertaintyBudget(
        levels=levels,
        total_uncertainty=round(multi_unc, 4),
        dominant_stage=dominant,
        propagation_factor=round(prop_factor, 4),
    )
