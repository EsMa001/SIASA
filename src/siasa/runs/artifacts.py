from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from siasa.adapters.fetch_metadata import FetchMetadataRecord
from siasa.data.normalized_models import NormalizedRecord
from siasa.features.base import FeatureValue
from siasa.readmodels.country_profile import build_country_profile_read_model
from siasa.readmodels.domain_detail import build_domain_detail_read_model
from siasa.readmodels.source_coverage import build_source_coverage_read_model
from siasa.readmodels.system_status import build_system_status_read_model
from siasa.readmodels.world_map import build_world_map_read_model
from siasa.reporting.country_report import GeneratedReport
from siasa.runs.run_state import RunState
from siasa.scoring.domain_status import DomainStatusResult
from siasa.snapshots.models import Snapshot
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
    normalized_records: list[NormalizedRecord],
    features: list[FeatureValue],
    domain_statuses: dict[str, DomainStatusResult],
    lineage_records: list[LineageRecord],
    snapshot: Snapshot,
    daily_report: GeneratedReport,
    country_reports: dict[str, GeneratedReport],
    baseline_mode: str = "Combined 30/90/365",
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
    country_reports_by_id = {country_id: report for country_id, report in country_reports.items()}

    for country_id, multi_domain_status in sorted(country_statuses.items()):
        country_features = [feature for feature in features if feature.country_id == country_id]
        country_domain_states = {
            domain: result.status
            for domain, result in sorted(domain_statuses.items())
            if any(feature.country_id == country_id and feature.domain == domain for feature in country_features)
        }
        country_uncertainty = _build_country_uncertainty(run_state)
        country_profile = build_country_profile_read_model(
            country_id=country_id,
            multi_domain_status=multi_domain_status,
            domain_states=country_domain_states,
            trends={"yearly": []},
            drivers=sorted(feature.feature_id for feature in country_features),
            linked_events=[],
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
            annotations=[],
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
            domain_read_model = build_domain_detail_read_model(
                country_id=country_id,
                domain=domain,
                time_series=[
                    {"timestamp": record.timestamp, "signal_key": record.signal_key, "value": record.value}
                    for record in domain_records
                ],
                baseline_comparison={
                    "current_window": _mean([record.value for record in domain_records]),
                    "delta_to_baseline": domain_statuses[domain].anomaly_score,
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
                uncertainty=list(domain_statuses[domain].uncertainty_indicators),
            )
            domain_path = domain_details_dir / f"{country_id}__{domain}.json"
            domain_path.write_text(json.dumps(domain_read_model, indent=2, sort_keys=True))
            readmodel_paths.append(domain_path)

    source_coverage_path = readmodels_dir / "source_coverage.json"
    source_coverage_path.write_text(
        json.dumps(
            build_source_coverage_read_model(
                [_build_source_coverage_row(record) for record in fetch_metadata_records],
                missing_sources=[],
            ),
            indent=2,
            sort_keys=True,
        )
    )
    readmodel_paths.append(source_coverage_path)

    available_reports = [daily_report.report_id] + [report.report_id for _, report in sorted(country_reports_by_id.items())]
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
    }


def _build_country_uncertainty(run_state: RunState) -> list[str]:
    uncertainty: list[str] = []
    if run_state.status == "partial_success":
        uncertainty.append("partial_success")
    if run_state.failed_sources:
        uncertainty.append(f"failed_sources:{','.join(run_state.failed_sources)}")
    return uncertainty


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
