from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from siasa.adapters.base import SourceAdapter
from siasa.features.base import FeatureService, FeatureValue
from siasa.data.normalized_models import NormalizedRecord
from siasa.reporting.country_report import GeneratedReport
from siasa.reporting.daily_snapshot import generate_daily_snapshot_report
from siasa.scoring.domain_status import DomainStatusResult
from siasa.scoring.multi_domain_status import MultiDomainStatusResult
from siasa.snapshots.models import Snapshot
from siasa.snapshots.service import create_snapshot

from .run_state import RunState, SourceExecutionResult


Normalizer = Callable[[str, str, list[dict[str, float]]], list[NormalizedRecord]]
DomainStatusAnalyzer = Callable[[str, list[FeatureValue]], DomainStatusResult]
MultiDomainStatusAnalyzer = Callable[[list[DomainStatusResult]], MultiDomainStatusResult]


@dataclass(frozen=True)
class DailyRunResult:
    run_state: RunState
    normalized_records: list[NormalizedRecord]
    features: list[FeatureValue]
    domain_statuses: dict[str, DomainStatusResult]
    multi_domain_status: MultiDomainStatusResult
    snapshot: Snapshot
    daily_report: GeneratedReport


@dataclass
class DailyRunOrchestrator:
    adapters: list[SourceAdapter]
    normalizer: Normalizer
    feature_services: list[FeatureService]
    domain_status_analyzer: DomainStatusAnalyzer
    multi_domain_status_analyzer: MultiDomainStatusAnalyzer
    country_set_id: str
    active_domains: list[str]
    rule_versions: dict[str, str]
    algorithm_version: str
    data_version: str

    def run(self, run_id: str) -> DailyRunResult:
        run_state = RunState.start(run_id)
        normalized_records: list[NormalizedRecord] = []

        for adapter in self.adapters:
            fetch_result = adapter.fetch()
            status = "success" if fetch_result.is_success else "failed"
            run_state.record_source_result(
                SourceExecutionResult(
                    source_id=adapter.source_id,
                    status=status,
                    diagnostics=fetch_result.diagnostics,
                )
            )
            if fetch_result.is_success:
                normalized_records.extend(
                    self.normalizer(adapter.source_id, adapter.domain, fetch_result.records)
                )

        features: list[FeatureValue] = []
        for service in self.feature_services:
            features.extend(service.compute(normalized_records))

        domain_statuses: dict[str, DomainStatusResult] = {}
        for domain in self.active_domains:
            domain_features = [feature for feature in features if feature.domain == domain]
            if domain_features:
                domain_statuses[domain] = self.domain_status_analyzer(domain, domain_features)

        multi_domain_status = self.multi_domain_status_analyzer(list(domain_statuses.values()))
        country_id = normalized_records[0].country_id if normalized_records else "UNKNOWN"
        analytical_outputs = {
            "country_status": {country_id: multi_domain_status.status},
            "domain_statuses": {domain: status.status for domain, status in domain_statuses.items()},
        }
        snapshot = create_snapshot(
            run_state=run_state,
            country_set_id=self.country_set_id,
            active_domains=self.active_domains,
            rule_versions=self.rule_versions,
            analytical_outputs=analytical_outputs,
            algorithm_version=self.algorithm_version,
            data_version=self.data_version,
        )
        daily_report = generate_daily_snapshot_report(snapshot)
        return DailyRunResult(
            run_state=run_state,
            normalized_records=normalized_records,
            features=features,
            domain_statuses=domain_statuses,
            multi_domain_status=multi_domain_status,
            snapshot=snapshot,
            daily_report=daily_report,
        )
