from siasa.scoring.data_sufficiency import DataSufficiencyResult
from siasa.scoring.domain_status import derive_domain_status


def test_domain_status_engine_covers_d0_to_d5_with_explanations() -> None:
    insufficient = DataSufficiencyResult(is_sufficient=False, coverage=0.2, freshness_hours=240, reasons=["coverage below threshold"])
    contradictory = DataSufficiencyResult(is_sufficient=True, coverage=0.8, freshness_hours=24, reasons=[])
    sufficient = DataSufficiencyResult(is_sufficient=True, coverage=0.8, freshness_hours=24, reasons=[])

    d0 = derive_domain_status("A", anomaly_score=0.0, sufficiency=insufficient)
    d1 = derive_domain_status("A", anomaly_score=0.1, sufficiency=sufficient)
    d2 = derive_domain_status("A", anomaly_score=0.3, sufficiency=sufficient)
    d3 = derive_domain_status("A", anomaly_score=0.7, sufficiency=sufficient)
    d4 = derive_domain_status("A", anomaly_score=1.2, sufficiency=sufficient)
    d5 = derive_domain_status("A", anomaly_score=0.7, sufficiency=contradictory, contradictory_signals=True)

    assert d0.status == "D0"
    assert d1.status == "D1"
    assert d2.status == "D2"
    assert d3.status == "D3"
    assert d4.status == "D4"
    assert d5.status == "D5"
    assert d4.drivers == ["anomaly_score"]
    assert d0.uncertainty_indicators == ["coverage below threshold"]
    assert d3.rule_references == ["SwR-021", "SwR-022"]
