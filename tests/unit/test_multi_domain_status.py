from siasa.scoring.data_sufficiency import DataSufficiencyResult
from siasa.scoring.domain_status import DomainStatusResult
from siasa.scoring.multi_domain_status import derive_multi_domain_status


SUFFICIENT = DataSufficiencyResult(is_sufficient=True, coverage=0.9, freshness_hours=24, reasons=[])
INSUFFICIENT = DataSufficiencyResult(is_sufficient=False, coverage=0.3, freshness_hours=240, reasons=["insufficient"])


def _domain(domain: str, status: str, sufficiency: DataSufficiencyResult = SUFFICIENT) -> DomainStatusResult:
    return DomainStatusResult(
        domain=domain,
        status=status,
        anomaly_score=0.0,
        drivers=["test"],
        uncertainty_indicators=list(sufficiency.reasons),
        rule_references=["SwR-023"],
        sufficiency=sufficiency,
    )


def test_multi_domain_status_engine_covers_s0_to_s6() -> None:
    assert derive_multi_domain_status([_domain("A", "D1"), _domain("B", "D1"), _domain("D", "D1")]).status == "S0"
    assert derive_multi_domain_status([_domain("A", "D2"), _domain("B", "D1"), _domain("D", "D1")]).status == "S1"
    assert derive_multi_domain_status([_domain("A", "D4"), _domain("B", "D1"), _domain("D", "D1")]).status == "S2"
    assert derive_multi_domain_status([_domain("A", "D3"), _domain("B", "D2"), _domain("D", "D1")]).status == "S3"
    assert derive_multi_domain_status([_domain("A", "D3"), _domain("B", "D4"), _domain("D", "D1")]).status == "S4"
    assert derive_multi_domain_status([_domain("A", "D5"), _domain("B", "D1"), _domain("D", "D1")]).status == "S5"
    assert derive_multi_domain_status([_domain("A", "D0", INSUFFICIENT), _domain("B", "D0", INSUFFICIENT), _domain("D", "D1")]).status == "S6"


def test_multi_domain_status_excludes_c_and_e_without_sufficiency_gate() -> None:
    result = derive_multi_domain_status(
        [_domain("A", "D1"), _domain("B", "D1"), _domain("D", "D1"), _domain("C", "D4")],
        optional_domain_gates={"C": False, "E": False},
    )

    assert result.status == "S0"
    assert result.included_domains == ["A", "B", "D"]
