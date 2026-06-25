from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

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

from .run_gate import build_analytical_completeness, record_degradation
from .run_state import RunState, SourceExecutionResult

if TYPE_CHECKING:
    from .artifacts import RunArtifactBundle

logger = logging.getLogger(__name__)


Normalizer = Callable[[str, str, list[dict[str, float]]], list[NormalizedRecord]]
DomainStatusAnalyzer = Callable[[str, list[FeatureValue], list[NormalizedRecord]], DomainStatusResult]
MultiDomainStatusAnalyzer = Callable[[list[DomainStatusResult], dict[str, bool] | None], MultiDomainStatusResult]
ValidationViewModelBuilder = Callable[
    [
        str,
        list[str],
        RunState,
        list[NormalizedRecord],
        dict[str, dict[str, DomainStatusResult]],
        dict[str, MultiDomainStatusResult],
        Snapshot,
    ],
    dict[str, object] | None,
]


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
    country_domain_statuses: dict[str, dict[str, DomainStatusResult]]
    multi_domain_status: MultiDomainStatusResult
    country_multi_domain_statuses: dict[str, MultiDomainStatusResult]
    lineage_records: list[LineageRecord]
    failure_artifact: FailureArtifact | None
    snapshot: Snapshot | None
    daily_report: GeneratedReport
    country_reports: dict[str, GeneratedReport]
    artifact_bundle: RunArtifactBundle | None = None
    rule_evaluation_results: list[Any] = field(default_factory=list)
    fusion_results: dict[str, Any] = field(default_factory=dict)
    bayesian_estimates: dict[str, dict[str, Any]] = field(default_factory=dict)
    uncertainty_budgets: dict[str, Any] = field(default_factory=dict)
    dependency_graph_result: Any = None
    provenance_chain_result: Any = None
    spread_paths_result: list[Any] = field(default_factory=list)
    amplification_result: list[Any] = field(default_factory=list)
    analytical_completeness: dict[str, Any] = field(default_factory=dict)



def _adapter_country_scope(adapter: SourceAdapter) -> list[str] | None:
    if hasattr(adapter, "country_ids"):
        country_ids = getattr(adapter, "country_ids")
        if country_ids is None:
            return None
        if isinstance(country_ids, dict):
            return sorted(str(country_id).upper() for country_id in country_ids.keys())
        return sorted(str(country_id).upper() for country_id in country_ids)
    if hasattr(adapter, "country_queries"):
        country_queries = getattr(adapter, "country_queries")
        if isinstance(country_queries, dict):
            return sorted(str(country_id).upper() for country_id in country_queries.keys())
    if hasattr(adapter, "country_codes"):
        country_codes = getattr(adapter, "country_codes")
        if isinstance(country_codes, dict):
            return sorted(str(country_id).upper() for country_id in country_codes.keys())
    return None



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
    validation_view_model_builder: ValidationViewModelBuilder | None = None
    requested_country_ids: tuple[str, ...] | None = None
    country_expected_domains: dict[str, list[str]] | None = None
    source_activation_readiness: list[dict[str, object]] | None = None

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
                country_domain_statuses={},
                multi_domain_status=MultiDomainStatusResult("S6", [], ["SwR-023", "SwR-024"]),
                country_multi_domain_statuses={},
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

        country_domain_statuses: dict[str, dict[str, DomainStatusResult]] = {}
        for country_id in sorted({feature.country_id for feature in features}):
            per_country_statuses: dict[str, DomainStatusResult] = {}
            for domain in self.active_domains:
                domain_features = [
                    feature for feature in features if feature.country_id == country_id and feature.domain == domain
                ]
                if domain_features:
                    domain_records = [
                        record
                        for record in normalized_records
                        if record.country_id == country_id and record.domain == domain
                    ]
                    per_country_statuses[domain] = self.domain_status_analyzer(domain, domain_features, domain_records)
            if per_country_statuses:
                country_domain_statuses[country_id] = per_country_statuses

        primary_country_id = normalized_records[0].country_id if normalized_records else "UNKNOWN"
        domain_statuses = country_domain_statuses.get(primary_country_id, {})

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
                country_domain_statuses=country_domain_statuses,
                multi_domain_status=MultiDomainStatusResult("S6", [], ["SwR-023", "SwR-024"]),
                country_multi_domain_statuses={},
                lineage_records=[],
                failure_artifact=failure_artifact,
                snapshot=None,
                daily_report=daily_report,
                country_reports={},
                artifact_bundle=None,
            )

        country_multi_domain_statuses = {}
        for country_id, per_country_statuses in sorted(country_domain_statuses.items()):
            # Enable C/E domain gates when features exist for this country (StR-247..250)
            optional_gates = {
                "C": "C" in per_country_statuses,
                "E": "E" in per_country_statuses,
            }
            country_multi_domain_statuses[country_id] = self.multi_domain_status_analyzer(
                list(per_country_statuses.values()),
                optional_gates,
            )
        multi_domain_status = country_multi_domain_statuses.get(
            primary_country_id,
            self.multi_domain_status_analyzer(list(domain_statuses.values())),
        )
        analytical_outputs = {
            "country_status": {
                country_id: result.status for country_id, result in sorted(country_multi_domain_statuses.items())
            },
            "domain_statuses": {domain: status.status for domain, status in domain_statuses.items()},
        }

        # --- Phase 4-6 analytical modules ---
        rule_evaluation_results: list[Any] = []
        fusion_results: dict[str, Any] = {}
        bayesian_estimates: dict[str, dict[str, Any]] = {}
        uncertainty_budgets: dict[str, Any] = {}
        analytical_degradations: list[dict[str, Any]] = []

        # (a) Rule engine evaluation
        try:
            from siasa.scoring.rule_engine import load_assessment_rules, evaluate_rules, AssessmentContext
            rules_path = Path(__file__).resolve().parents[3] / "vmodel" / "project" / "assessment_rules.yaml"
            if rules_path.exists():
                rules = load_assessment_rules(rules_path)
                contexts = []
                for cid, per_country_statuses in country_domain_statuses.items():
                    mds = country_multi_domain_statuses.get(cid)
                    mds_status = mds.status if mds else ""
                    for dom, ds in per_country_statuses.items():
                        contexts.append(AssessmentContext(
                            country_id=cid,
                            domain=dom,
                            domain_status=ds.status,
                            anomaly_score=ds.anomaly_score,
                            multi_domain_status=mds_status,
                        ))
                rule_evaluation_results = evaluate_rules(rules, contexts)
        except ImportError:
            logger.debug("Rule engine dependencies not available, skipping rule evaluation")
        except Exception as exc:
            logger.exception("Rule evaluation failed, continuing with empty results")
            record_degradation(analytical_degradations, "rule_engine", exc)

        # (b) Cross-domain fusion
        try:
            from siasa.scoring.cross_domain_fusion import fuse_domain_evidence
            for cid, per_country_statuses in country_domain_statuses.items():
                fusion_results[cid] = fuse_domain_evidence(list(per_country_statuses.values()))
        except ImportError:
            logger.debug("Cross-domain fusion module not available, skipping")
        except Exception as exc:
            logger.exception("Cross-domain fusion failed, continuing with empty results")
            record_degradation(analytical_degradations, "cross_domain_fusion", exc)

        # (c) Probabilistic (Bayesian) scoring
        try:
            from siasa.scoring.probabilistic import compute_bayesian_status
            for cid, per_country_statuses in country_domain_statuses.items():
                bayesian_estimates[cid] = {}
                for dom, ds in per_country_statuses.items():
                    bayesian_estimates[cid][dom] = compute_bayesian_status(
                        anomaly_score=ds.anomaly_score,
                    )
        except ImportError:
            logger.debug("Probabilistic scoring module not available, skipping")
        except Exception as exc:
            logger.exception("Probabilistic scoring failed, continuing with empty results")
            record_degradation(analytical_degradations, "probabilistic", exc)

        # (d) Uncertainty propagation
        try:
            from siasa.scoring.uncertainty_propagation import propagate_uncertainty
            for cid in country_domain_statuses:
                country_features_for_unc = [f for f in features if f.country_id == cid]
                if country_features_for_unc:
                    source_uncertainties = [
                        (f.coverage, 1.0 - f.coverage) for f in country_features_for_unc
                    ]
                    uncertainty_budgets[cid] = propagate_uncertainty(source_uncertainties)
        except ImportError:
            logger.debug("Uncertainty propagation module not available, skipping")
        except Exception as exc:
            logger.exception("Uncertainty propagation failed, continuing with empty results")
            record_degradation(analytical_degradations, "uncertainty_propagation", exc)

        # (e) Dependency graph — source co-occurrence across countries/domains
        dependency_graph_result: Any = None
        try:
            from siasa.analysis.dependency_graph import DependencyEdge, build_dependency_graph
            dep_edges: list[Any] = []
            # Build edges from features: sources that both contribute to the same country/domain
            # are considered dependent (implicit co-occurrence coupling)
            source_pairs_seen: set[tuple[str, str]] = set()
            for feat in features:
                src_ids = list(feat.provenance_source_ids)
                for i in range(len(src_ids)):
                    for j in range(i + 1, len(src_ids)):
                        pair = (src_ids[i], src_ids[j])
                        if pair not in source_pairs_seen:
                            source_pairs_seen.add(pair)
                            dep_edges.append(DependencyEdge(
                                source_from=src_ids[i],
                                source_to=src_ids[j],
                                weight=1.0,
                            ))
            if dep_edges:
                dependency_graph_result = build_dependency_graph(dep_edges)
        except ImportError:
            logger.debug("Dependency graph module not available, skipping")
        except Exception as exc:
            logger.exception("Dependency graph failed, continuing with empty result")
            record_degradation(analytical_degradations, "dependency_graph", exc)

        # (f) Provenance graph — build from lineage records after they are computed
        # NOTE: lineage_records are computed later in the pipeline; we store a builder
        # and call it after lineage is built. Placeholder here — wired after lineage below.
        provenance_chain_result: Any = None

        # (g) Information epidemiology — signal spread across sources from normalized records
        spread_paths_result: list[Any] = []
        amplification_result: list[Any] = []
        try:
            from siasa.analysis.info_epidemiology import (
                SpreadObservation,
                detect_spread_paths,
                detect_amplification,
            )
            observations: list[Any] = []
            for rec in normalized_records:
                # Use freshness_hours as proxy for observed_at_hours (relative age)
                freshness = rec.quality_context.get("freshness_hours")
                if isinstance(freshness, (int, float)):
                    observations.append(SpreadObservation(
                        source_id=rec.provenance_source_id,
                        signal_key=rec.signal_key,
                        observed_at_hours=float(freshness),
                        value=float(rec.value) if rec.value is not None else 0.0,
                    ))
            if len(observations) >= 2:
                spread_paths_result = detect_spread_paths(observations)
                amplification_result = detect_amplification(observations)
        except ImportError:
            logger.debug("Info epidemiology module not available, skipping")
        except Exception as exc:
            logger.exception("Info epidemiology failed, continuing with empty results")
            record_degradation(analytical_degradations, "info_epidemiology", exc)

        snapshot_rule_versions = dict(self.rule_versions)
        for normalized_record in normalized_records:
            mapping_version = normalized_record.quality_context.get("mapping_version")
            if mapping_version is None:
                continue
            snapshot_rule_versions[f"normalization:{normalized_record.provenance_source_id}"] = str(mapping_version)
        snapshot = create_snapshot(
            run_state=run_state,
            country_set_id=self.country_set_id,
            active_domains=self.active_domains,
            rule_versions=snapshot_rule_versions,
            analytical_outputs=analytical_outputs,
            algorithm_version=self.algorithm_version,
            data_version=self.data_version,
        )
        daily_report = generate_daily_snapshot_report(snapshot)
        country_reports: dict[str, GeneratedReport] = {}
        for country_id, per_country_multi_domain_status in sorted(country_multi_domain_statuses.items()):
            country_reports.update(
                self._build_country_reports(
                    run_state=run_state,
                    country_id=country_id,
                    features=[feature for feature in features if feature.country_id == country_id],
                    normalized_records=[record for record in normalized_records if record.country_id == country_id],
                    domain_statuses=country_domain_statuses.get(country_id, {}),
                    multi_domain_status=per_country_multi_domain_status,
                )
            )
        lineage_records = self._build_lineage_records(
            raw_records=raw_records,
            normalized_records=normalized_records,
            features=features,
            domain_statuses=domain_statuses,
            snapshot=snapshot,
            report=daily_report,
            country_reports=country_reports,
        )

        # (f) Provenance graph — built from lineage records now available
        try:
            from siasa.analysis.provenance_graph import ProvenanceNode, ProvenanceEdge, build_provenance_chain
            prov_nodes: list[Any] = []
            prov_edges: list[Any] = []
            for lr in lineage_records:
                prov_nodes.append(ProvenanceNode(node_id=lr.source_id, stage="source", run_id=run_state.run_id))
                prov_nodes.append(ProvenanceNode(node_id=lr.normalized_id, stage="normalized", run_id=run_state.run_id))
                prov_nodes.append(ProvenanceNode(node_id=lr.feature_id, stage="feature", run_id=run_state.run_id))
                prov_nodes.append(ProvenanceNode(node_id=lr.domain_status_id, stage="domain_score", run_id=run_state.run_id))
                prov_nodes.append(ProvenanceNode(node_id=lr.multi_domain_status_id, stage="multi_domain", run_id=run_state.run_id))
                prov_edges.append(ProvenanceEdge(from_node=lr.source_id, to_node=lr.normalized_id, transform="fetch"))
                prov_edges.append(ProvenanceEdge(from_node=lr.normalized_id, to_node=lr.feature_id, transform="extract"))
                prov_edges.append(ProvenanceEdge(from_node=lr.feature_id, to_node=lr.domain_status_id, transform="score"))
                prov_edges.append(ProvenanceEdge(from_node=lr.domain_status_id, to_node=lr.multi_domain_status_id, transform="fuse"))
            # Deduplicate nodes by node_id
            seen_node_ids: set[str] = set()
            unique_prov_nodes = []
            for n in prov_nodes:
                if n.node_id not in seen_node_ids:
                    seen_node_ids.add(n.node_id)
                    unique_prov_nodes.append(n)
            if unique_prov_nodes:
                provenance_chain_result = build_provenance_chain(unique_prov_nodes, prov_edges)
        except ImportError:
            logger.debug("Provenance graph module not available, skipping")
        except Exception as exc:
            logger.exception("Provenance graph failed, continuing with empty result")
            record_degradation(analytical_degradations, "provenance_graph", exc)
        artifact_bundle = None
        validation_view_model = None
        validation_artifact_reason = "not_configured"
        if self.validation_view_model_builder is not None:
            validation_view_model = self.validation_view_model_builder(
                primary_country_id,
                list(self.active_domains),
                run_state,
                normalized_records,
                country_domain_statuses,
                country_multi_domain_statuses,
                snapshot,
            )
            validation_artifact_reason = None if validation_view_model is not None else "no_usable_input_data"
        analytical_completeness = build_analytical_completeness(analytical_degradations)
        artifact_status = {
            "validation_backtest": {
                "status": "present" if validation_view_model is not None else "absent",
                "reason": validation_artifact_reason,
            },
            "traceability_lineage": {"status": "present", "reason": None},
            "repo_closure": {"status": "present", "reason": None},
            "annotations": {"status": "present", "reason": None},
            "analytical_completeness": {
                "status": analytical_completeness["status"],
                "reason": (
                    None
                    if analytical_completeness["status"] == "complete"
                    else "degraded_stages:" + ",".join(analytical_completeness["degraded_stages"])
                ),
            },
        }
        if self.artifacts_output_dir is not None:
            from .artifacts import write_run_artifacts

            artifact_bundle = write_run_artifacts(
                output_dir=self.artifacts_output_dir,
                run_state=run_state,
                fetch_metadata_records=fetch_metadata_records,
                raw_records=raw_records,
                normalized_records=normalized_records,
                features=features,
                domain_statuses=domain_statuses,
                country_domain_statuses=country_domain_statuses,
                lineage_records=lineage_records,
                snapshot=snapshot,
                daily_report=daily_report,
                country_reports=country_reports,
                annotation_records=self.annotation_records or [],
                baseline_mode=self.baseline_mode,
                validation_view_model=validation_view_model,
                artifact_status=artifact_status,
                source_domain_by_source={adapter.source_id: adapter.domain for adapter in self.adapters},
                source_countries_by_source={adapter.source_id: _adapter_country_scope(adapter) for adapter in self.adapters},
                source_activation_readiness=list(self.source_activation_readiness or []),
                requested_country_ids=list(self.requested_country_ids or []),
                country_expected_domains=dict(self.country_expected_domains or {}),
                rule_evaluation_results=rule_evaluation_results,
                fusion_results=fusion_results,
                bayesian_estimates=bayesian_estimates,
                uncertainty_budgets=uncertainty_budgets,
                dependency_graph_result=dependency_graph_result,
                provenance_chain_result=provenance_chain_result,
                spread_paths_result=spread_paths_result,
                amplification_result=amplification_result,
            )

        return DailyRunResult(
            run_state=run_state,
            fetch_metadata_records=fetch_metadata_records,
            raw_records=raw_records,
            normalized_records=normalized_records,
            features=features,
            domain_statuses=domain_statuses,
            country_domain_statuses=country_domain_statuses,
            multi_domain_status=multi_domain_status,
            country_multi_domain_statuses=country_multi_domain_statuses,
            lineage_records=lineage_records,
            failure_artifact=None,
            snapshot=snapshot,
            daily_report=daily_report,
            country_reports=country_reports,
            artifact_bundle=artifact_bundle,
            rule_evaluation_results=rule_evaluation_results,
            fusion_results=fusion_results,
            bayesian_estimates=bayesian_estimates,
            uncertainty_budgets=uncertainty_budgets,
            dependency_graph_result=dependency_graph_result,
            provenance_chain_result=provenance_chain_result,
            spread_paths_result=spread_paths_result,
            amplification_result=amplification_result,
            analytical_completeness=analytical_completeness,
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
        normalized_records: list[NormalizedRecord],
        domain_statuses: dict[str, DomainStatusResult],
        multi_domain_status: MultiDomainStatusResult,
    ) -> dict[str, GeneratedReport]:
        if country_id == "UNKNOWN":
            return {}

        drivers = sorted(feature.feature_id for feature in features)
        domain_states = {domain: status.status for domain, status in domain_statuses.items()}
        coverage = sum(feature.coverage for feature in features) / len(features) if features else 0.0
        linked_events = [f"EVT-{country_id}-{run_state.run_id}"] if any(
            record.country_id == country_id and record.domain == "B" and "event" in record.signal_key
            for record in normalized_records
        ) else []
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
            linked_events=linked_events,
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
        country_reports: dict[str, GeneratedReport],
    ) -> list[LineageRecord]:
        raw_by_source_and_country: dict[tuple[str, str], list[RawRecord]] = {}
        raw_by_source: dict[str, list[RawRecord]] = {}
        for raw_record in raw_records:
            raw_by_source.setdefault(raw_record.source_id, []).append(raw_record)
            country_id = str(raw_record.raw_payload.get("country_id") or "UNKNOWN")
            raw_by_source_and_country.setdefault((raw_record.source_id, country_id), []).append(raw_record)

        normalized_by_source_and_country: dict[tuple[str, str], list[NormalizedRecord]] = {}
        for normalized_record in normalized_records:
            normalized_by_source_and_country.setdefault(
                (normalized_record.provenance_source_id, normalized_record.country_id), []
            ).append(normalized_record)

        lineage_records: list[LineageRecord] = []
        for feature in features:
            source_id = feature.provenance_source_ids[0]
            raw_record = (
                raw_by_source_and_country.get((source_id, feature.country_id)) or raw_by_source[source_id]
            )[0]
            normalized_record = normalized_by_source_and_country[(source_id, feature.country_id)][0]
            domain_status = domain_statuses.get(feature.domain)
            country_report = country_reports.get(feature.country_id)
            source_normalized_records = normalized_by_source_and_country.get((source_id, feature.country_id), [])
            report_ids = [
                report.report_id,
                f"REP-COVERAGE-{snapshot.run_id}",
                f"REP-DOMAIN-{feature.country_id}-{feature.domain}",
            ]
            if country_report is not None:
                report_ids.append(country_report.report_id)
            if (
                feature.domain == "B"
                and "event" in feature.feature_id
                and any(record.domain == "B" and "event" in record.signal_key for record in source_normalized_records)
            ):
                report_ids.append(f"REP-EVENT-EVT-{feature.country_id}-{snapshot.run_id}")
            lineage_records.append(
                build_lineage_record(
                    source_id=source_id,
                    raw_record_id=raw_record.raw_record_id,
                    normalized_id=normalized_record.normalized_id,
                    feature_id=feature.feature_id,
                    domain_status_id=f"DST-{feature.country_id}-{feature.domain}-{snapshot.run_id}",
                    multi_domain_status_id=f"MST-{feature.country_id}-{snapshot.run_id}",
                    snapshot_id=snapshot.snapshot_id,
                    observed_at=raw_record.fetched_at,
                    report_id=report.report_id,
                    report_ids=sorted(set(report_ids)),
                )
            )
        return lineage_records
