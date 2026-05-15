from __future__ import annotations

import json
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
from siasa.readmodels.source_coverage import build_source_coverage_read_model
from siasa.readmodels.system_status import build_system_status_read_model
from siasa.readmodels.world_map import build_world_map_read_model
from siasa.reporting.country_report import GeneratedReport
from siasa.reporting.manual_reports import generate_coverage_report, generate_domain_report, generate_event_report
from siasa.runs.run_state import RunState
from siasa.scoring.domain_status import DomainStatusResult
from siasa.snapshots.models import Snapshot
from siasa.traceability.consistency import build_repo_closure_report
from siasa.traceability.lineage import LineageRecord


@dataclass(frozen=True)
class RunArtifactBundle:
    output_dir: Path
    snapshot_path: Path
    report_paths: list[Path]
    readmodel_paths: list[Path]


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
) -> RunArtifactBundle:
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
    world_map_path.write_text(
        json.dumps(
            build_world_map_read_model(
                country_statuses=country_statuses,
                active_domains=snapshot.active_domains,
                baseline_mode=baseline_mode,
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
        missing_domains = [
            domain for domain in snapshot.active_domains if domain not in country_domain_states
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
            "expected_domains": list(snapshot.active_domains),
            "observed_domains": sorted(country_domain_states.keys()),
            "missing_domains": missing_domains,
        }
        if gap_details:
            country_domain_gap_summary["gap_details"] = gap_details
        country_coverage_rows.append(
            {
                "country_id": country_id,
                "priority": str(country_context.get("priority", "unassigned")),
                "source_count": len(country_source_ids),
                "source_depth_band": source_depth_band,
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
                countries_total=len(country_statuses),
                countries_with_updates=len(country_statuses),
                failed_sources=run_state.failed_sources,
                available_reports=available_reports,
                snapshot_id=snapshot.snapshot_id,
                reprocessing_status="idle",
                last_run=run_state.run_id,
                artifact_status=artifact_status,
                country_coverage_visibility=_build_country_coverage_visibility(country_coverage_rows),
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
    if source_count == 2:
        return "moderate"
    return "deep"



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

    country_gap_rows = [
        {
            "country_id": str(row.get("country_id", "UNKNOWN")),
            "priority": str(row.get("priority", "unassigned")),
            "source_count": int(row.get("source_count", 0)),
            "source_depth_band": str(row.get("source_depth_band", "minimal")),
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
                            "action_category": str(source_detail.get("action_category", "unknown")),
                            "severity": str(source_detail.get("severity", "low")),
                        }
                        for source_detail in detail.get("source_reason_details", [])
                        if isinstance(source_detail, dict)
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

    remediation_watchlist = [
        {
            "action_category": action_category,
            "severity": severity,
            "country_count": len(sorted(group["countries"])),
            "source_count": len(sorted(group["source_ids"])),
            "countries": sorted(group["countries"]),
            "source_ids": sorted(group["source_ids"]),
        }
        for (action_category, severity), group in sorted(
            remediation_groups.items(),
            key=lambda item: (_severity_rank(str(item[0][1])), str(item[0][0])),
        )
    ]

    return {
        "priority_summary": priority_summary,
        "source_depth_band_summary": source_depth_band_summary,
        "country_gap_rows": country_gap_rows,
        "missing_domain_totals": dict(sorted(missing_domain_totals.items())),
        "remediation_watchlist": remediation_watchlist,
    }



def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)



def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
