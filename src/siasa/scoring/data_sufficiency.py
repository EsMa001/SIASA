from __future__ import annotations

from dataclasses import dataclass, field

from siasa.features.base import FeatureValue


@dataclass(frozen=True)
class DataSufficiencyResult:
    is_sufficient: bool
    coverage: float
    freshness_hours: float | None
    reasons: list[str] = field(default_factory=list)


def _resolve_effective_freshness_threshold(
    domain: str,
    source_id: str | None,
    fallback_hours: float,
) -> float:
    """Resolve freshness threshold via freshness_config YAML (per-source > per-domain > global).

    Falls back to ``fallback_hours`` if the config file is missing or unusable.
    Requirement trace: AP-F11, StR-129..134 (konfigurierbare Freshness-Windows).
    """
    try:
        from siasa.scoring.freshness_config import resolve_freshness_threshold
        return resolve_freshness_threshold(domain=domain, source_id=source_id)
    except Exception:
        return fallback_hours


def evaluate_data_sufficiency(
    features: list[FeatureValue],
    minimum_coverage: float = 0.6,
    maximum_freshness_hours: float = 168.0,
    minimum_feature_count: int = 2,
) -> DataSufficiencyResult:
    if len(features) < minimum_feature_count:
        return DataSufficiencyResult(False, coverage=0.0, freshness_hours=None, reasons=["too few features"])

    coverage = sum(feature.coverage for feature in features) / len(features)
    freshness_values = [feature.confidence_inputs.get("freshness_hours") for feature in features]
    freshness_hours = max(
        float(value) for value in freshness_values if isinstance(value, int | float)
    ) if any(isinstance(value, int | float) for value in freshness_values) else None

    reasons: list[str] = []
    if coverage < minimum_coverage:
        reasons.append("coverage below threshold")

    freshness_violation = False
    for feature in features:
        feature_freshness = feature.confidence_inputs.get("freshness_hours")
        if not isinstance(feature_freshness, int | float):
            continue
        feature_threshold = feature.confidence_inputs.get("freshness_horizon_hours")
        if isinstance(feature_threshold, int | float):
            resolved_threshold = float(feature_threshold)
        else:
            # Use freshness_config YAML (per-source > per-domain > global fallback)
            domain = getattr(feature, "domain", "")
            source_id = (feature.provenance_source_ids[0] if feature.provenance_source_ids else None)
            resolved_threshold = _resolve_effective_freshness_threshold(
                domain=domain,
                source_id=source_id,
                fallback_hours=maximum_freshness_hours,
            )
        if float(feature_freshness) > resolved_threshold:
            freshness_violation = True
            break
    if freshness_hours is not None and freshness_violation:
        reasons.append("freshness beyond threshold")

    return DataSufficiencyResult(
        is_sufficient=not reasons,
        coverage=coverage,
        freshness_hours=freshness_hours,
        reasons=reasons,
    )
