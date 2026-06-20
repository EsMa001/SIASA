from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from siasa.adapters.fetch_metadata import FetchMetadataRecord
from siasa.annotations.models import AnnotationRecord
from siasa.catalog import load_country_set
from siasa.data.normalized_models import NormalizedRecord
from siasa.features.base import FeatureValue
from siasa.readmodels.annotations import build_annotations_view_model
from siasa.readmodels.country_profile import build_country_profile_read_model
from siasa.readmodels.domain_detail import build_domain_detail_read_model
from siasa.readmodels.readiness import build_readiness_view_model
from siasa.readmodels.approval_lifecycle import (
    build_default_approval_lifecycle_record,
    build_approval_lifecycle_view_model,
    load_approval_lifecycle_record,
)
from siasa.readmodels.release_demo_package import build_release_demo_package_view_model
from siasa.readmodels.release_evidence import build_repo_release_gate_assessment
from siasa.readmodels.release_gate import build_release_gate_view_model
from siasa.readmodels.source_coverage import build_source_coverage_read_model
from siasa.readmodels.stakeholder_functional_closure import build_stakeholder_functional_closure_report
from siasa.readmodels.system_status import build_system_status_read_model
from siasa.readmodels.world_map import build_world_map_read_model
from siasa.reporting.country_report import GeneratedReport
from siasa.reporting.manual_reports import generate_coverage_report, generate_domain_report, generate_event_report
from siasa.runs.run_state import RunState
from siasa.scoring.domain_status import DomainStatusResult
from siasa.snapshots.models import Snapshot
from siasa.traceability.consistency import build_repo_closure_report, build_traceability_integrity_report
from siasa.traceability.lineage import LineageRecord


@dataclass(frozen=True)
class RunArtifactBundle:
    output_dir: Path
    snapshot_path: Path
    report_paths: list[Path]
    readmodel_paths: list[Path]



def _reset_artifact_output_dir(output_dir: Path) -> None:
    if not output_dir.exists():
        return
    for path in (
        output_dir / "readmodels",
        output_dir / "reports",
        output_dir / "exports",
    ):
        if path.exists():
            shutil.rmtree(path)
    snapshot_path = output_dir / "snapshot.json"
    if snapshot_path.exists():
        snapshot_path.unlink()



def write_run_artifacts(
    *,
    output_dir: Path,
    run_state: RunState,
    fetch_metadata_records: list[FetchMetadataRecord],
    raw_records: list[object],
    normalized_records: list[NormalizedRecord],
    features: list[FeatureValue],
    domain_statuses: dict[str, DomainStatusResult],
    country_domain_statuses: dict[str, dict[str, DomainStatusResult]],
    lineage_records: list[LineageRecord],
    snapshot: Snapshot,
    daily_report: GeneratedReport,
    country_reports: dict[str, GeneratedReport],
    annotation_records: list[AnnotationRecord] | None = None,
    baseline_mode: str = "Combined 30/90/365",
    validation_view_model: dict[str, object] | None = None,
    artifact_status: dict[str, dict[str, object | None]] | None = None,
    source_domain_by_source: dict[str, str] | None = None,
    source_countries_by_source: dict[str, list[str] | None] | None = None,
    source_activation_readiness: list[dict[str, object]] | None = None,
    requested_country_ids: list[str] | None = None,
    country_expected_domains: dict[str, list[str]] | None = None,
    rule_evaluation_results: list[object] | None = None,
    fusion_results: dict[str, object] | None = None,
    bayesian_estimates: dict[str, dict[str, object]] | None = None,
    uncertainty_budgets: dict[str, object] | None = None,
    dependency_graph_result: object | None = None,
    provenance_chain_result: object | None = None,
    spread_paths_result: list[object] | None = None,
    amplification_result: list[object] | None = None,
) -> RunArtifactBundle:
    _reset_artifact_output_dir(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    readmodels_dir = output_dir / "readmodels"
    country_profiles_dir = readmodels_dir / "country_profiles"
    domain_details_dir = readmodels_dir / "domain_details"
    reports_dir = output_dir / "reports"
    exports_dir = output_dir / "exports"
    country_profiles_dir.mkdir(parents=True, exist_ok=True)
    domain_details_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = output_dir / "snapshot.json"
    snapshot_path.write_text(json.dumps(asdict(snapshot), indent=2, sort_keys=True))

    country_statuses = {
        str(country_id): str(status)
        for country_id, status in snapshot.analytical_outputs.get("country_status", {}).items()
    }
    world_map_path = readmodels_dir / "world_map.json"
    country_expected_domains = {
        str(country_id): [str(domain) for domain in domains]
        for country_id, domains in dict(country_expected_domains or {}).items()
    }
    world_map_path.write_text(
        json.dumps(
            build_world_map_read_model(
                country_statuses=country_statuses,
                active_domains=snapshot.active_domains,
                baseline_mode=baseline_mode,
                active_domains_by_country=country_expected_domains,
            ),
            indent=2,
            sort_keys=True,
        )
    )

    readmodel_paths = [world_map_path]
    source_context_by_source = _build_source_context(fetch_metadata_records)
    fetch_status_by_source = {record.source_id: record.fetch_status for record in fetch_metadata_records}
    source_domain_by_source = dict(source_domain_by_source or {})
    source_countries_by_source = dict(source_countries_by_source or {})
    explicit_requested_country_ids = [str(country_id).upper() for country_id in (requested_country_ids or []) if str(country_id).strip()]
    requested_country_ids = sorted(dict.fromkeys(explicit_requested_country_ids))
    if not requested_country_ids:
        requested_country_ids = sorted(
            {
                str(country_id)
                for country_ids in source_countries_by_source.values()
                if country_ids is not None
                for country_id in country_ids
            }
        )
    if not requested_country_ids:
        requested_country_ids = sorted(country_statuses)
    else:
        requested_country_ids = sorted({*requested_country_ids, *country_statuses})
    countries_without_updates = [
        country_id for country_id in requested_country_ids if country_id not in country_statuses
    ]
    country_metadata = _load_country_metadata(Path(__file__).resolve().parents[3])
    country_reports_by_id = {country_id: report for country_id, report in country_reports.items()}
    annotation_records = annotation_records or []
    extra_reports: list[tuple[str, GeneratedReport]] = []
    country_coverage_rows: list[dict[str, object]] = []

    for country_id, multi_domain_status in sorted(country_statuses.items()):
        country_features = [feature for feature in features if feature.country_id == country_id]
        country_event_records = [
            record
            for record in normalized_records
            if record.country_id == country_id and record.domain == "B" and "event" in record.signal_key
        ]
        country_event_ids: list[str] = []
        if country_event_records:
            event_id = f"EVT-{country_id}-{run_state.run_id}"
            country_event_ids.append(event_id)
            event_signal_keys = sorted({record.signal_key for record in country_event_records})
            event_source_ids = sorted({record.provenance_source_id for record in country_event_records})
            extra_reports.append(
                (
                    f"event_report_{event_id}.json",
                    generate_event_report(
                        country_id=country_id,
                        event_id=event_id,
                        title=f"Event context for {country_id}",
                        summary=f"Signals: {', '.join(event_signal_keys)}",
                        related_domains=["B"],
                        source_state={
                            source_id: str(source_context_by_source[source_id]["status"])
                            for source_id in event_source_ids
                            if source_id in source_context_by_source
                        },
                    ),
                )
            )
        per_country_domain_statuses = country_domain_statuses.get(country_id, {})
        country_domain_states = {
            domain: result.status
            for domain, result in sorted(per_country_domain_statuses.items())
            if any(feature.country_id == country_id and feature.domain == domain for feature in country_features)
        }
        country_uncertainty = _build_country_uncertainty(run_state)
        country_annotation_ids = _annotation_ids_for_item(annotation_records, country_id)
        country_trends = {"yearly": _build_country_yearly_trend(country_id, normalized_records)}
        country_context = dict(country_metadata.get(country_id, {}))
        country_source_ids = sorted({record.provenance_source_id for record in normalized_records if record.country_id == country_id})
        source_depth_band = _source_depth_band(len(country_source_ids))
        expected_domains = list(country_expected_domains.get(country_id, snapshot.active_domains))
        missing_domains = [
            domain for domain in expected_domains if domain not in country_domain_states
        ]
        gap_details = _build_gap_details(
            country_id=country_id,
            missing_domains=missing_domains,
            raw_records=raw_records,
            normalized_records=normalized_records,
            fetch_metadata_records=fetch_metadata_records,
            fetch_status_by_source=fetch_status_by_source,
            source_domain_by_source=source_domain_by_source,
            source_countries_by_source=source_countries_by_source,
        )
        country_domain_gap_summary = {
            "expected_domains": expected_domains,
            "observed_domains": sorted(country_domain_states.keys()),
            "missing_domains": missing_domains,
        }
        if gap_details:
            country_domain_gap_summary["gap_details"] = gap_details
        country_freshness_hours = _country_freshness_hours(country_id, normalized_records)
        country_coverage_rows.append(
            {
                "country_id": country_id,
                "priority": str(country_context.get("priority", "unassigned")),
                "source_count": len(country_source_ids),
                "source_depth_band": source_depth_band,
                "freshness_hours": country_freshness_hours,
                "freshness_band": _freshness_band(country_freshness_hours),
                "missing_domains": list(country_domain_gap_summary["missing_domains"]),
                "missing_domain_count": len(country_domain_gap_summary["missing_domains"]),
                "gap_details": gap_details,
            }
        )
        country_profile = build_country_profile_read_model(
            country_id=country_id,
            multi_domain_status=multi_domain_status,
            domain_states=country_domain_states,
            trends=country_trends,
            drivers=sorted(feature.feature_id for feature in country_features),
            linked_events=country_event_ids,
            coverage=_mean([feature.coverage for feature in country_features]),
            confidence=_mean(
                [
                    float(feature.confidence_inputs.get("source_count", 0))
                    for feature in country_features
                    if feature.confidence_inputs.get("source_count") is not None
                ]
            ),
            counter_indicators=[],
            uncertainty=country_uncertainty,
            annotations=country_annotation_ids,
            country_context=country_context,
            source_depth={"source_ids": country_source_ids, "source_count": len(country_source_ids)},
            domain_gap_summary=country_domain_gap_summary,
            configured_domains=expected_domains,
        )
        country_profile_path = country_profiles_dir / f"{country_id}.json"
        country_profile_path.write_text(json.dumps(country_profile, indent=2, sort_keys=True))
        readmodel_paths.append(country_profile_path)

        for domain, status in sorted(country_domain_states.items()):
            domain_features = [feature for feature in country_features if feature.domain == domain]
            domain_records = [
                record
                for record in normalized_records
                if record.country_id == country_id and record.domain == domain
            ]
            source_context = [
                source_context_by_source[source_id]
                for source_id in sorted({record.provenance_source_id for record in domain_records})
                if source_id in source_context_by_source
            ]
            domain_annotation_ids = _annotation_ids_for_item(annotation_records, f"{country_id}:{domain}")
            domain_status = per_country_domain_statuses[domain]
            domain_read_model = build_domain_detail_read_model(
                country_id=country_id,
                domain=domain,
                time_series=[
                    {"timestamp": record.timestamp, "signal_key": record.signal_key, "value": record.value}
                    for record in domain_records
                ],
                baseline_comparison={
                    "current_window": _mean([record.value for record in domain_records]),
                    "delta_to_baseline": domain_status.anomaly_score,
                },
                feature_values=[
                    {
                        "feature_id": feature.feature_id,
                        "value": feature.value,
                        "coverage": feature.coverage,
                    }
                    for feature in domain_features
                ],
                source_context=source_context,
                anomaly_state=status,
                uncertainty=list(domain_status.uncertainty_indicators),
                annotations=domain_annotation_ids,
            )
            domain_path = domain_details_dir / f"{country_id}__{domain}.json"
            domain_path.write_text(json.dumps(domain_read_model, indent=2, sort_keys=True))
            readmodel_paths.append(domain_path)

            extra_reports.append(
                (
                    f"domain_report_{country_id}_{domain}.json",
                    generate_domain_report(
                        country_id=country_id,
                        domain=domain,
                        anomaly_state=status,
                        feature_values=[
                            {
                                "feature_id": feature.feature_id,
                                "value": feature.value,
                                "coverage": feature.coverage,
                            }
                            for feature in domain_features
                        ],
                        source_state={entry["source_id"]: str(entry["status"]) for entry in source_context},
                        uncertainty=list(domain_status.uncertainty_indicators),
                        linked_event_ids=country_event_ids if domain == "B" else [],
                    ),
                )
            )

    source_coverage_rows = [_build_source_coverage_row(record) for record in fetch_metadata_records]
    source_coverage_path = readmodels_dir / "source_coverage.json"
    source_coverage_path.write_text(
        json.dumps(
            build_source_coverage_read_model(
                source_coverage_rows,
                missing_sources=[],
                source_activation_readiness=source_activation_readiness,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    readmodel_paths.append(source_coverage_path)

    extra_reports.append(
        (
            "coverage_report.json",
            generate_coverage_report(
                run_id=run_state.run_id,
                source_rows=source_coverage_rows,
                failed_sources=run_state.failed_sources,
                missing_sources=[],
                source_state={record.source_id: record.fetch_status for record in fetch_metadata_records},
            ),
        )
    )

    available_reports = sorted(
        [daily_report.report_id]
        + [report.report_id for _, report in sorted(country_reports_by_id.items())]
        + [report.report_id for _, report in extra_reports]
    )
    system_status_path = readmodels_dir / "system_status.json"
    system_status_path.write_text(
        json.dumps(
            build_system_status_read_model(
                run_id=run_state.run_id,
                run_status=run_state.status,
                active_domains=snapshot.active_domains,
                countries_total=len(requested_country_ids),
                countries_with_updates=len(country_statuses),
                countries_without_updates=countries_without_updates,
                failed_sources=run_state.failed_sources,
                available_reports=available_reports,
                snapshot_id=snapshot.snapshot_id,
                country_set_id=snapshot.country_set_id,
                reprocessing_status="idle",
                last_run=run_state.run_id,
                artifact_status=artifact_status,
                country_coverage_visibility=_build_country_coverage_visibility(country_coverage_rows),
                source_activation_readiness=source_activation_readiness,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    readmodel_paths.append(system_status_path)

    traceability_path = readmodels_dir / "traceability_lineage.json"
    traceability_path.write_text(
        json.dumps(
            {"lineage_records": [asdict(record) for record in lineage_records]},
            indent=2,
            sort_keys=True,
        )
    )
    readmodel_paths.append(traceability_path)

    repo_closure_path = readmodels_dir / "repo_closure.json"
    repo_closure_path.write_text(
        json.dumps(
            build_repo_closure_report(repo_root=Path(__file__).resolve().parents[3]),
            indent=2,
            sort_keys=True,
        )
    )
    readmodel_paths.append(repo_closure_path)

    annotations_path = readmodels_dir / "annotations.json"
    annotations_path.write_text(json.dumps(build_annotations_view_model(annotation_records), indent=2, sort_keys=True))
    readmodel_paths.append(annotations_path)

    if validation_view_model is not None:
        validation_path = readmodels_dir / "validation_backtest.json"
        validation_path.write_text(json.dumps(validation_view_model, indent=2, sort_keys=True))
        readmodel_paths.append(validation_path)

    readiness_available_pages = {
        "index.html",
        "coverage.html",
        "reports.html",
        "runs.html",
        "trends.html",
        "events.html",
        "comparison.html",
        "readiness.html",
        "release_package.html",
        "traceability.html",
        "annotations.html",
    }
    if validation_view_model is not None:
        readiness_available_pages.add("validation.html")
    readiness_report_catalog = {
        report_id: {"report_id": report_id}
        for report_id in available_reports
    }
    readiness_view_model = build_readiness_view_model(
                country_profile_read_models={
                    country_file.stem: json.loads(country_file.read_text())
                    for country_file in sorted(country_profiles_dir.glob("*.json"))
                },
                domain_detail_read_models={
                    (str(read_model["country_id"]), str(read_model["domain"])): read_model
                    for read_model in (
                        json.loads(domain_file.read_text())
                        for domain_file in sorted(domain_details_dir.glob("*.json"))
                    )
                },
                report_catalog=readiness_report_catalog,
                system_status_read_model=json.loads(system_status_path.read_text()),
                source_coverage_read_model=json.loads(source_coverage_path.read_text()),
                validation_view_model=validation_view_model,
                traceability_view_model=json.loads(traceability_path.read_text()),
                annotations_view_model=json.loads(annotations_path.read_text()),
                repo_closure_view_model=json.loads(repo_closure_path.read_text()),
                available_pages=readiness_available_pages,
            )
    readiness_path = readmodels_dir / "readiness.json"
    readiness_path.write_text(
        json.dumps(readiness_view_model, indent=2, sort_keys=True)
    )
    readmodel_paths.append(readiness_path)

    # G4: Approval lifecycle record - load existing or create default pending record
    approval_lifecycle_path = readmodels_dir / "approval_lifecycle_record.json"
    existing_record = load_approval_lifecycle_record(approval_lifecycle_path)
    if existing_record is None:
        existing_record = build_default_approval_lifecycle_record(
            package_run_id=run_state.run_id if run_state is not None else '',
        )
    approval_lifecycle_vm = build_approval_lifecycle_view_model(existing_record)
    approval_lifecycle_path.write_text(
        json.dumps(approval_lifecycle_vm, indent=2, sort_keys=True)
    )
    readmodel_paths.append(approval_lifecycle_path)

    release_demo_package_path = readmodels_dir / "release_demo_package.json"
    release_demo_package_path.write_text(
        json.dumps(
            build_release_demo_package_view_model(
                readiness_view_model=readiness_view_model,
                release_gate_view_model=build_release_gate_view_model(
                    readiness_view_model=readiness_view_model,
                    traceability_integrity_report=build_traceability_integrity_report(repo_root=Path(__file__).resolve().parents[3]),
                ),
                operator_release_summary_view_model=None,
                operator_blocker_causality_view_model=None,
                operator_operability_cluster_view_model=None,
                operator_stale_remediation_action_plan_view_model=None,
                system_status_read_model=json.loads(system_status_path.read_text()),
                validation_view_model=validation_view_model,
                traceability_view_model=json.loads(traceability_path.read_text()),
                repo_closure_view_model=json.loads(repo_closure_path.read_text()),
                approval_lifecycle_view_model=approval_lifecycle_vm,
                available_pages=readiness_available_pages,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    readmodel_paths.append(release_demo_package_path)

    traceability_integrity_path = readmodels_dir / "traceability_integrity.json"
    traceability_integrity_path.write_text(
        json.dumps(
            build_traceability_integrity_report(repo_root=Path(__file__).resolve().parents[3]),
            indent=2,
            sort_keys=True,
        )
    )
    readmodel_paths.append(traceability_integrity_path)

    stakeholder_functional_closure_path = readmodels_dir / "stakeholder_functional_closure.json"
    stakeholder_functional_closure_path.write_text(
        json.dumps(
            build_stakeholder_functional_closure_report(repo_root=Path(__file__).resolve().parents[3]),
            indent=2,
            sort_keys=True,
        )
    )
    readmodel_paths.append(stakeholder_functional_closure_path)

    release_gate_path = readmodels_dir / "release_gate.json"
    release_gate_path.write_text(
        json.dumps(
            build_release_gate_view_model(
                readiness_view_model=readiness_view_model,
                traceability_integrity_report=json.loads(traceability_integrity_path.read_text()),
            ),
            indent=2,
            sort_keys=True,
        )
    )
    readmodel_paths.append(release_gate_path)

    release_assessment = build_repo_release_gate_assessment(repo_root=Path(__file__).resolve().parents[3])
    release_evidence_assessment_path = readmodels_dir / "release_evidence_assessment.json"
    release_evidence_assessment_path.write_text(
        json.dumps(release_assessment, indent=2, sort_keys=True)
    )
    readmodel_paths.append(release_evidence_assessment_path)

    stakeholder_e2e_flow_coverage_path = readmodels_dir / "stakeholder_e2e_flow_coverage.json"
    stakeholder_e2e_flow_coverage_path.write_text(
        json.dumps(release_assessment.get("stakeholder_e2e_flow_coverage", {}), indent=2, sort_keys=True)
    )
    readmodel_paths.append(stakeholder_e2e_flow_coverage_path)

    stakeholder_e2e_ui_smoke_path = readmodels_dir / "stakeholder_e2e_ui_smoke.json"
    stakeholder_e2e_ui_smoke_path.write_text(
        json.dumps(release_assessment.get("stakeholder_e2e_ui_smoke", {}), indent=2, sort_keys=True)
    )
    readmodel_paths.append(stakeholder_e2e_ui_smoke_path)

    stakeholder_browser_e2e_acceptance_path = readmodels_dir / "stakeholder_browser_e2e_acceptance.json"
    stakeholder_browser_e2e_acceptance_path.write_text(
        json.dumps(release_assessment.get("stakeholder_browser_e2e_acceptance", {}), indent=2, sort_keys=True)
    )
    readmodel_paths.append(stakeholder_browser_e2e_acceptance_path)

    stakeholder_browser_interaction_depth_path = readmodels_dir / "stakeholder_browser_interaction_depth.json"
    stakeholder_browser_interaction_depth_path.write_text(
        json.dumps(release_assessment.get("stakeholder_browser_interaction_depth", {}), indent=2, sort_keys=True)
    )
    readmodel_paths.append(stakeholder_browser_interaction_depth_path)

    stakeholder_browser_failure_resilience_path = readmodels_dir / "stakeholder_browser_failure_resilience.json"
    stakeholder_browser_failure_resilience_path.write_text(
        json.dumps(release_assessment.get("stakeholder_browser_failure_resilience", {}), indent=2, sort_keys=True)
    )
    readmodel_paths.append(stakeholder_browser_failure_resilience_path)

    release_readiness_index_path = readmodels_dir / "release_readiness_index.json"
    release_readiness_index_path.write_text(
        json.dumps(release_assessment.get("release_readiness_index", {}), indent=2, sort_keys=True)
    )
    readmodel_paths.append(release_readiness_index_path)

    report_paths = []
    daily_report_path = reports_dir / "daily_snapshot.json"
    daily_report_path.write_text(
        json.dumps(_serialize_report(daily_report, _write_report_exports(daily_report, exports_dir)), indent=2, sort_keys=True)
    )
    report_paths.append(daily_report_path)
    for country_id, report in sorted(country_reports_by_id.items()):
        report_path = reports_dir / f"country_profile_{country_id}.json"
        report_path.write_text(
            json.dumps(_serialize_report(report, _write_report_exports(report, exports_dir)), indent=2, sort_keys=True)
        )
        report_paths.append(report_path)
    for report_filename, report in extra_reports:
        report_path = reports_dir / report_filename
        report_path.write_text(
            json.dumps(_serialize_report(report, _write_report_exports(report, exports_dir)), indent=2, sort_keys=True)
        )
        report_paths.append(report_path)

    # --- Phase 4-6 analytics artifacts ---
    _write_analytics_artifacts(
        output_dir=output_dir,
        rule_evaluation_results=rule_evaluation_results,
        fusion_results=fusion_results,
        bayesian_estimates=bayesian_estimates,
        uncertainty_budgets=uncertainty_budgets,
        dependency_graph_result=dependency_graph_result,
        provenance_chain_result=provenance_chain_result,
        spread_paths_result=spread_paths_result,
        amplification_result=amplification_result,
    )

    return RunArtifactBundle(
        output_dir=output_dir,
        snapshot_path=snapshot_path,
        report_paths=report_paths,
        readmodel_paths=readmodel_paths,
    )


def _serialize_report(report: GeneratedReport, export_files: list[dict[str, Any]]) -> dict[str, object]:
    return {
        "report_id": report.report_id,
        "report_type": report.report_type,
        "format": "json+markdown",
        "markdown": report.markdown,
        "payload": report.json_payload,
        "export_files": export_files,
    }


def _write_report_exports(report: GeneratedReport, exports_dir: Path) -> list[dict[str, Any]]:
    report_export_dir = exports_dir / report.report_type
    report_export_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = report_export_dir / f"{report.report_id}.md"
    markdown_path.write_text(report.markdown)
    json_path = report_export_dir / f"{report.report_id}.json"
    json_path.write_text(json.dumps(report.json_payload, indent=2, sort_keys=True))

    return [
        {
            "label": "Markdown",
            "format": "md",
            "path": str(markdown_path),
            "relative_path": markdown_path.relative_to(exports_dir.parent).as_posix(),
        },
        {
            "label": "JSON",
            "format": "json",
            "path": str(json_path),
            "relative_path": json_path.relative_to(exports_dir.parent).as_posix(),
        },
    ]


def _write_analytics_artifacts(
    *,
    output_dir: Path,
    rule_evaluation_results: list[object] | None = None,
    fusion_results: dict[str, object] | None = None,
    bayesian_estimates: dict[str, dict[str, object]] | None = None,
    uncertainty_budgets: dict[str, object] | None = None,
    dependency_graph_result: object | None = None,
    provenance_chain_result: object | None = None,
    spread_paths_result: list[object] | None = None,
    amplification_result: list[object] | None = None,
) -> None:
    """Write Phase 4-6 analytical results as JSON files under analytics/."""
    analytics_dir = output_dir / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)

    def _safe_asdict(obj: object) -> Any:
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
        if isinstance(obj, dict):
            return {k: _safe_asdict(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_safe_asdict(item) for item in obj]
        return obj

    # Rule evaluations
    rule_data = [_safe_asdict(r) for r in (rule_evaluation_results or [])]
    (analytics_dir / "rule_evaluations.json").write_text(
        json.dumps(rule_data, indent=2, sort_keys=True)
    )

    # Cross-domain fusion
    fusion_data = {k: _safe_asdict(v) for k, v in (fusion_results or {}).items()}
    (analytics_dir / "cross_domain_fusion.json").write_text(
        json.dumps(fusion_data, indent=2, sort_keys=True)
    )

    # Bayesian estimates
    bayesian_data = {
        k: {dk: _safe_asdict(dv) for dk, dv in v.items()}
        for k, v in (bayesian_estimates or {}).items()
    }
    (analytics_dir / "bayesian_estimates.json").write_text(
        json.dumps(bayesian_data, indent=2, sort_keys=True)
    )

    # Uncertainty budgets
    uncertainty_data = {k: _safe_asdict(v) for k, v in (uncertainty_budgets or {}).items()}
    (analytics_dir / "uncertainty_budgets.json").write_text(
        json.dumps(uncertainty_data, indent=2, sort_keys=True)
    )

    # Dependency graph
    dep_data = _safe_asdict(dependency_graph_result) if dependency_graph_result is not None else {}
    (analytics_dir / "dependency_graph.json").write_text(
        json.dumps(dep_data, indent=2, sort_keys=True)
    )

    # Provenance chain
    prov_data = _safe_asdict(provenance_chain_result) if provenance_chain_result is not None else {}
    (analytics_dir / "provenance_chain.json").write_text(
        json.dumps(prov_data, indent=2, sort_keys=True)
    )

    # Information epidemiology
    epi_data = {
        "spread_paths": [_safe_asdict(p) for p in (spread_paths_result or [])],
        "amplification_events": [_safe_asdict(a) for a in (amplification_result or [])],
    }
    (analytics_dir / "info_epidemiology.json").write_text(
        json.dumps(epi_data, indent=2, sort_keys=True)
    )


def _build_source_context(fetch_metadata_records: list[FetchMetadataRecord]) -> dict[str, dict[str, object]]:
    source_context: dict[str, dict[str, object]] = {}
    for record in fetch_metadata_records:
        freshness_hours = None
        if record.fetched_at.startswith("RUN-"):
            freshness_hours = None
        source_context[record.source_id] = {
            "source_id": record.source_id,
            "status": record.fetch_status,
            "history_horizon": "n/a",
            "freshness_hours": freshness_hours,
            "confidence": None,
        }
    return source_context


def _build_source_coverage_row(record: FetchMetadataRecord) -> dict[str, object]:
    return {
        "source_id": record.source_id,
        "status": record.fetch_status,
        "history_horizon": "n/a",
        "freshness_hours": None,
        "confidence": None,
        "record_count": record.record_count,
        "diagnostics": record.diagnostics,
    }


def _annotation_ids_for_item(annotation_records: list[AnnotationRecord], item_id: str) -> list[str]:
    return [annotation.annotation_id for annotation in annotation_records if item_id in annotation.linked_items]


def _build_country_uncertainty(run_state: RunState) -> list[str]:
    uncertainty: list[str] = []
    if run_state.status == "partial_success":
        uncertainty.append("partial_success")
    if run_state.failed_sources:
        uncertainty.append(f"failed_sources:{','.join(run_state.failed_sources)}")
    return uncertainty



def _build_country_yearly_trend(country_id: str, normalized_records: list[NormalizedRecord]) -> list[dict[str, float | str]]:
    series_by_label: dict[str, list[float]] = {}
    for record in normalized_records:
        if record.country_id != country_id:
            continue
        timestamp = str(record.timestamp)
        label = timestamp[:7] if "-" in timestamp else timestamp[:4]
        if not label:
            continue
        series_by_label.setdefault(label, []).append(float(record.value))
    return [
        {"label": label, "value": sum(values) / len(values)}
        for label, values in sorted(series_by_label.items())
    ]



def _load_country_metadata(repo_root: Path) -> dict[str, dict[str, str]]:
    country_set_path = repo_root / "vmodel" / "project" / "mvp_countries.yaml"
    if not country_set_path.exists():
        return {}
    try:
        records = load_country_set(country_set_path)
    except (OSError, ValueError):
        return {}
    return {
        record.iso3: {
            "country_name": record.country_name,
            "priority": record.priority,
            "selection_type": record.selection_type,
            "region": record.region,
            "rationale": record.rationale,
        }
        for record in records
    }



def _build_gap_details(
    *,
    country_id: str,
    missing_domains: list[str],
    raw_records: list[object],
    normalized_records: list[NormalizedRecord],
    fetch_metadata_records: list[FetchMetadataRecord],
    fetch_status_by_source: dict[str, str],
    source_domain_by_source: dict[str, str],
    source_countries_by_source: dict[str, list[str] | None],
) -> list[dict[str, object]]:
    gap_details: list[dict[str, object]] = []
    metadata_by_source = {record.source_id: record for record in fetch_metadata_records}
    for domain in missing_domains:
        domain_source_ids = sorted(
            source_id
            for source_id, source_domain in source_domain_by_source.items()
            if source_domain == domain and _source_applies_to_country(source_countries_by_source.get(source_id), country_id)
        )
        country_domain_raw_records = [
            raw_record
            for raw_record in raw_records
            if getattr(raw_record, "source_id", None) in domain_source_ids
            and str(getattr(raw_record, "raw_payload", {}).get("country_id", "")).upper() == country_id
        ]
        country_domain_records = [
            record for record in normalized_records if record.country_id == country_id and record.domain == domain
        ]
        source_reason_details = [
            _build_source_gap_reason_detail(
                source_id=source_id,
                country_id=country_id,
                domain=domain,
                raw_records=raw_records,
                normalized_records=normalized_records,
                metadata=metadata_by_source.get(source_id),
                fetch_status=fetch_status_by_source.get(source_id),
            )
            for source_id in domain_source_ids
        ]
        if not domain_source_ids:
            reason = "not_configured_for_runtime"
        elif any(fetch_status_by_source.get(source_id) == "failed" for source_id in domain_source_ids):
            reason = "source_failed_this_run"
        elif all((metadata_by_source.get(source_id).record_count if metadata_by_source.get(source_id) is not None else 0) == 0 for source_id in domain_source_ids):
            reason = "zero_records_returned"
        elif not country_domain_raw_records:
            reason = "no_usable_input_data"
        elif not country_domain_records:
            reason = "records_filtered_out_or_not_mapped"
        else:
            freshness_values = [
                float(record.quality_context.get("freshness_hours"))
                for record in country_domain_records
                if isinstance(record.quality_context.get("freshness_hours"), (int, float))
            ]
            if freshness_values and min(freshness_values) > 168.0:
                reason = "stale_source_window"
            else:
                reason = "filtered_by_feature_or_sufficiency_gate"
        gap_details.append(
            {
                "domain": domain,
                "reason": reason,
                "source_ids": domain_source_ids,
                "diagnostics_by_source": {
                    source_id: metadata_by_source[source_id].diagnostics
                    for source_id in domain_source_ids
                    if source_id in metadata_by_source and metadata_by_source[source_id].diagnostics
                },
                "source_reason_details": source_reason_details,
            }
        )
    return gap_details



def _build_source_gap_reason_detail(
    *,
    source_id: str,
    country_id: str,
    domain: str,
    raw_records: list[object],
    normalized_records: list[NormalizedRecord],
    metadata: FetchMetadataRecord | None,
    fetch_status: str | None,
) -> dict[str, object]:
    source_raw_records = [raw_record for raw_record in raw_records if getattr(raw_record, "source_id", None) == source_id]
    source_country_raw_records = [
        raw_record
        for raw_record in source_raw_records
        if str(getattr(raw_record, "raw_payload", {}).get("country_id", "")).upper() == country_id
    ]
    source_country_domain_records = [
        record
        for record in normalized_records
        if record.country_id == country_id and record.domain == domain and record.provenance_source_id == source_id
    ]
    if fetch_status == "failed":
        reason = "source_failed_this_run"
    elif metadata is not None and metadata.record_count == 0:
        reason = "zero_records_returned"
    elif not source_country_raw_records:
        reason = "records_only_for_other_countries_in_scope"
    elif not source_country_domain_records:
        reason = "records_for_country_not_mapped_to_required_signal_set"
    else:
        freshness_values = [
            float(record.quality_context.get("freshness_hours"))
            for record in source_country_domain_records
            if isinstance(record.quality_context.get("freshness_hours"), (int, float))
        ]
        if freshness_values and min(freshness_values) > 168.0:
            reason = "stale_source_window"
        else:
            reason = "filtered_by_feature_or_sufficiency_gate"
    action_category, severity = _classify_source_gap_action(reason)
    return {
        "source_id": source_id,
        "reason": reason,
        "diagnostics": metadata.diagnostics if metadata is not None else "",
        "action_category": action_category,
        "severity": severity,
    }



def _classify_source_gap_action(reason: str) -> tuple[str, str]:
    if reason == "source_failed_this_run":
        return ("fetch_problem", "high")
    if reason == "zero_records_returned":
        return ("fetch_problem", "medium")
    if reason == "records_only_for_other_countries_in_scope":
        return ("scope_config_problem", "medium")
    if reason == "records_for_country_not_mapped_to_required_signal_set":
        return ("mapping_problem", "medium")
    if reason == "stale_source_window":
        return ("freshness_problem", "medium")
    if reason == "filtered_by_feature_or_sufficiency_gate":
        return ("downstream_gating_problem", "medium")
    return ("unknown", "low")



def _source_applies_to_country(configured_countries: list[str] | None, country_id: str) -> bool:
    if configured_countries is None:
        return True
    return country_id in configured_countries



def _source_depth_band(source_count: int) -> str:
    if source_count <= 1:
        return "minimal"
    if source_count <= 3:
        return "moderate"
    return "deep"



def _country_freshness_hours(country_id: str, normalized_records: list[NormalizedRecord]) -> float | None:
    freshness_values = [
        float(record.quality_context.get("freshness_hours"))
        for record in normalized_records
        if record.country_id == country_id and isinstance(record.quality_context.get("freshness_hours"), (int, float))
    ]
    if not freshness_values:
        return None
    return max(freshness_values)



def _freshness_band(freshness_hours: float | None) -> str:
    if freshness_hours is None:
        return "unknown"
    if freshness_hours <= 24.0:
        return "fresh"
    if freshness_hours <= 168.0:
        return "aging"
    return "stale"



def _build_country_coverage_visibility(country_rows: list[dict[str, object]]) -> dict[str, object]:
    priority_map: dict[str, list[str]] = {}
    for row in country_rows:
        priority = str(row.get("priority", "unassigned"))
        priority_map.setdefault(priority, []).append(str(row.get("country_id", "UNKNOWN")))
    priority_summary = [
        {
            "priority": priority,
            "country_count": len(sorted(country_ids)),
            "countries": sorted(country_ids),
        }
        for priority, country_ids in sorted(priority_map.items())
    ]

    source_depth_band_summary = []
    for band in ("minimal", "moderate", "deep"):
        band_countries = sorted(
            str(row.get("country_id", "UNKNOWN"))
            for row in country_rows
            if str(row.get("source_depth_band", "")) == band
        )
        source_depth_band_summary.append(
            {
                "band": band,
                "country_count": len(band_countries),
                "countries": band_countries,
            }
        )

    freshness_band_summary = []
    for band in ("fresh", "aging", "stale", "unknown"):
        band_countries = sorted(
            str(row.get("country_id", "UNKNOWN"))
            for row in country_rows
            if str(row.get("freshness_band", "unknown")) == band
        )
        freshness_band_summary.append(
            {
                "band": band,
                "country_count": len(band_countries),
                "countries": band_countries,
            }
        )

    country_freshness_rows = [
        {
            "country_id": str(row.get("country_id", "UNKNOWN")),
            "freshness_hours": row.get("freshness_hours"),
            "freshness_band": str(row.get("freshness_band", "unknown")),
            "priority": str(row.get("priority", "unassigned")),
            "source_depth_band": str(row.get("source_depth_band", "minimal")),
        }
        for row in sorted(country_rows, key=lambda row: str(row.get("country_id", "UNKNOWN")))
    ]

    stale_priority_watchlist = [
        {
            "priority_rank": index + 1,
            "country_id": str(row.get("country_id", "UNKNOWN")),
            "priority": str(row.get("priority", "unassigned")),
            "freshness_hours": row.get("freshness_hours"),
            "source_depth_band": str(row.get("source_depth_band", "minimal")),
        }
        for index, row in enumerate(
            sorted(
                [
                    row
                    for row in country_freshness_rows
                    if str(row.get("freshness_band", "unknown")) == "stale"
                ],
                key=lambda row: (
                    _priority_sort_key(str(row.get("priority", "unassigned"))),
                    -(float(row.get("freshness_hours")) if isinstance(row.get("freshness_hours"), (int, float)) else -1.0),
                    str(row.get("country_id", "UNKNOWN")),
                ),
            )
        )
    ]

    stale_priority_summary = {
        "stale_country_count": len(stale_priority_watchlist),
        "p1_stale_count": sum(1 for row in stale_priority_watchlist if str(row.get("priority")) == "P1"),
        "p2_stale_count": sum(1 for row in stale_priority_watchlist if str(row.get("priority")) == "P2"),
        "p3_stale_count": sum(1 for row in stale_priority_watchlist if str(row.get("priority")) == "P3"),
    }

    country_gap_rows = [
        {
            "country_id": str(row.get("country_id", "UNKNOWN")),
            "priority": str(row.get("priority", "unassigned")),
            "source_count": int(row.get("source_count", 0)),
            "source_depth_band": str(row.get("source_depth_band", "minimal")),
            "freshness_hours": row.get("freshness_hours"),
            "freshness_band": str(row.get("freshness_band", "unknown")),
            "missing_domains": [str(item) for item in row.get("missing_domains", [])],
            "missing_domain_count": int(row.get("missing_domain_count", 0)),
            "gap_details": [
                {
                    "domain": str(detail.get("domain", "UNKNOWN")),
                    "reason": str(detail.get("reason", "unknown")),
                    "source_ids": [str(item) for item in detail.get("source_ids", [])],
                    "diagnostics_by_source": {str(source_id): str(diagnostic) for source_id, diagnostic in dict(detail.get("diagnostics_by_source", {})).items()},
                    "source_reason_details": [
                        {
                            "source_id": str(source_detail.get("source_id", "UNKNOWN")),
                            "reason": str(source_detail.get("reason", "unknown")),
                            "diagnostics": str(source_detail.get("diagnostics", "")),
                            "action_category": str(source_detail.get("action_category", "triage_required")),
                            "severity": str(source_detail.get("severity", "low")),
                        }
                        for source_detail in detail.get("source_reason_details", [])
                    ],
                }
                for detail in row.get("gap_details", [])
            ],
        }
        for row in country_rows
        if row.get("missing_domain_count", 0)
    ]


    missing_domain_totals: dict[str, int] = {}
    for row in country_gap_rows:
        for domain in row.get("missing_domains", []):
            missing_domain_totals[domain] = missing_domain_totals.get(domain, 0) + 1

    remediation_groups: dict[tuple[str, str], dict[str, object]] = {}
    for row in country_gap_rows:
        country_id = str(row.get("country_id", "UNKNOWN"))
        for detail in row.get("gap_details", []):
            for source_detail in detail.get("source_reason_details", []):
                action_category = str(source_detail.get("action_category", "unknown"))
                severity = str(source_detail.get("severity", "low"))
                group = remediation_groups.setdefault(
                    (action_category, severity),
                    {
                        "action_category": action_category,
                        "severity": severity,
                        "countries": set(),
                        "source_ids": set(),
                    },
                )
                group["countries"].add(country_id)
                group["source_ids"].add(str(source_detail.get("source_id", "UNKNOWN")))

    remediation_watchlist = []
    for priority_rank, ((action_category, severity), group) in enumerate(
        sorted(
            remediation_groups.items(),
            key=lambda item: (
                -_remediation_priority_score(
                    str(item[0][1]),
                    len(set(item[1]["countries"])),
                    len(set(item[1]["source_ids"])),
                ),
                _severity_rank(str(item[0][1])),
                str(item[0][0]),
                tuple(sorted(str(source_id) for source_id in item[1]["source_ids"])),
                tuple(sorted(str(country_id) for country_id in item[1]["countries"])),
            ),
        ),
        start=1,
    ):
        countries = sorted(group["countries"])
        source_ids = sorted(group["source_ids"])
        country_count = len(countries)
        source_count = len(source_ids)
        remediation_watchlist.append(
            {
                "priority_rank": priority_rank,
                "priority_score": _remediation_priority_score(severity, country_count, source_count),
                "action_category": action_category,
                "severity": severity,
                "country_count": country_count,
                "source_count": source_count,
                "countries": countries,
                "source_ids": source_ids,
                "suggested_next_action": _suggested_next_action(action_category),
                "owner_hint": _owner_hint(action_category),
                "evidence_link": _watchlist_evidence_link(source_ids),
            }
        )

    return {
        "priority_summary": priority_summary,
        "source_depth_band_summary": source_depth_band_summary,
        "freshness_band_summary": freshness_band_summary,
        "country_freshness_rows": country_freshness_rows,
        "stale_priority_summary": stale_priority_summary,
        "stale_priority_watchlist": stale_priority_watchlist,
        "country_gap_rows": country_gap_rows,
        "missing_domain_totals": dict(sorted(missing_domain_totals.items())),
        "remediation_watchlist": remediation_watchlist,
    }



def _priority_sort_key(priority: str) -> int:
    return {"P1": 0, "P2": 1, "P3": 2}.get(priority, 3)



def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)



def _remediation_priority_score(severity: str, country_count: int, source_count: int) -> int:
    severity_base = {"high": 200, "medium": 100, "low": 0}.get(severity, 0)
    return severity_base + (10 * max(country_count, 0)) + max(source_count, 0)



def _suggested_next_action(action_category: str) -> str:
    if action_category == "fetch_problem":
        return "Retry adapter execution and inspect source-side rate limiting or transport failures."
    if action_category == "scope_config_problem":
        return "Review country scope and source applicability configuration for the affected source."
    if action_category == "mapping_problem":
        return "Review normalization and required-signal mapping for the affected source."
    if action_category == "freshness_problem":
        return "Review source freshness window and staleness thresholds for the affected feed."
    if action_category == "downstream_gating_problem":
        return "Review feature sufficiency and downstream gating thresholds for the affected source."
    return "Review gap diagnostics manually and classify the next remediation step."



def _owner_hint(action_category: str) -> str:
    if action_category == "fetch_problem":
        return "adapter/source integration"
    if action_category == "scope_config_problem":
        return "runtime/source configuration"
    if action_category == "mapping_problem":
        return "normalization/mapping maintenance"
    if action_category == "freshness_problem":
        return "source operations / freshness governance"
    if action_category == "downstream_gating_problem":
        return "feature/scoring logic"
    return "triage required"



def _watchlist_evidence_link(source_ids: list[str]) -> str:
    if len(source_ids) == 1:
        return f"coverage.html#source-{source_ids[0]}"
    return "coverage.html"



def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
