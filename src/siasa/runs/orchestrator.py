from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from siasa.adapters.base import SourceAdapter
from siasa.adapters.fetch_metadata import FetchMetadataRecord
from siasa.annotations.models import AnnotationRecord
from siasa.features.base import FeatureService, FeatureValue
from siasa.data.normalized_models import NormalizedRecord
from siasa.data.raw_models import RawRecord
from siasa.reporting.country_report import GeneratedReport, generate_country_report
from siasa.reporting.daily_snapshot import generate_daily_snapshot_report
from siasa.governance.roles import validate_source_governance_metadata
from siasa.scoring.domain_status import DomainStatusResult
from siasa.scoring.multi_domain_status import MultiDomainStatusResult
from siasa.snapshots.models import Snapshot
from siasa.snapshots.service import create_snapshot
from siasa.traceability.lineage import LineageRecord, build_lineage_record

from .run_state import RunState, SourceExecutionResult

if TYPE_CHECKING:
    from .artifacts import RunArtifactBundle


Normalizer = Callable[[str, str, list[dict[str, float]]], list[NormalizedRecord]]
DomainStatusAnalyzer = Callable[[str, list[FeatureValue]], DomainStatusResult]
MultiDomainStatusAnalyzer = Callable[[list[DomainStatusResult]], MultiDomainStatusResult]


@dataclass(frozen=True)
class FailureArtifact:
    run_id: str
    reason: str
    failed_sources: list[str]
    diagnostics_by_source: dict[str, str]


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
    failure_artifact: FailureArtifact | None
    snapshot: Snapshot | None
    daily_report: GeneratedReport
    country_reports: dict[str, GeneratedReport]
    artifact_bundle: RunArtifactBundle | None = None


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
    source_records: dict[str, dict[str, str]] | None = None
    annotation_records: list[AnnotationRecord] | None = None
    artifacts_output_dir: Path | None = None
    baseline_mode: str = "Combined 30/90/365"

    def run(self, run_id: str) -> DailyRunResult:
        run_state = RunState.start(run_id)
        governance_failure = self._validate_active_sources(run_id)
        if governance_failure is not None:
            return DailyRunResult(
                run_state=RunState(run_id=run_id, status="failed"),
                fetch_metadata_records=[],
                raw_records=[],
                normalized_records=[],
                features=[],
                domain_statuses={},
                multi_domain_status=MultiDomainStatusResult("S6", [], ["SwR-023", "SwR-024"]),
                lineage_records=[],
                failure_artifact=governance_failure,
                snapshot=None,
                daily_report=self._build_failure_report(governance_failure),
                country_reports={},
                artifact_bundle=None,
            )

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

        failure_reason: str | None = None
        if run_state.status == "failed":
            failure_reason = "all_sources_failed"
        elif not normalized_records:
            run_state.status = "failed"
            failure_reason = "no_data_after_fetch"
        elif not features:
            run_state.status = "failed"
            failure_reason = "no_features_computed"

        if failure_reason is not None:
            failure_artifact = self._build_failure_artifact(run_state, failure_reason)
            daily_report = self._build_failure_report(failure_artifact)
            return DailyRunResult(
                run_state=run_state,
                fetch_metadata_records=fetch_metadata_records,
                raw_records=raw_records,
                normalized_records=normalized_records,
                features=features,
                domain_statuses=domain_statuses,
                multi_domain_status=MultiDomainStatusResult("S6", [], ["SwR-023", "SwR-024"]),
                lineage_records=[],
                failure_artifact=failure_artifact,
                snapshot=None,
                daily_report=daily_report,
                country_reports={},
                artifact_bundle=None,
            )

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
        artifact_bundle = None
        if self.artifacts_output_dir is not None:
            from .artifacts import write_run_artifacts

            artifact_bundle = write_run_artifacts(
                output_dir=self.artifacts_output_dir,
                run_state=run_state,
                fetch_metadata_records=fetch_metadata_records,
                normalized_records=normalized_records,
                features=features,
                domain_statuses=domain_statuses,
                lineage_records=lineage_records,
                snapshot=snapshot,
                daily_report=daily_report,
                country_reports=country_reports,
                annotation_records=self.annotation_records or [],
                baseline_mode=self.baseline_mode,
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
            failure_artifact=None,
            snapshot=snapshot,
            daily_report=daily_report,
            country_reports=country_reports,
            artifact_bundle=artifact_bundle,
        )

    def _validate_active_sources(self, run_id: str) -> FailureArtifact | None:
        if not self.source_records:
            return None

        invalid_sources: list[str] = []
        diagnostics_by_source: dict[str, str] = {}
        for adapter in self.adapters:
            source_record = self.source_records.get(adapter.source_id)
            try:
                validate_source_governance_metadata(source_record or {})
            except ValueError as exc:
                invalid_sources.append(adapter.source_id)
                diagnostics_by_source[adapter.source_id] = str(exc)

        if not invalid_sources:
            return None

        return FailureArtifact(
            run_id=run_id,
            reason="source_governance_invalid",
            failed_sources=invalid_sources,
            diagnostics_by_source=diagnostics_by_source,
        )

    def _build_failure_artifact(self, run_state: RunState, reason: str) -> FailureArtifact:
        diagnostics_by_source = {
            result.source_id: result.diagnostics
            for result in run_state.source_results
            if result.diagnostics
        }
        return FailureArtifact(
            run_id=run_state.run_id,
            reason=reason,
            failed_sources=run_state.failed_sources,
            diagnostics_by_source=diagnostics_by_source,
        )

    def _build_failure_report(self, failure_artifact: FailureArtifact) -> GeneratedReport:
        payload = {
            "run_id": failure_artifact.run_id,
            "status": "failed",
            "failure_reason": failure_artifact.reason,
            "failed_sources": failure_artifact.failed_sources,
            "diagnostics_by_source": failure_artifact.diagnostics_by_source,
        }
        markdown = "\n".join(
            [
                "# Failed Daily Run",
                f"Run ID: {failure_artifact.run_id}",
                f"Reason: {failure_artifact.reason}",
                f"Failed sources: {', '.join(failure_artifact.failed_sources) if failure_artifact.failed_sources else '-'}",
            ]
        )
        return GeneratedReport(
            report_id=f"REP-FAIL-{failure_artifact.run_id}",
            report_type="failed_run",
            markdown=markdown,
            json_payload=payload,
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
