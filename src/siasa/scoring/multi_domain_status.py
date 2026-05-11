from __future__ import annotations

from dataclasses import dataclass

from .domain_status import DomainStatusResult


@dataclass(frozen=True)
class MultiDomainStatusResult:
    status: str
    included_domains: list[str]
    rule_references: list[str]



def derive_multi_domain_status(
    domain_results: list[DomainStatusResult],
    optional_domain_gates: dict[str, bool] | None = None,
) -> MultiDomainStatusResult:
    gates = optional_domain_gates or {}
    included_results: list[DomainStatusResult] = []
    for result in domain_results:
        if result.domain in {"C", "E"} and not gates.get(result.domain, False):
            continue
        included_results.append(result)

    included_domains = [result.domain for result in included_results]
    core_results = [result for result in included_results if result.domain in {"A", "B", "D"}]
    if sum(1 for result in core_results if result.status == "D0") >= 2:
        return MultiDomainStatusResult("S6", included_domains, ["SwR-023", "SwR-024"])
    if any(result.status == "D5" for result in included_results):
        return MultiDomainStatusResult("S5", included_domains, ["SwR-023", "SwR-024"])

    notable = [result for result in included_results if result.status in {"D2", "D3", "D4"}]
    strong = [result for result in included_results if result.status in {"D3", "D4"}]
    very_strong = [result for result in included_results if result.status == "D4"]

    if len(strong) >= 2:
        status = "S4" if len(very_strong) >= 1 else "S3"
    elif len(notable) >= 2:
        status = "S3"
    elif len(very_strong) == 1:
        status = "S2"
    elif len(notable) == 1:
        status = "S1"
    else:
        status = "S0"

    return MultiDomainStatusResult(status, included_domains, ["SwR-023", "SwR-024"])
