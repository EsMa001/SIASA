from __future__ import annotations

from dataclasses import dataclass, field

from siasa.features.base import FeatureValue


@dataclass(frozen=True)
class DataSufficiencyResult:
    is_sufficient: bool
    coverage: float
    freshness_hours: float | None
    reasons: list[str] = field(default_factory=list)



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
    if freshness_hours is not None and freshness_hours > maximum_freshness_hours:
        reasons.append("freshness beyond threshold")

    return DataSufficiencyResult(
        is_sufficient=not reasons,
        coverage=coverage,
        freshness_hours=freshness_hours,
        reasons=reasons,
    )
