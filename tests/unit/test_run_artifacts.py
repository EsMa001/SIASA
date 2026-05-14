import json
from dataclasses import dataclass
from pathlib import Path

from siasa.adapters.base import FetchResult, SourceAdapter
from siasa.annotations.models import AnnotationRecord
from siasa.data.normalized_models import NormalizedRecord
from siasa.features.domain_a import DomainAFeatureService
from siasa.features.domain_b import DomainBFeatureService
from siasa.runs.orchestrator import DailyRunOrchestrator
from siasa.scoring.data_sufficiency import evaluate_data_sufficiency
from siasa.scoring.domain_status import derive_domain_status
from siasa.scoring.multi_domain_status import derive_multi_domain_status


@dataclass
class FakeAdapter(SourceAdapter):
    source_id: str
    domain: str
    _result: FetchResult

    def fetch(self) -> FetchResult:
        return self._result


def _normalize(source_id: str, domain: str, records: list[dict[str, float]]) -> list[NormalizedRecord]:
    normalized: list[NormalizedRecord] = []
    for index, record in enumerate(records, start=1):
        normalized.append(
            NormalizedRecord(
                normalized_id=f"NORM-{source_id}-{index}",
                country_id=str(record.get("country_id", "UKR")),
                timestamp=str(record.get("timestamp", "2026-05-11T18:00:00Z")),
                domain=domain,
                signal_key=str(record["signal_key"]),
                value=float(record["value"]),
                provenance_source_id=source_id,
                quality_context={
                    "expected_source_count": int(record.get("expected_source_count", 1)),
                    "freshness_hours": int(record.get("freshness_hours", 6)),
                },
            )
        )
    return normalized


def _domain_status_analyzer(domain: str, features):
    sufficiency = evaluate_data_sufficiency(features)
    anomaly_score = {"A": 0.7, "B": 0.3, "D": 0.1}.get(domain, 0.1)
    return derive_domain_status(domain, anomaly_score=anomaly_score, sufficiency=sufficiency)


def test_daily_run_orchestrator_writes_gui_artifact_bundle_after_successful_run(tmp_path: Path) -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"signal_key": "article_count", "value": 3.0, "expected_source_count": 1, "freshness_hours": 6},
                        {"signal_key": "tone", "value": -0.2, "expected_source_count": 1, "freshness_hours": 6},
                        {"signal_key": "topic:security", "value": 2.0, "expected_source_count": 1, "freshness_hours": 6},
                    ]
                ),
            ),
            FakeAdapter(
                source_id="SRC-B",
                domain="B",
                _result=FetchResult(
                    records=[
                        {"signal_key": "conflict_event_count", "value": 4.0, "expected_source_count": 1, "freshness_hours": 12},
                        {"signal_key": "protest_event_count", "value": 2.0, "expected_source_count": 1, "freshness_hours": 12},
                    ]
                ),
            ),
        ],
        normalizer=_normalize,
        feature_services=[DomainAFeatureService(), DomainBFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
        annotation_records=[
            AnnotationRecord(
                annotation_id="ANN-200-COUNTRY",
                created_at="2026-05-11T18:05:00Z",
                author="analyst",
                scope="country",
                annotation_type="context_note",
                severity_assessment="relevant",
                confidence_assessment="medium",
                text="Country-level review note.",
                tags=["country"],
                linked_items=["UKR"],
                review_status="draft",
            ),
            AnnotationRecord(
                annotation_id="ANN-200-DOMAIN",
                created_at="2026-05-11T18:06:00Z",
                author="analyst",
                scope="domain",
                annotation_type="lineage_note",
                severity_assessment="uncertain",
                confidence_assessment="high",
                text="Domain-level lineage note.",
                tags=["domain"],
                linked_items=["UKR:A"],
                review_status="reviewed",
            ),
            AnnotationRecord(
                annotation_id="ANN-200-SNAPSHOT",
                created_at="2026-05-11T18:07:00Z",
                author="analyst",
                scope="snapshot",
                annotation_type="review_note",
                severity_assessment="uncertain",
                confidence_assessment="low",
                text="Snapshot review note.",
                tags=["snapshot"],
                linked_items=["SNAP-RUN-200-v1"],
                review_status="unreviewed",
            ),
        ],
        artifacts_output_dir=tmp_path / "bundle",
    )

    result = orchestrator.run(run_id="RUN-200")

    assert result.artifact_bundle is not None
    assert (tmp_path / "bundle" / "snapshot.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "world_map.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "country_profiles" / "UKR.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "domain_details" / "UKR__A.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "domain_details" / "UKR__B.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "source_coverage.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "system_status.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "traceability_lineage.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "repo_closure.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "annotations.json").exists()
    assert (tmp_path / "bundle" / "reports" / "daily_snapshot.json").exists()
    assert (tmp_path / "bundle" / "reports" / "country_profile_UKR.json").exists()
    assert (tmp_path / "bundle" / "reports" / "coverage_report.json").exists()
    assert (tmp_path / "bundle" / "reports" / "domain_report_UKR_A.json").exists()
    assert (tmp_path / "bundle" / "reports" / "domain_report_UKR_B.json").exists()
    assert (tmp_path / "bundle" / "reports" / "event_report_EVT-UKR-RUN-200.json").exists()
    assert (tmp_path / "bundle" / "exports" / "daily_snapshot" / "REP-DAILY-SNAP-RUN-200-v1.md").exists()
    assert (tmp_path / "bundle" / "exports" / "daily_snapshot" / "REP-DAILY-SNAP-RUN-200-v1.json").exists()
    assert (tmp_path / "bundle" / "exports" / "country_profile" / "REP-COUNTRY-UKR.md").exists()
    assert (tmp_path / "bundle" / "exports" / "country_profile" / "REP-COUNTRY-UKR.json").exists()
    assert (tmp_path / "bundle" / "exports" / "coverage_report" / "REP-COVERAGE-RUN-200.md").exists()
    assert (tmp_path / "bundle" / "exports" / "coverage_report" / "REP-COVERAGE-RUN-200.json").exists()
    assert (tmp_path / "bundle" / "exports" / "domain_report" / "REP-DOMAIN-UKR-A.md").exists()
    assert (tmp_path / "bundle" / "exports" / "domain_report" / "REP-DOMAIN-UKR-B.json").exists()
    assert (tmp_path / "bundle" / "exports" / "event_report" / "REP-EVENT-EVT-UKR-RUN-200.md").exists()
    assert (tmp_path / "bundle" / "exports" / "event_report" / "REP-EVENT-EVT-UKR-RUN-200.json").exists()

    snapshot = json.loads((tmp_path / "bundle" / "snapshot.json").read_text())
    world_map = json.loads((tmp_path / "bundle" / "readmodels" / "world_map.json").read_text())
    country_profile = json.loads((tmp_path / "bundle" / "readmodels" / "country_profiles" / "UKR.json").read_text())
    domain_detail_a = json.loads((tmp_path / "bundle" / "readmodels" / "domain_details" / "UKR__A.json").read_text())
    system_status = json.loads((tmp_path / "bundle" / "readmodels" / "system_status.json").read_text())
    traceability = json.loads((tmp_path / "bundle" / "readmodels" / "traceability_lineage.json").read_text())
    repo_closure = json.loads((tmp_path / "bundle" / "readmodels" / "repo_closure.json").read_text())
    annotations = json.loads((tmp_path / "bundle" / "readmodels" / "annotations.json").read_text())
    daily_report = json.loads((tmp_path / "bundle" / "reports" / "daily_snapshot.json").read_text())
    coverage_report = json.loads((tmp_path / "bundle" / "reports" / "coverage_report.json").read_text())
    domain_report_a = json.loads((tmp_path / "bundle" / "reports" / "domain_report_UKR_A.json").read_text())
    event_report = json.loads((tmp_path / "bundle" / "reports" / "event_report_EVT-UKR-RUN-200.json").read_text())

    assert snapshot["snapshot_id"] == "SNAP-RUN-200-v1"
    assert world_map["countries"] == [{"country_id": "UKR", "status": "S3", "active_domains": ["A", "B"], "drill_down_target": "/countries/UKR"}]
    assert country_profile["multi_domain_status"] == "S3"
    assert country_profile["domain_states"] == {"A": "D3", "B": "D2"}
    assert country_profile["drivers"]
    assert country_profile["linked_events"] == ["EVT-UKR-RUN-200"]
    assert country_profile["annotations"] == ["ANN-200-COUNTRY"]
    assert domain_detail_a["annotations"] == ["ANN-200-DOMAIN"]
    assert system_status["available_reports"] == ["REP-COUNTRY-UKR", "REP-COVERAGE-RUN-200", "REP-DAILY-SNAP-RUN-200-v1", "REP-DOMAIN-UKR-A", "REP-DOMAIN-UKR-B", "REP-EVENT-EVT-UKR-RUN-200"]
    assert coverage_report["report_id"] == "REP-COVERAGE-RUN-200"
    assert coverage_report["payload"]["run_id"] == "RUN-200"
    assert coverage_report["payload"]["failed_sources"] == []
    assert domain_report_a["report_id"] == "REP-DOMAIN-UKR-A"
    assert domain_report_a["payload"]["source_state"] == {"SRC-A": "success"}
    assert event_report["report_id"] == "REP-EVENT-EVT-UKR-RUN-200"
    assert event_report["payload"]["related_domains"] == ["B"]
    assert event_report["payload"]["source_state"] == {"SRC-B": "success"}
    assert "REP-COVERAGE-RUN-200" in traceability["lineage_records"][0]["report_ids"]
    assert "REP-COUNTRY-UKR" in traceability["lineage_records"][0]["report_ids"]
    assert repo_closure["summary"] == {"slice_count": 9, "requirement_count": 45, "closed": 45, "at_risk": 0}
    assert repo_closure["slice_ids"] == [
        "baseline-and-status-engines",
        "catalog-and-ingestion-foundation",
        "feature-computation-foundation",
        "governance-and-run-controls",
        "gui-readmodels-and-annotations",
        "normalization-and-mapping",
        "reporting-and-export",
        "snapshot-and-lineage",
        "validation-and-backtest",
    ]
    assert traceability["lineage_records"][0]["raw_record_id"] == "RAW-SRC-A-1"
    assert traceability["lineage_records"][0]["report_id"] == "REP-DAILY-SNAP-RUN-200-v1"
    assert annotations["by_linked_item"]["UKR"] == ["ANN-200-COUNTRY"]
    assert annotations["by_linked_item"]["UKR:A"] == ["ANN-200-DOMAIN"]
    assert annotations["by_scope"]["snapshot"] == ["ANN-200-SNAPSHOT"]
    assert daily_report["report_id"] == "REP-DAILY-SNAP-RUN-200-v1"
    assert daily_report["payload"]["snapshot_id"] == "SNAP-RUN-200-v1"
    assert daily_report["export_files"][0]["relative_path"] == "exports/daily_snapshot/REP-DAILY-SNAP-RUN-200-v1.md"
    assert json.loads((tmp_path / "bundle" / "exports" / "daily_snapshot" / "REP-DAILY-SNAP-RUN-200-v1.json").read_text())["snapshot_id"] == "SNAP-RUN-200-v1"



def test_daily_run_orchestrator_writes_multi_country_artifact_bundle(tmp_path: Path) -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"country_id": "UKR", "signal_key": "article_count", "value": 3.0, "expected_source_count": 1, "freshness_hours": 6},
                        {"country_id": "UKR", "signal_key": "tone", "value": -0.2, "expected_source_count": 1, "freshness_hours": 6},
                        {"country_id": "POL", "signal_key": "article_count", "value": 5.0, "expected_source_count": 1, "freshness_hours": 8},
                        {"country_id": "POL", "signal_key": "tone", "value": 0.1, "expected_source_count": 1, "freshness_hours": 8},
                    ]
                ),
            ),
            FakeAdapter(
                source_id="SRC-B",
                domain="B",
                _result=FetchResult(
                    records=[
                        {"country_id": "UKR", "signal_key": "conflict_event_count", "value": 4.0, "expected_source_count": 1, "freshness_hours": 12},
                        {"country_id": "POL", "signal_key": "conflict_event_count", "value": 1.0, "expected_source_count": 1, "freshness_hours": 10},
                    ]
                ),
            ),
        ],
        normalizer=_normalize,
        feature_services=[DomainAFeatureService(), DomainBFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
        artifacts_output_dir=tmp_path / "bundle-multi",
    )

    result = orchestrator.run(run_id="RUN-201")

    world_map = json.loads((tmp_path / "bundle-multi" / "readmodels" / "world_map.json").read_text())
    system_status = json.loads((tmp_path / "bundle-multi" / "readmodels" / "system_status.json").read_text())
    pol_profile = json.loads((tmp_path / "bundle-multi" / "readmodels" / "country_profiles" / "POL.json").read_text())
    ukr_profile = json.loads((tmp_path / "bundle-multi" / "readmodels" / "country_profiles" / "UKR.json").read_text())

    assert result.artifact_bundle is not None
    assert [country["country_id"] for country in world_map["countries"]] == ["POL", "UKR"]
    assert system_status["coverage"] == {"countries_total": 2, "countries_with_updates": 2}
    assert sorted(result.country_reports) == ["POL", "UKR"]
    assert pol_profile["multi_domain_status"] == "S3"
    assert ukr_profile["multi_domain_status"] == "S3"



def test_daily_run_orchestrator_writes_partial_success_bundle_with_failed_source_context(tmp_path: Path) -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"signal_key": "article_count", "value": 3.0, "expected_source_count": 1, "freshness_hours": 6},
                        {"signal_key": "tone", "value": -0.2, "expected_source_count": 1, "freshness_hours": 6},
                        {"signal_key": "topic:security", "value": 2.0, "expected_source_count": 1, "freshness_hours": 6},
                    ]
                ),
            ),
            FakeAdapter(
                source_id="SRC-B",
                domain="B",
                _result=FetchResult(records=[], diagnostics="timeout", is_success=False),
            ),
        ],
        normalizer=_normalize,
        feature_services=[DomainAFeatureService(), DomainBFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
        annotation_records=[
            AnnotationRecord(
                annotation_id="ANN-200-COUNTRY",
                created_at="2026-05-11T18:05:00Z",
                author="analyst",
                scope="country",
                annotation_type="context_note",
                severity_assessment="relevant",
                confidence_assessment="medium",
                text="Country-level review note.",
                tags=["country"],
                linked_items=["UKR"],
                review_status="draft",
            ),
            AnnotationRecord(
                annotation_id="ANN-200-DOMAIN",
                created_at="2026-05-11T18:06:00Z",
                author="analyst",
                scope="domain",
                annotation_type="lineage_note",
                severity_assessment="uncertain",
                confidence_assessment="high",
                text="Domain-level lineage note.",
                tags=["domain"],
                linked_items=["UKR:A"],
                review_status="reviewed",
            ),
            AnnotationRecord(
                annotation_id="ANN-200-SNAPSHOT",
                created_at="2026-05-11T18:07:00Z",
                author="analyst",
                scope="snapshot",
                annotation_type="review_note",
                severity_assessment="uncertain",
                confidence_assessment="low",
                text="Snapshot review note.",
                tags=["snapshot"],
                linked_items=["SNAP-RUN-200-v1"],
                review_status="unreviewed",
            ),
        ],
        artifacts_output_dir=tmp_path / "bundle",
    )

    result = orchestrator.run(run_id="RUN-201")

    assert result.artifact_bundle is not None

    source_coverage = json.loads((tmp_path / "bundle" / "readmodels" / "source_coverage.json").read_text())
    country_profile = json.loads((tmp_path / "bundle" / "readmodels" / "country_profiles" / "UKR.json").read_text())
    system_status = json.loads((tmp_path / "bundle" / "readmodels" / "system_status.json").read_text())

    assert source_coverage["failed_sources"] == ["SRC-B"]
    assert country_profile["uncertainty"] == ["partial_success", "failed_sources:SRC-B"]
    assert system_status["run_status"] == "partial_success"
    assert system_status["failed_sources"] == ["SRC-B"]
