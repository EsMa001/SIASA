from __future__ import annotations

from dataclasses import dataclass

from .data_sufficiency import DataSufficiencyResult
from .scoring_thresholds import domain_status_cutpoints


@dataclass(frozen=True)
class DomainStatusResult:
    domain: str
    status: str
    anomaly_score: float
    drivers: list[str]
    uncertainty_indicators: list[str]
    rule_references: list[str]
    sufficiency: DataSufficiencyResult



def derive_domain_status(
    domain: str,
    anomaly_score: float,
    sufficiency: DataSufficiencyResult,
    contradictory_signals: bool = False,
) -> DomainStatusResult:
    d1_max, d2_max, d3_max = domain_status_cutpoints()
    if not sufficiency.is_sufficient:
        status = "D0"
    elif contradictory_signals:
        status = "D5"
    elif anomaly_score < d1_max:
        status = "D1"
    elif anomaly_score < d2_max:
        status = "D2"
    elif anomaly_score < d3_max:
        status = "D3"
    else:
        status = "D4"

    drivers = ["anomaly_score"] if status in {"D1", "D2", "D3", "D4"} else []
    uncertainty_indicators = list(sufficiency.reasons)
    if contradictory_signals:
        uncertainty_indicators.append("contradictory signals")

    return DomainStatusResult(
        domain=domain,
        status=status,
        anomaly_score=anomaly_score,
        drivers=drivers,
        uncertainty_indicators=uncertainty_indicators,
        rule_references=["SwR-021", "SwR-022"],
        sufficiency=sufficiency,
    )
