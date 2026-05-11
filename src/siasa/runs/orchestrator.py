from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from siasa.adapters.base import SourceAdapter
from siasa.adapters.fetch_metadata import FetchMetadataRecord
from siasa.features.base import FeatureService, FeatureValue
from siasa.data.normalized_models import NormalizedRecord
from siasa.data.raw_models import RawRecord
from siasa.reporting.country_report import GeneratedReport, generate_country_report
from siasa.reporting.daily_snapshot import generate_daily_snapshot_report
from siasa.scoring.domain_status import DomainStatusResult
from siasa.scoring.multi_domain_status import MultiDomainStatusResult
from siasa.snapshots.models import Snapshot
from siasa.snapshots.service import create_snapshot
from siasa.traceability.lineage import LineageRecord, build_lineage_record

from .run_state import RunState, SourceExecutionResult


Normalizer = Callable[[str, str, list[dict[str, float]]], list[NormalizedRecord]]
DomainStatusAnalyzer = Callable[[str, list[FeatureValue]], DomainStatusResult]
MultiDomainStatusAnalyzer = Callable[[list[DomainStatusResult]], MultiDomainStatusResult]


@dataclass(frozen=True)
class DailyRunResult:
    run_state: RunState
    fetch_metadata_records: list[FetchMetadataRecord]
    raw_records: list[RawRecord]
    normalized_records: list[NormalizedRecord]
    features: list[FeatureValue]
    domain_statuses: dict[str, DomainStatusResult]
    multi_domain_status: MultiDomainStatusResult
    lineage_records: list[LineageRecord]
    snapshot: Snapshot
    daily_report: GeneratedReport
    country_reports: dict[str, GeneratedReport]


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
        fetch_metadata_records: list[FetchMetadataRecord] = []
        raw_records: list[RawRecord] = []
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
            fetch_metadata_records.append(
                FetchMetadataRecord(
                    source_id=adapter.source_id,
                    fetch_status=status,
                    fetched_at=run_id,
                    diagnostics=fetch_result.diagnostics,
                    record_count=len(fetch_result.records),
                )
            )
            if fetch_result.is_success:
                for index, record in enumerate(fetch_result.records, start=1):
                    raw_records.append(
                        RawRecord(
                            raw_record_id=f"RAW-{adapter.source_id}-{index}",
                            source_id=adapter.source_id,
                            fetched_at=run_id,
                            storage_mode="payload",
                            raw_payload=record,
                        )
                    )
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
        country_reports = self._build_country_reports(
            run_state=run_state,
            country_id=country_id,
            features=features,
            domain_statuses=domain_statuses,
            multi_domain_status=multi_domain_status,
        )
        lineage_records = self._build_lineage_records(
            raw_records=raw_records,
            normalized_records=normalized_records,
            features=features,
            domain_statuses=domain_statuses,
            snapshot=snapshot,
            report=daily_report,
        )
        return DailyRunResult(
            run_state=run_state,
            fetch_metadata_records=fetch_metadata_records,
            raw_records=raw_records,
            normalized_records=normalized_records,
            features=features,
            domain_statuses=domain_statuses,
            multi_domain_status=multi_domain_status,
            lineage_records=lineage_records,
            snapshot=snapshot,
            daily_report=daily_report,
            country_reports=country_reports,
        )

    def _build_country_reports(
        self,
        run_state: RunState,
        country_id: str,
        features: list[FeatureValue],
        domain_statuses: dict[str, DomainStatusResult],
        multi_domain_status: MultiDomainStatusResult,
    ) -> dict[str, GeneratedReport]:
        if country_id == "UNKNOWN":
            return {}

        drivers = sorted(feature.feature_id for feature in features)
        domain_states = {domain: status.status for domain, status in domain_statuses.items()}
        coverage = sum(feature.coverage for feature in features) / len(features) if features else 0.0
        uncertainty: list[str] = []
        if run_state.status == "partial_success":
            uncertainty.append("partial_success")
        if run_state.failed_sources:
            uncertainty.append(f"failed_sources:{','.join(run_state.failed_sources)}")

        report = generate_country_report(
            country_id=country_id,
            multi_domain_status=multi_domain_status.status,
            domain_states=domain_states,
            drivers=drivers,
            counter_indicators=[],
            coverage=coverage,
            uncertainty=uncertainty,
            linked_events=[],
        )
        return {country_id: report}

    def _build_lineage_records(
        self,
        raw_records: list[RawRecord],
        normalized_records: list[NormalizedRecord],
        features: list[FeatureValue],
        domain_statuses: dict[str, DomainStatusResult],
        snapshot: Snapshot,
        report: GeneratedReport,
    ) -> list[LineageRecord]:
        raw_by_source: dict[str, list[RawRecord]] = {}
        for raw_record in raw_records:
            raw_by_source.setdefault(raw_record.source_id, []).append(raw_record)

        normalized_by_source: dict[str, list[NormalizedRecord]] = {}
        for normalized_record in normalized_records:
            normalized_by_source.setdefault(normalized_record.provenance_source_id, []).append(normalized_record)

        lineage_records: list[LineageRecord] = []
        for feature in features:
            source_id = feature.provenance_source_ids[0]
            raw_record = raw_by_source[source_id][0]
            normalized_record = normalized_by_source[source_id][0]
            domain_status = domain_statuses.get(feature.domain)
            lineage_records.append(
                build_lineage_record(
                    source_id=source_id,
                    raw_record_id=raw_record.raw_record_id,
                    normalized_id=normalized_record.normalized_id,
                    feature_id=feature.feature_id,
                    domain_status_id=f"DST-{feature.country_id}-{feature.domain}-{snapshot.run_id}",
                    multi_domain_status_id=f"MST-{feature.country_id}-{snapshot.run_id}",
                    snapshot_id=snapshot.snapshot_id,
                    report_id=report.report_id,
                )
            )
        return lineage_records
