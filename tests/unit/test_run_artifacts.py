import json
from dataclasses import dataclass
from pathlib import Path

from siasa.adapters.base import FetchResult, SourceAdapter
from siasa.annotations.models import AnnotationRecord
from siasa.data.normalized_models import NormalizedRecord
from siasa.features.domain_a import DomainAFeatureService
from siasa.features.domain_b import DomainBFeatureService
from siasa.runs.artifacts import _build_country_coverage_visibility, _load_country_metadata
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


@dataclass
class ScopedFakeAdapter(SourceAdapter):
    source_id: str
    domain: str
    country_ids: tuple[str, ...]
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



def test_load_country_metadata_returns_empty_mapping_when_governed_file_is_unavailable(tmp_path: Path) -> None:
    assert _load_country_metadata(tmp_path) == {}



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
    assert (tmp_path / "bundle" / "readmodels" / "readiness.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "traceability_integrity.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "stakeholder_functional_closure.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "release_gate.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "approval_lifecycle_record.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "stakeholder_e2e_flow_coverage.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "stakeholder_e2e_ui_smoke.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "stakeholder_browser_e2e_acceptance.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "stakeholder_browser_interaction_depth.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "stakeholder_browser_failure_resilience.json").exists()
    assert (tmp_path / "bundle" / "readmodels" / "release_readiness_index.json").exists()
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
    readiness = json.loads((tmp_path / "bundle" / "readmodels" / "readiness.json").read_text())
    traceability_integrity = json.loads((tmp_path / "bundle" / "readmodels" / "traceability_integrity.json").read_text())
    stakeholder_functional_closure = json.loads((tmp_path / "bundle" / "readmodels" / "stakeholder_functional_closure.json").read_text())
    release_gate = json.loads((tmp_path / "bundle" / "readmodels" / "release_gate.json").read_text())
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
    assert system_status["artifact_status"]["validation_backtest"] == {
        "status": "absent",
        "reason": "not_configured",
    }
    assert readiness["run_id"] == "RUN-200"
    assert readiness["snapshot_id"] == "SNAP-RUN-200-v1"
    assert readiness["demo_verdict"] == "blocked"
    assert readiness["release_verdict"] == "blocked_by_known_gaps"
    assert readiness["known_gaps"] == ["validation_backtest_absent:not_configured"]
    assert traceability_integrity["summary"]["requirement_count"] == 68
    assert stakeholder_functional_closure["focus_gap_cluster"] == {
        "stakeholder_ids": [
            "StR-001", "StR-002", "StR-004", "StR-007", "StR-024", "StR-025",
            "StR-135", "StR-136", "StR-137", "StR-138", "StR-139", "StR-140", "StR-141", "StR-142",
            "StR-226", "StR-227", "StR-228", "StR-229", "StR-230",
        ],
        "covered_count": 19,
        "implemented_count": 19,
        "not_implemented_count": 0,
        "not_implemented_ids": [],
    }
    assert release_gate["gate_verdict"] == "no_go"
    assert "release_verdict_ready" in release_gate["blockers"]
    assert "known_gaps_clear" in release_gate["blockers"]
    assert readiness["artifact_checks"][0] == {
        "artifact": "validation_backtest",
        "status": "absent",
        "reason": "not_configured",
    }
    assert domain_report_a["report_id"] == "REP-DOMAIN-UKR-A"
    assert domain_report_a["payload"]["source_state"] == {"SRC-A": "success"}
    assert event_report["report_id"] == "REP-EVENT-EVT-UKR-RUN-200"
    assert event_report["payload"]["related_domains"] == ["B"]
    assert event_report["payload"]["source_state"] == {"SRC-B": "success"}
    assert "REP-COVERAGE-RUN-200" in traceability["lineage_records"][0]["report_ids"]
    assert "REP-COUNTRY-UKR" in traceability["lineage_records"][0]["report_ids"]
    assert repo_closure["summary"] == {"slice_count": 10, "requirement_count": 70, "closed": 70, "at_risk": 0}
    assert repo_closure["slice_ids"] == [
        "baseline-and-status-engines",
        "catalog-and-ingestion-foundation",
        "feature-computation-foundation",
        "governance-and-run-controls",
        "gui-readmodels-and-annotations",
        "ml-training-data-lake",
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



def test_daily_run_orchestrator_cleans_stale_artifacts_before_writing_new_bundle(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle-clean"
    stale_readmodels = bundle_dir / "readmodels"
    stale_country_profiles = stale_readmodels / "country_profiles"
    stale_domain_details = stale_readmodels / "domain_details"
    stale_reports = bundle_dir / "reports"
    stale_exports = bundle_dir / "exports" / "domain_report"
    stale_country_profiles.mkdir(parents=True)
    stale_domain_details.mkdir(parents=True)
    stale_reports.mkdir(parents=True)
    stale_exports.mkdir(parents=True)
    (bundle_dir / "snapshot.json").write_text('{"snapshot_id": "STALE"}')
    (stale_readmodels / "world_map.json").write_text('{"countries": ["STALE"]}')
    (stale_country_profiles / "STALE.json").write_text('{"country_id": "STALE"}')
    (stale_domain_details / "STALE__A.json").write_text('{"country_id": "STALE", "domain": "A"}')
    (stale_reports / "old_report.json").write_text('{"report_id": "OLD"}')
    (stale_exports / "OLD.md").write_text('stale')
    (stale_exports / "OLD.json").write_text('{"stale": true}')

    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"signal_key": "article_count", "value": 3.0, "expected_source_count": 1, "freshness_hours": 6},
                        {"signal_key": "tone", "value": -0.2, "expected_source_count": 1, "freshness_hours": 6},
                    ]
                ),
            ),
            FakeAdapter(
                source_id="SRC-B",
                domain="B",
                _result=FetchResult(
                    records=[
                        {"signal_key": "conflict_event_count", "value": 4.0, "expected_source_count": 1, "freshness_hours": 12},
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
        artifacts_output_dir=bundle_dir,
    )

    result = orchestrator.run(run_id="RUN-200A")

    assert result.artifact_bundle is not None
    assert not (stale_country_profiles / "STALE.json").exists()
    assert not (stale_domain_details / "STALE__A.json").exists()
    assert not (stale_reports / "old_report.json").exists()
    assert not (stale_exports / "OLD.md").exists()
    assert not (stale_exports / "OLD.json").exists()
    assert json.loads((bundle_dir / "snapshot.json").read_text())["snapshot_id"] == "SNAP-RUN-200A-v1"



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
    assert [country["active_domains"] for country in world_map["countries"]] == [["A", "B"], ["A", "B"]]
    assert system_status["coverage"] == {
        "countries_total": 2,
        "countries_with_updates": 2,
        "countries_without_updates": [],
    }
    assert system_status["country_coverage_visibility"] == {
        "priority_summary": [
            {"priority": "P1", "country_count": 1, "countries": ["UKR"]},
            {"priority": "P2", "country_count": 1, "countries": ["POL"]},
        ],
        "source_depth_band_summary": [
            {"band": "minimal", "country_count": 0, "countries": []},
            {"band": "moderate", "country_count": 2, "countries": ["POL", "UKR"]},
            {"band": "deep", "country_count": 0, "countries": []},
        ],
        "freshness_band_summary": [
            {"band": "fresh", "country_count": 2, "countries": ["POL", "UKR"]},
            {"band": "aging", "country_count": 0, "countries": []},
            {"band": "stale", "country_count": 0, "countries": []},
            {"band": "unknown", "country_count": 0, "countries": []},
        ],
        "country_freshness_rows": [
            {"country_id": "POL", "freshness_hours": 10.0, "freshness_band": "fresh", "priority": "P2", "source_depth_band": "moderate"},
            {"country_id": "UKR", "freshness_hours": 12.0, "freshness_band": "fresh", "priority": "P1", "source_depth_band": "moderate"},
        ],
        "country_gap_rows": [],
        "missing_domain_totals": {},
        "remediation_watchlist": [],
        "stale_priority_summary": {
            "stale_country_count": 0,
            "p1_stale_count": 0,
            "p2_stale_count": 0,
            "p3_stale_count": 0,
        },
        "stale_priority_watchlist": [],
    }
    assert sorted(result.country_reports) == ["POL", "UKR"]
    assert pol_profile["multi_domain_status"] == "S3"
    assert ukr_profile["multi_domain_status"] == "S3"
    assert pol_profile["trends"]["yearly"]
    assert ukr_profile["trends"]["yearly"]
    assert pol_profile["trends"]["yearly"][0]["label"]
    assert isinstance(pol_profile["trends"]["yearly"][0]["value"], float)
    # Per-domain trend series (new: distinct series per domain)
    assert "yearly_by_domain" in pol_profile["trends"]
    assert "yearly_by_domain" in ukr_profile["trends"]
    pol_domains = pol_profile["trends"]["yearly_by_domain"]
    assert isinstance(pol_domains, dict)
    assert len(pol_domains) > 0, "Expected at least one domain in yearly_by_domain"
    for domain, series in pol_domains.items():
        assert isinstance(domain, str)
        assert len(domain) == 1, f"Domain keys should be single letters, got {domain}"
        assert len(series) > 0
        assert series[0]["label"]
        assert isinstance(series[0]["value"], float)



def test_daily_run_orchestrator_records_country_gap_visibility_in_system_status(tmp_path: Path) -> None:
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
        artifacts_output_dir=tmp_path / "bundle-gap-visibility",
    )

    result = orchestrator.run(run_id="RUN-204")

    system_status = json.loads((tmp_path / "bundle-gap-visibility" / "readmodels" / "system_status.json").read_text())
    pol_profile = json.loads((tmp_path / "bundle-gap-visibility" / "readmodels" / "country_profiles" / "POL.json").read_text())

    assert result.artifact_bundle is not None
    assert pol_profile["domain_gap_summary"]["missing_domains"] == ["B"]
    assert pol_profile["domain_gap_summary"]["gap_details"] == [
        {
            "domain": "B",
            "reason": "no_usable_input_data",
            "source_ids": ["SRC-B"],
            "diagnostics_by_source": {},
            "source_reason_details": [{"source_id": "SRC-B", "reason": "records_only_for_other_countries_in_scope", "diagnostics": "", "action_category": "scope_config_problem", "severity": "medium"}],
        }
    ]
    assert system_status["country_coverage_visibility"]["country_gap_rows"] == [
        {
            "country_id": "POL",
            "priority": "P2",
            "source_count": 1,
            "source_depth_band": "minimal",
            "freshness_hours": 8.0,
            "freshness_band": "fresh",
            "missing_domains": ["B"],
            "missing_domain_count": 1,
            "gap_details": [
                {
                    "domain": "B",
                    "reason": "no_usable_input_data",
                    "source_ids": ["SRC-B"],
                    "diagnostics_by_source": {},
                    "source_reason_details": [{"source_id": "SRC-B", "reason": "records_only_for_other_countries_in_scope", "diagnostics": "", "action_category": "scope_config_problem", "severity": "medium"}],
                }
            ],
        }
    ]
    assert system_status["country_coverage_visibility"]["remediation_watchlist"] == [
        {
            "priority_rank": 1,
            "priority_score": 111,
            "action_category": "scope_config_problem",
            "severity": "medium",
            "country_count": 1,
            "source_count": 1,
            "countries": ["POL"],
            "source_ids": ["SRC-B"],
            "suggested_next_action": "Review country scope and source applicability configuration for the affected source.",
            "owner_hint": "runtime/source configuration",
            "evidence_link": "coverage.html#source-SRC-B",
        }
    ]
    assert system_status["country_coverage_visibility"]["missing_domain_totals"] == {"B": 1}
    assert system_status["country_coverage_visibility"]["freshness_band_summary"] == [
        {"band": "fresh", "country_count": 2, "countries": ["POL", "UKR"]},
        {"band": "aging", "country_count": 0, "countries": []},
        {"band": "stale", "country_count": 0, "countries": []},
        {"band": "unknown", "country_count": 0, "countries": []},
    ]
    assert system_status["country_coverage_visibility"]["country_freshness_rows"] == [
        {"country_id": "POL", "freshness_hours": 8.0, "freshness_band": "fresh", "priority": "P2", "source_depth_band": "minimal"},
        {"country_id": "UKR", "freshness_hours": 12.0, "freshness_band": "fresh", "priority": "P1", "source_depth_band": "moderate"},
    ]
    assert system_status["country_coverage_visibility"]["stale_priority_summary"] == {
        "stale_country_count": 0,
        "p1_stale_count": 0,
        "p2_stale_count": 0,
        "p3_stale_count": 0,
    }
    assert system_status["country_coverage_visibility"]["stale_priority_watchlist"] == []



def test_build_country_coverage_visibility_assigns_priority_scores_and_stable_ranking() -> None:
    visibility = _build_country_coverage_visibility(
        [
            {
                "country_id": "UKR",
                "priority": "P1",
                "source_count": 2,
                "source_depth_band": "moderate",
                "missing_domains": ["A"],
                "missing_domain_count": 1,
                "gap_details": [
                    {
                        "domain": "A",
                        "reason": "source_failed_this_run",
                        "source_ids": ["SRC-X", "SRC-Y"],
                        "diagnostics_by_source": {},
                        "source_reason_details": [
                            {"source_id": "SRC-X", "reason": "source_failed_this_run", "diagnostics": "timeout", "action_category": "fetch_problem", "severity": "high"},
                            {"source_id": "SRC-Y", "reason": "source_failed_this_run", "diagnostics": "timeout", "action_category": "fetch_problem", "severity": "high"},
                        ],
                    }
                ],
            },
            {
                "country_id": "POL",
                "priority": "P2",
                "source_count": 1,
                "source_depth_band": "minimal",
                "missing_domains": ["B"],
                "missing_domain_count": 1,
                "gap_details": [
                    {
                        "domain": "B",
                        "reason": "no_usable_input_data",
                        "source_ids": ["SRC-B"],
                        "diagnostics_by_source": {},
                        "source_reason_details": [
                            {"source_id": "SRC-B", "reason": "records_only_for_other_countries_in_scope", "diagnostics": "ukr_only_window", "action_category": "scope_config_problem", "severity": "medium"},
                        ],
                    }
                ],
            },
            {
                "country_id": "TWN",
                "priority": "P2",
                "source_count": 1,
                "source_depth_band": "minimal",
                "missing_domains": ["B"],
                "missing_domain_count": 1,
                "gap_details": [
                    {
                        "domain": "B",
                        "reason": "no_usable_input_data",
                        "source_ids": ["SRC-B"],
                        "diagnostics_by_source": {},
                        "source_reason_details": [
                            {"source_id": "SRC-B", "reason": "records_only_for_other_countries_in_scope", "diagnostics": "ukr_only_window", "action_category": "scope_config_problem", "severity": "medium"},
                        ],
                    }
                ],
            },
        ]
    )

    assert visibility["remediation_watchlist"] == [
        {
            "priority_rank": 1,
            "priority_score": 212,
            "action_category": "fetch_problem",
            "severity": "high",
            "country_count": 1,
            "source_count": 2,
            "countries": ["UKR"],
            "source_ids": ["SRC-X", "SRC-Y"],
            "suggested_next_action": "Retry adapter execution and inspect source-side rate limiting or transport failures.",
            "owner_hint": "adapter/source integration",
            "evidence_link": "coverage.html",
        },
        {
            "priority_rank": 2,
            "priority_score": 121,
            "action_category": "scope_config_problem",
            "severity": "medium",
            "country_count": 2,
            "source_count": 1,
            "countries": ["POL", "TWN"],
            "source_ids": ["SRC-B"],
            "suggested_next_action": "Review country scope and source applicability configuration for the affected source.",
            "owner_hint": "runtime/source configuration",
            "evidence_link": "coverage.html#source-SRC-B",
        },
    ]
    assert visibility["stale_priority_summary"] == {
        "stale_country_count": 0,
        "p1_stale_count": 0,
        "p2_stale_count": 0,
        "p3_stale_count": 0,
    }
    assert visibility["stale_priority_watchlist"] == []



def test_build_country_coverage_visibility_builds_stale_priority_watchlist_by_priority_then_staleness() -> None:
    visibility = _build_country_coverage_visibility(
        [
            {
                "country_id": "UKR",
                "priority": "P1",
                "freshness_hours": 8760.0,
                "freshness_band": "stale",
                "source_depth_band": "moderate",
                "source_count": 2,
                "missing_domains": [],
                "missing_domain_count": 0,
                "gap_details": [],
            },
            {
                "country_id": "POL",
                "priority": "P2",
                "freshness_hours": 300.0,
                "freshness_band": "stale",
                "source_depth_band": "minimal",
                "source_count": 1,
                "missing_domains": [],
                "missing_domain_count": 0,
                "gap_details": [],
            },
            {
                "country_id": "CAN",
                "priority": "P2",
                "freshness_hours": 1200.0,
                "freshness_band": "stale",
                "source_depth_band": "moderate",
                "source_count": 1,
                "missing_domains": [],
                "missing_domain_count": 0,
                "gap_details": [],
            },
            {
                "country_id": "AUS",
                "priority": "P3",
                "freshness_hours": 1000.0,
                "freshness_band": "stale",
                "source_depth_band": "minimal",
                "source_count": 1,
                "missing_domains": [],
                "missing_domain_count": 0,
                "gap_details": [],
            },
        ]
    )

    assert visibility["stale_priority_summary"] == {
        "stale_country_count": 4,
        "p1_stale_count": 1,
        "p2_stale_count": 2,
        "p3_stale_count": 1,
    }
    assert visibility["stale_priority_watchlist"] == [
        {"priority_rank": 1, "country_id": "UKR", "priority": "P1", "freshness_hours": 8760.0, "source_depth_band": "moderate"},
        {"priority_rank": 2, "country_id": "CAN", "priority": "P2", "freshness_hours": 1200.0, "source_depth_band": "moderate"},
        {"priority_rank": 3, "country_id": "POL", "priority": "P2", "freshness_hours": 300.0, "source_depth_band": "minimal"},
        {"priority_rank": 4, "country_id": "AUS", "priority": "P3", "freshness_hours": 1000.0, "source_depth_band": "minimal"},
    ]



def test_build_country_coverage_visibility_breaks_equal_priority_scores_deterministically() -> None:
    visibility = _build_country_coverage_visibility(
        [
            {
                "country_id": country_id,
                "priority": "P2",
                "source_count": 1,
                "source_depth_band": "minimal",
                "missing_domains": ["A"],
                "missing_domain_count": 1,
                "gap_details": [
                    {
                        "domain": "A",
                        "reason": "zero_records_returned",
                        "source_ids": ["SRC-M"],
                        "diagnostics_by_source": {},
                        "source_reason_details": [
                            {"source_id": "SRC-M", "reason": "zero_records_returned", "diagnostics": "", "action_category": "fetch_problem", "severity": "medium"},
                        ],
                    }
                ],
            }
            for country_id in [
                "ARG", "BRA", "CAN", "DEU", "ESP", "FRA", "GRC", "HUN", "ITA", "JPN", "KEN",
            ]
        ]
        + [
            {
                "country_id": "UKR",
                "priority": "P1",
                "source_count": 1,
                "source_depth_band": "minimal",
                "missing_domains": ["A"],
                "missing_domain_count": 1,
                "gap_details": [
                    {
                        "domain": "A",
                        "reason": "source_failed_this_run",
                        "source_ids": ["SRC-H"],
                        "diagnostics_by_source": {},
                        "source_reason_details": [
                            {"source_id": "SRC-H", "reason": "source_failed_this_run", "diagnostics": "timeout", "action_category": "fetch_problem", "severity": "high"},
                        ],
                    }
                ],
            }
        ]
    )

    assert [
        (row["priority_rank"], row["priority_score"], row["action_category"], row["severity"], row["countries"])
        for row in visibility["remediation_watchlist"]
    ] == [
        (1, 211, "fetch_problem", "high", ["UKR"]),
        (2, 211, "fetch_problem", "medium", ["ARG", "BRA", "CAN", "DEU", "ESP", "FRA", "GRC", "HUN", "ITA", "JPN", "KEN"]),
    ]



def test_daily_run_orchestrator_respects_country_specific_expected_domains(tmp_path: Path) -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"country_id": "TWN", "signal_key": "article_count", "value": 7.0, "expected_source_count": 1, "freshness_hours": 6},
                        {"country_id": "TWN", "signal_key": "tone", "value": -0.3, "expected_source_count": 1, "freshness_hours": 6},
                    ]
                ),
            ),
            FakeAdapter(
                source_id="SRC-B",
                domain="B",
                _result=FetchResult(
                    records=[
                        {"country_id": "TWN", "signal_key": "conflict_event_count", "value": 2.0, "expected_source_count": 1, "freshness_hours": 4},
                    ]
                ),
            ),
        ],
        normalizer=_normalize,
        feature_services=[DomainAFeatureService(), DomainBFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B", "D"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
        artifacts_output_dir=tmp_path / "bundle-country-expected-domains",
        country_expected_domains={"TWN": ["A", "B"]},
    )

    result = orchestrator.run(run_id="RUN-204A")

    world_map = json.loads((tmp_path / "bundle-country-expected-domains" / "readmodels" / "world_map.json").read_text())
    twn_profile = json.loads((tmp_path / "bundle-country-expected-domains" / "readmodels" / "country_profiles" / "TWN.json").read_text())
    system_status = json.loads((tmp_path / "bundle-country-expected-domains" / "readmodels" / "system_status.json").read_text())

    assert result.artifact_bundle is not None
    assert world_map["countries"] == [{"country_id": "TWN", "status": "S3", "active_domains": ["A", "B"], "drill_down_target": "/countries/TWN"}]
    assert twn_profile["configured_domains"] == ["A", "B"]
    assert twn_profile["domain_gap_summary"] == {"expected_domains": ["A", "B"], "observed_domains": ["A", "B"], "missing_domains": []}
    assert system_status["country_coverage_visibility"]["country_gap_rows"] == []



def test_daily_run_orchestrator_uses_country_specific_source_scope_for_gap_reasons(tmp_path: Path) -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"country_id": "POL", "signal_key": "article_count", "value": 5.0, "expected_source_count": 1, "freshness_hours": 8},
                        {"country_id": "POL", "signal_key": "tone", "value": 0.1, "expected_source_count": 1, "freshness_hours": 8},
                    ]
                ),
            ),
            ScopedFakeAdapter(
                source_id="SRC-B",
                domain="B",
                country_ids=("UKR",),
                _result=FetchResult(
                    records=[
                        {"country_id": "UKR", "signal_key": "conflict_event_count", "value": 4.0, "expected_source_count": 1, "freshness_hours": 12},
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
        artifacts_output_dir=tmp_path / "bundle-country-scope",
    )

    result = orchestrator.run(run_id="RUN-205")

    system_status = json.loads((tmp_path / "bundle-country-scope" / "readmodels" / "system_status.json").read_text())
    pol_profile = json.loads((tmp_path / "bundle-country-scope" / "readmodels" / "country_profiles" / "POL.json").read_text())

    assert result.artifact_bundle is not None
    assert pol_profile["domain_gap_summary"]["gap_details"] == [
        {"domain": "B", "reason": "not_configured_for_runtime", "source_ids": [], "diagnostics_by_source": {}, "source_reason_details": []}
    ]
    assert system_status["country_coverage_visibility"]["country_gap_rows"][0]["gap_details"] == [
        {"domain": "B", "reason": "not_configured_for_runtime", "source_ids": [], "diagnostics_by_source": {}, "source_reason_details": []}
    ]



def test_daily_run_orchestrator_marks_failed_source_gap_causes(tmp_path: Path) -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"country_id": "POL", "signal_key": "article_count", "value": 5.0, "expected_source_count": 1, "freshness_hours": 8},
                        {"country_id": "POL", "signal_key": "tone", "value": 0.1, "expected_source_count": 1, "freshness_hours": 8},
                    ]
                ),
            ),
            ScopedFakeAdapter(
                source_id="SRC-B",
                domain="B",
                country_ids=("POL",),
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
        artifacts_output_dir=tmp_path / "bundle-failed-source-gap",
    )

    result = orchestrator.run(run_id="RUN-205A")
    pol_profile = json.loads((tmp_path / "bundle-failed-source-gap" / "readmodels" / "country_profiles" / "POL.json").read_text())

    assert result.artifact_bundle is not None
    assert pol_profile["domain_gap_summary"]["gap_details"] == [
        {
            "domain": "B",
            "reason": "source_failed_this_run",
            "source_ids": ["SRC-B"],
            "diagnostics_by_source": {"SRC-B": "timeout"},
            "source_reason_details": [{"source_id": "SRC-B", "reason": "source_failed_this_run", "diagnostics": "timeout", "action_category": "fetch_problem", "severity": "high"}],
        }
    ]



def test_daily_run_orchestrator_marks_zero_record_gap_causes(tmp_path: Path) -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"country_id": "POL", "signal_key": "article_count", "value": 5.0, "expected_source_count": 1, "freshness_hours": 8},
                        {"country_id": "POL", "signal_key": "tone", "value": 0.1, "expected_source_count": 1, "freshness_hours": 8},
                    ]
                ),
            ),
            ScopedFakeAdapter(source_id="SRC-B", domain="B", country_ids=("POL",), _result=FetchResult(records=[], diagnostics="empty_window", is_success=True)),
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
        artifacts_output_dir=tmp_path / "bundle-zero-records",
    )

    result = orchestrator.run(run_id="RUN-206")
    pol_profile = json.loads((tmp_path / "bundle-zero-records" / "readmodels" / "country_profiles" / "POL.json").read_text())

    assert result.artifact_bundle is not None
    assert pol_profile["domain_gap_summary"]["gap_details"] == [
        {
            "domain": "B",
            "reason": "zero_records_returned",
            "source_ids": ["SRC-B"],
            "diagnostics_by_source": {"SRC-B": "empty_window"},
            "source_reason_details": [{"source_id": "SRC-B", "reason": "zero_records_returned", "diagnostics": "empty_window", "action_category": "fetch_problem", "severity": "medium"}],
        }
    ]



def test_daily_run_orchestrator_marks_filtered_record_gap_causes(tmp_path: Path) -> None:
    def _dropping_normalizer(source_id: str, domain: str, records: list[dict[str, float]]) -> list[NormalizedRecord]:
        if source_id == "SRC-B":
            return []
        return _normalize(source_id, domain, records)

    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"country_id": "POL", "signal_key": "article_count", "value": 5.0, "expected_source_count": 1, "freshness_hours": 8},
                        {"country_id": "POL", "signal_key": "tone", "value": 0.1, "expected_source_count": 1, "freshness_hours": 8},
                    ]
                ),
            ),
            ScopedFakeAdapter(
                source_id="SRC-B",
                domain="B",
                country_ids=("POL",),
                _result=FetchResult(records=[{"country_id": "POL", "signal_key": "conflict_event_count", "value": 2.0, "expected_source_count": 1, "freshness_hours": 12}], diagnostics="fetched_but_filtered", is_success=True),
            ),
        ],
        normalizer=_dropping_normalizer,
        feature_services=[DomainAFeatureService(), DomainBFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
        artifacts_output_dir=tmp_path / "bundle-filtered-records",
    )

    result = orchestrator.run(run_id="RUN-207")
    pol_profile = json.loads((tmp_path / "bundle-filtered-records" / "readmodels" / "country_profiles" / "POL.json").read_text())

    assert result.artifact_bundle is not None
    assert pol_profile["domain_gap_summary"]["gap_details"] == [
        {
            "domain": "B",
            "reason": "records_filtered_out_or_not_mapped",
            "source_ids": ["SRC-B"],
            "diagnostics_by_source": {"SRC-B": "fetched_but_filtered"},
            "source_reason_details": [{"source_id": "SRC-B", "reason": "records_for_country_not_mapped_to_required_signal_set", "diagnostics": "fetched_but_filtered", "action_category": "mapping_problem", "severity": "medium"}],
        }
    ]



def test_daily_run_orchestrator_marks_stale_gap_causes(tmp_path: Path) -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"country_id": "POL", "signal_key": "article_count", "value": 5.0, "expected_source_count": 1, "freshness_hours": 8},
                        {"country_id": "POL", "signal_key": "tone", "value": 0.1, "expected_source_count": 1, "freshness_hours": 8},
                    ]
                ),
            ),
            ScopedFakeAdapter(
                source_id="SRC-B",
                domain="B",
                country_ids=("POL",),
                _result=FetchResult(records=[{"country_id": "POL", "signal_key": "conflict_event_count", "value": 2.0, "expected_source_count": 1, "freshness_hours": 400}], diagnostics="stale_b_window", is_success=True),
            ),
        ],
        normalizer=_normalize,
        feature_services=[DomainAFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
        artifacts_output_dir=tmp_path / "bundle-stale-records",
    )

    result = orchestrator.run(run_id="RUN-208")
    pol_profile = json.loads((tmp_path / "bundle-stale-records" / "readmodels" / "country_profiles" / "POL.json").read_text())

    assert result.artifact_bundle is not None
    assert pol_profile["domain_gap_summary"]["gap_details"] == [
        {
            "domain": "B",
            "reason": "stale_source_window",
            "source_ids": ["SRC-B"],
            "diagnostics_by_source": {"SRC-B": "stale_b_window"},
            "source_reason_details": [{"source_id": "SRC-B", "reason": "stale_source_window", "diagnostics": "stale_b_window", "action_category": "freshness_problem", "severity": "medium"}],
        }
    ]



def test_daily_run_orchestrator_marks_filtered_by_gate_gap_causes(tmp_path: Path) -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"country_id": "POL", "signal_key": "article_count", "value": 5.0, "expected_source_count": 1, "freshness_hours": 8},
                        {"country_id": "POL", "signal_key": "tone", "value": 0.1, "expected_source_count": 1, "freshness_hours": 8},
                    ]
                ),
            ),
            ScopedFakeAdapter(
                source_id="SRC-B",
                domain="B",
                country_ids=("POL",),
                _result=FetchResult(records=[{"country_id": "POL", "signal_key": "conflict_event_count", "value": 2.0, "expected_source_count": 1, "freshness_hours": 24}], diagnostics="fresh_but_unscored", is_success=True),
            ),
        ],
        normalizer=_normalize,
        feature_services=[DomainAFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
        artifacts_output_dir=tmp_path / "bundle-filtered-gate-records",
    )

    result = orchestrator.run(run_id="RUN-208A")
    pol_profile = json.loads((tmp_path / "bundle-filtered-gate-records" / "readmodels" / "country_profiles" / "POL.json").read_text())

    assert result.artifact_bundle is not None
    assert pol_profile["domain_gap_summary"]["gap_details"] == [
        {
            "domain": "B",
            "reason": "filtered_by_feature_or_sufficiency_gate",
            "source_ids": ["SRC-B"],
            "diagnostics_by_source": {"SRC-B": "fresh_but_unscored"},
            "source_reason_details": [{"source_id": "SRC-B", "reason": "filtered_by_feature_or_sufficiency_gate", "diagnostics": "fresh_but_unscored", "action_category": "downstream_gating_problem", "severity": "medium"}],
        }
    ]



def test_daily_run_orchestrator_decomposes_mixed_no_usable_input_data_by_source(tmp_path: Path) -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"country_id": "POL", "signal_key": "article_count", "value": 5.0, "expected_source_count": 1, "freshness_hours": 8},
                        {"country_id": "POL", "signal_key": "tone", "value": 0.1, "expected_source_count": 1, "freshness_hours": 8},
                    ]
                ),
            ),
            ScopedFakeAdapter(
                source_id="SRC-B1",
                domain="B",
                country_ids=("POL",),
                _result=FetchResult(records=[], diagnostics="empty_pol_window", is_success=True),
            ),
            ScopedFakeAdapter(
                source_id="SRC-B2",
                domain="B",
                country_ids=("POL",),
                _result=FetchResult(records=[{"country_id": "UKR", "signal_key": "conflict_event_count", "value": 4.0, "expected_source_count": 1, "freshness_hours": 12}], diagnostics="ukr_only_window", is_success=True),
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
        artifacts_output_dir=tmp_path / "bundle-mixed-no-usable-input",
    )

    result = orchestrator.run(run_id="RUN-209")
    pol_profile = json.loads((tmp_path / "bundle-mixed-no-usable-input" / "readmodels" / "country_profiles" / "POL.json").read_text())
    system_status = json.loads((tmp_path / "bundle-mixed-no-usable-input" / "readmodels" / "system_status.json").read_text())
    readiness = json.loads((tmp_path / "bundle-mixed-no-usable-input" / "readmodels" / "readiness.json").read_text())

    assert result.artifact_bundle is not None
    assert pol_profile["domain_gap_summary"]["gap_details"] == [
        {
            "domain": "B",
            "reason": "no_usable_input_data",
            "source_ids": ["SRC-B1", "SRC-B2"],
            "diagnostics_by_source": {"SRC-B1": "empty_pol_window", "SRC-B2": "ukr_only_window"},
            "source_reason_details": [
                {"source_id": "SRC-B1", "reason": "zero_records_returned", "diagnostics": "empty_pol_window", "action_category": "fetch_problem", "severity": "medium"},
                {"source_id": "SRC-B2", "reason": "records_only_for_other_countries_in_scope", "diagnostics": "ukr_only_window", "action_category": "scope_config_problem", "severity": "medium"},
            ],
        }
    ]
    assert system_status["country_coverage_visibility"]["country_gap_rows"][0]["gap_details"] == [
        {
            "domain": "B",
            "reason": "no_usable_input_data",
            "source_ids": ["SRC-B1", "SRC-B2"],
            "diagnostics_by_source": {"SRC-B1": "empty_pol_window", "SRC-B2": "ukr_only_window"},
            "source_reason_details": [
                {"source_id": "SRC-B1", "reason": "zero_records_returned", "diagnostics": "empty_pol_window", "action_category": "fetch_problem", "severity": "medium"},
                {"source_id": "SRC-B2", "reason": "records_only_for_other_countries_in_scope", "diagnostics": "ukr_only_window", "action_category": "scope_config_problem", "severity": "medium"},
            ],
        }
    ]
    assert readiness["release_verdict"] == "blocked_by_known_gaps"
    assert "country_gap:POL:B:no_usable_input_data" in readiness["known_gaps"]
    assert "validation_backtest_absent:not_configured" in readiness["known_gaps"]



def test_daily_run_orchestrator_writes_country_specific_multi_country_artifact_statuses(tmp_path: Path) -> None:
    def _country_specific_domain_status(domain: str, features):
        country_id = features[0].country_id
        if country_id == "UKR":
            return derive_domain_status(domain, anomaly_score=1.1 if domain == "A" else 0.4, sufficiency=evaluate_data_sufficiency(features))
        return derive_domain_status(domain, anomaly_score=0.1 if domain == "A" else 0.7, sufficiency=evaluate_data_sufficiency(features))

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
                        {"country_id": "UKR", "signal_key": "protest_event_count", "value": 1.0, "expected_source_count": 1, "freshness_hours": 12},
                        {"country_id": "POL", "signal_key": "conflict_event_count", "value": 1.0, "expected_source_count": 1, "freshness_hours": 10},
                        {"country_id": "POL", "signal_key": "protest_event_count", "value": 3.0, "expected_source_count": 1, "freshness_hours": 10},
                    ]
                ),
            ),
        ],
        normalizer=_normalize,
        feature_services=[DomainAFeatureService(), DomainBFeatureService()],
        domain_status_analyzer=_country_specific_domain_status,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
        artifacts_output_dir=tmp_path / "bundle-multi-distinct",
    )

    result = orchestrator.run(run_id="RUN-202")

    pol_profile = json.loads((tmp_path / "bundle-multi-distinct" / "readmodels" / "country_profiles" / "POL.json").read_text())
    ukr_profile = json.loads((tmp_path / "bundle-multi-distinct" / "readmodels" / "country_profiles" / "UKR.json").read_text())
    pol_domain_a = json.loads((tmp_path / "bundle-multi-distinct" / "readmodels" / "domain_details" / "POL__A.json").read_text())
    ukr_domain_a = json.loads((tmp_path / "bundle-multi-distinct" / "readmodels" / "domain_details" / "UKR__A.json").read_text())

    assert result.country_domain_statuses["POL"]["A"].status == "D1"
    assert result.country_domain_statuses["UKR"]["A"].status == "D4"
    assert pol_profile["domain_states"]["A"] == "D1"
    assert ukr_profile["domain_states"]["A"] == "D4"
    assert pol_domain_a["baseline_comparison"]["delta_to_baseline"] == 0.1
    assert ukr_domain_a["baseline_comparison"]["delta_to_baseline"] == 1.1



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



def test_daily_run_orchestrator_records_optional_artifact_absence_reasons(tmp_path: Path) -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[
            FakeAdapter(
                source_id="SRC-A",
                domain="A",
                _result=FetchResult(
                    records=[
                        {"country_id": "POL", "signal_key": "article_count", "value": 3.0, "expected_source_count": 1, "freshness_hours": 6},
                        {"country_id": "POL", "signal_key": "tone", "value": -0.2, "expected_source_count": 1, "freshness_hours": 6},
                    ]
                ),
            ),
            FakeAdapter(
                source_id="SRC-B",
                domain="B",
                _result=FetchResult(
                    records=[
                        {"country_id": "POL", "signal_key": "conflict_event_count", "value": 4.0, "expected_source_count": 1, "freshness_hours": 12},
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
        artifacts_output_dir=tmp_path / "bundle-absence-reasons",
        validation_view_model_builder=lambda *_args, **_kwargs: None,
    )

    result = orchestrator.run(run_id="RUN-203")

    system_status = json.loads((tmp_path / "bundle-absence-reasons" / "readmodels" / "system_status.json").read_text())
    assert result.artifact_bundle is not None
    assert system_status["artifact_status"]["validation_backtest"] == {
        "status": "absent",
        "reason": "no_usable_input_data",
    }
    assert system_status["artifact_status"]["traceability_lineage"] == {
        "status": "present",
        "reason": None,
    }
    assert system_status["artifact_status"]["repo_closure"] == {
        "status": "present",
        "reason": None,
    }
    assert system_status["artifact_status"]["annotations"] == {
        "status": "present",
        "reason": None,
    }
