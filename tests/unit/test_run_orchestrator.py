from __future__ import annotations

from dataclasses import dataclass

from siasa.adapters.base import FetchResult, SourceAdapter
from siasa.data.normalization_mappings import NormalizationMappingVersion
from siasa.data.normalization_service import normalize_records
from siasa.data.normalized_models import NormalizedRecord
from siasa.data.raw_models import RawRecord
from siasa.features.domain_a import DomainAFeatureService
from siasa.features.domain_b import DomainBFeatureService
from siasa.features.base import FeatureValue
from siasa.runs.orchestrator import DailyRunOrchestrator
from siasa.traceability.lineage import LineageRecord
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



def test_daily_run_orchestrator_uses_normalization_mapping_versions_in_snapshot_rule_context() -> None:
    adapters = [
        FakeAdapter(
            source_id="SRC-A",
            domain="A",
            _result=FetchResult(
                records=[
                    {
                        "country_id": "UKR",
                        "timestamp": "2026-05-11T18:00:00Z",
                        "signal_key": "article_count",
                        "value": 3.0,
                        "expected_source_count": 1,
                        "freshness_hours": 6,
                    },
                    {
                        "country_id": "UKR",
                        "timestamp": "2026-05-11T18:00:00Z",
                        "signal_key": "tone",
                        "value": -0.2,
                        "expected_source_count": 1,
                        "freshness_hours": 6,
                    },
                    {
                        "country_id": "UKR",
                        "timestamp": "2026-05-11T18:00:00Z",
                        "signal_key": "topic:security",
                        "value": 2.0,
                        "expected_source_count": 1,
                        "freshness_hours": 6,
                    },
                ]
            ),
        )
    ]
    mappings = [NormalizationMappingVersion(mapping_id="MAP-SRC-A-v2", source_id="SRC-A", version="v2", is_active=True)]

    orchestrator = DailyRunOrchestrator(
        adapters=adapters,
        normalizer=lambda source_id, domain, records: normalize_records(
            source_id=source_id,
            domain=domain,
            raw_records=records,
            mappings=mappings,
        ),
        feature_services=[DomainAFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    result = orchestrator.run(run_id="RUN-109")

    assert result.normalized_records[0].quality_context["mapping_version"] == "v2"
    assert result.normalized_records[0].quality_context["mapping_id"] == "MAP-SRC-A-v2"
    assert result.snapshot.rule_versions["normalization:SRC-A"] == "v2"



def test_daily_run_orchestrator_executes_end_to_end_pipeline() -> None:
    adapters = [
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
    ]

    orchestrator = DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalize,
        feature_services=[DomainAFeatureService(), DomainBFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    result = orchestrator.run(run_id="RUN-100")

    assert result.run_state.status == "success"
    assert len(result.normalized_records) == 5
    assert sorted(result.domain_statuses) == ["A", "B"]
    assert result.domain_statuses["A"].status == "D3"
    assert result.domain_statuses["B"].status == "D2"
    assert result.multi_domain_status.status == "S3"
    assert result.snapshot.snapshot_id == "SNAP-RUN-100-v1"
    assert result.snapshot.analytical_outputs["country_status"] == {"UKR": "S3"}
    assert result.daily_report.json_payload["country_status"] == {"UKR": "S3"}
    assert result.country_reports["UKR"].report_id == "REP-COUNTRY-UKR"
    assert result.country_reports["UKR"].json_payload["multi_domain_status"] == "S3"
    assert result.country_reports["UKR"].json_payload["domain_states"] == {"A": "D3", "B": "D2"}
    assert result.country_reports["UKR"].json_payload["linked_events"] == ["EVT-UKR-RUN-100"]



def test_daily_run_orchestrator_continues_after_source_failure_and_marks_partial_success() -> None:
    adapters = [
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
    ]

    orchestrator = DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalize,
        feature_services=[DomainAFeatureService(), DomainBFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    result = orchestrator.run(run_id="RUN-101")

    assert result.run_state.status == "partial_success"
    assert result.run_state.failed_sources == ["SRC-B"]
    assert result.snapshot.status == "partial_success"
    assert result.daily_report.json_payload["status"] == "partial_success"
    assert result.multi_domain_status.status == "S1"
    assert result.country_reports["UKR"].json_payload["uncertainty"] == ["partial_success", "failed_sources:SRC-B"]



def test_daily_run_orchestrator_persists_fetch_metadata_and_raw_records() -> None:
    adapters = [
        FakeAdapter(
            source_id="SRC-A",
            domain="A",
            _result=FetchResult(
                records=[
                    {"signal_key": "article_count", "value": 3.0, "expected_source_count": 1, "freshness_hours": 6},
                    {"signal_key": "tone", "value": -0.2, "expected_source_count": 1, "freshness_hours": 6},
                ],
                diagnostics="ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-B",
            domain="B",
            _result=FetchResult(records=[], diagnostics="timeout", is_success=False),
        ),
    ]

    orchestrator = DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalize,
        feature_services=[DomainAFeatureService(), DomainBFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    result = orchestrator.run(run_id="RUN-102")

    assert [record.source_id for record in result.fetch_metadata_records] == ["SRC-A", "SRC-B"]
    assert result.fetch_metadata_records[0].fetch_status == "success"
    assert result.fetch_metadata_records[0].record_count == 2
    assert result.fetch_metadata_records[1].fetch_status == "failed"
    assert result.fetch_metadata_records[1].diagnostics == "timeout"
    assert len(result.raw_records) == 2
    assert result.raw_records[0].raw_record_id == "RAW-SRC-A-1"
    assert result.raw_records[0].storage_mode == "payload"
    assert result.raw_records[0].raw_payload == {"signal_key": "article_count", "value": 3.0, "expected_source_count": 1, "freshness_hours": 6}



def test_daily_run_orchestrator_builds_lineage_records_for_features_and_snapshot() -> None:
    adapters = [
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
        )
    ]

    orchestrator = DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalize,
        feature_services=[DomainAFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    result = orchestrator.run(run_id="RUN-103")

    assert result.lineage_records
    assert all(isinstance(record, LineageRecord) for record in result.lineage_records)
    assert result.lineage_records[0].source_id == "SRC-A"
    assert result.lineage_records[0].snapshot_id == "SNAP-RUN-103-v1"
    assert result.lineage_records[0].report_id == "REP-DAILY-SNAP-RUN-103-v1"
    assert "REP-COUNTRY-UKR" in result.lineage_records[0].report_ids
    assert "REP-COVERAGE-RUN-103" in result.lineage_records[0].report_ids
    assert "REP-DOMAIN-UKR-A" in result.lineage_records[0].report_ids



def test_daily_run_orchestrator_emits_failure_artifact_when_all_sources_fail() -> None:
    adapters = [
        FakeAdapter(source_id="SRC-A", domain="A", _result=FetchResult(records=[], diagnostics="timeout", is_success=False)),
        FakeAdapter(source_id="SRC-B", domain="B", _result=FetchResult(records=[], diagnostics="auth", is_success=False)),
    ]

    orchestrator = DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalize,
        feature_services=[DomainAFeatureService(), DomainBFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    result = orchestrator.run(run_id="RUN-104")

    assert result.run_state.status == "failed"
    assert result.failure_artifact is not None
    assert result.failure_artifact.reason == "all_sources_failed"
    assert result.failure_artifact.failed_sources == ["SRC-A", "SRC-B"]
    assert result.snapshot is None
    assert result.daily_report.report_id == "REP-FAIL-RUN-104"
    assert result.daily_report.json_payload["status"] == "failed"



def test_daily_run_orchestrator_emits_failure_artifact_when_fetch_succeeds_but_no_data_is_normalized() -> None:
    adapters = [
        FakeAdapter(source_id="SRC-A", domain="A", _result=FetchResult(records=[], diagnostics="empty-source", is_success=True))
    ]

    orchestrator = DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalize,
        feature_services=[DomainAFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    result = orchestrator.run(run_id="RUN-105")

    assert result.run_state.status == "failed"
    assert result.failure_artifact is not None
    assert result.failure_artifact.reason == "no_data_after_fetch"
    assert result.failure_artifact.failed_sources == []
    assert result.snapshot is None
    assert result.country_reports == {}
    assert result.daily_report.json_payload["failure_reason"] == "no_data_after_fetch"



def test_daily_run_orchestrator_blocks_run_when_active_source_governance_metadata_is_missing() -> None:
    adapters = [
        FakeAdapter(
            source_id="SRC-A",
            domain="A",
            _result=FetchResult(
                records=[{"signal_key": "article_count", "value": 3.0, "expected_source_count": 1, "freshness_hours": 6}],
                diagnostics="should-not-fetch",
                is_success=True,
            ),
        )
    ]

    orchestrator = DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalize,
        feature_services=[DomainAFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
        source_records={"SRC-A": {"source_id": "SRC-A", "status": "active", "access": "api"}},
    )

    result = orchestrator.run(run_id="RUN-106")

    assert result.run_state.status == "failed"
    assert result.failure_artifact is not None
    assert result.failure_artifact.reason == "source_governance_invalid"
    assert result.failure_artifact.failed_sources == ["SRC-A"]
    assert result.fetch_metadata_records == []
    assert result.daily_report.json_payload["failure_reason"] == "source_governance_invalid"



def test_country_report_and_lineage_only_reference_event_reports_when_event_source_records_exist() -> None:
    orchestrator = DailyRunOrchestrator(
        adapters=[],
        normalizer=_normalize,
        feature_services=[],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    features = [
        FeatureValue(
            feature_id="B_event_count",
            country_id="UKR",
            domain="B",
            value=5.0,
            coverage=1.0,
            provenance_source_ids=["SRC-B"],
            confidence_inputs={"source_count": 1},
        )
    ]
    normalized_records = [
        NormalizedRecord(
            normalized_id="NORM-SRC-B-1",
            country_id="UKR",
            timestamp="2026-05-11T18:00:00Z",
            domain="B",
            signal_key="incident_index",
            value=5.0,
            provenance_source_id="SRC-B",
            quality_context={"expected_source_count": 1, "freshness_hours": 6},
        )
    ]

    run_state = orchestrator.run(run_id="RUN-107").run_state
    country_reports = orchestrator._build_country_reports(
        run_state=run_state,
        country_id="UKR",
        features=features,
        normalized_records=normalized_records,
        domain_statuses={"B": _domain_status_analyzer("B", features)},
        multi_domain_status=derive_multi_domain_status([_domain_status_analyzer("B", features)]),
    )

    snapshot = type("S", (), {"run_id": "RUN-107", "snapshot_id": "SNAP-RUN-107-v1"})()
    lineage_records = orchestrator._build_lineage_records(
        raw_records=[
            RawRecord(
                raw_record_id="RAW-SRC-B-1",
                source_id="SRC-B",
                fetched_at="RUN-107",
                storage_mode="payload",
                raw_payload={"signal_key": "incident_index", "value": 5.0},
            )
        ],
        normalized_records=normalized_records,
        features=features,
        domain_statuses={"B": _domain_status_analyzer("B", features)},
        snapshot=snapshot,
        report=type("R", (), {"report_id": "REP-DAILY-SNAP-RUN-107-v1"})(),
        country_reports=country_reports,
    )

    assert country_reports["UKR"].json_payload["linked_events"] == []
    assert all("REP-EVENT-EVT-UKR-RUN-107" not in record.report_ids for record in lineage_records)



def test_lineage_only_adds_event_report_to_event_derived_domain_b_features() -> None:
    adapters = [
        FakeAdapter(
            source_id="SRC-B",
            domain="B",
            _result=FetchResult(
                records=[
                    {"signal_key": "conflict_event_count", "value": 4.0, "expected_source_count": 1, "freshness_hours": 12},
                    {"signal_key": "disaster_alert_level", "value": 2.0, "expected_source_count": 1, "freshness_hours": 12},
                ]
            ),
        )
    ]

    orchestrator = DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalize,
        feature_services=[DomainBFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    result = orchestrator.run(run_id="RUN-108")

    lineage_by_feature = {record.feature_id: record for record in result.lineage_records}
    assert "REP-EVENT-EVT-UKR-RUN-108" in lineage_by_feature["B_event_count"].report_ids
    assert "REP-EVENT-EVT-UKR-RUN-108" not in lineage_by_feature["B_disaster_alert_level"].report_ids



def test_daily_run_orchestrator_builds_country_reports_for_multiple_countries() -> None:
    adapters = [
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
    ]

    orchestrator = DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalize,
        feature_services=[DomainAFeatureService(), DomainBFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A", "B"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    result = orchestrator.run(run_id="RUN-110")

    assert result.snapshot.analytical_outputs["country_status"] == {"POL": "S3", "UKR": "S3"}
    assert sorted(result.country_reports) == ["POL", "UKR"]
    assert result.country_domain_statuses["POL"]["A"].status == "D3"
    assert result.country_domain_statuses["POL"]["B"].status == "D2"
    assert result.country_domain_statuses["UKR"]["A"].status == "D3"
    assert result.country_domain_statuses["UKR"]["B"].status == "D2"
    assert result.country_multi_domain_statuses["POL"].status == "S3"
    assert result.country_multi_domain_statuses["UKR"].status == "S3"
    assert result.country_reports["POL"].json_payload["multi_domain_status"] == "S3"
    assert result.country_reports["UKR"].json_payload["multi_domain_status"] == "S3"



def test_daily_run_orchestrator_builds_country_specific_lineage_for_multiple_countries() -> None:
    adapters = [
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
        )
    ]

    orchestrator = DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalize,
        feature_services=[DomainAFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="MVP-COUNTRIES-v1",
        active_domains=["A"],
        rule_versions={"domain_status": "rules-2026-05", "multi_domain_status": "rules-2026-05"},
        algorithm_version="alg-0.1",
        data_version="data-0.1",
    )

    result = orchestrator.run(run_id="RUN-111")

    lineage_by_country = {
        feature.country_id: record
        for feature in result.features
        for record in result.lineage_records
        if record.feature_id == feature.feature_id and record.domain_status_id == f"DST-{feature.country_id}-{feature.domain}-RUN-111"
    }

    assert lineage_by_country["UKR"].raw_record_id == "RAW-SRC-A-1"
    assert lineage_by_country["POL"].raw_record_id == "RAW-SRC-A-3"
    assert lineage_by_country["UKR"].normalized_id == "NORM-SRC-A-1"
    assert lineage_by_country["POL"].normalized_id == "NORM-SRC-A-3"


def test_daily_run_orchestrator_populates_analytical_module_results() -> None:
    """Phase 4-6 analytical modules (rule_engine, cross_domain_fusion, probabilistic,
    uncertainty_propagation) are invoked during run() and results are present in
    DailyRunResult."""
    adapter = FakeAdapter(
        source_id="SRC-A",
        domain="A",
        _result=FetchResult(
            records=[{"signal_key": "conflict_intensity", "value": 0.8, "country_id": "UKR"}],
            is_success=True,
            diagnostics="",
        ),
    )
    orchestrator = DailyRunOrchestrator(
        adapters=[adapter],
        normalizer=_normalize,
        feature_services=[DomainAFeatureService()],
        domain_status_analyzer=_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id="TEST-SET",
        active_domains=["A"],
        rule_versions={"domain_status": "v1", "multi_domain_status": "v1"},
        algorithm_version="v1",
        data_version="v1",
    )

    result = orchestrator.run(run_id="RUN-ANALYTICS-001")

    assert result.run_state.status in {"success", "partial_success"}

    # cross-domain fusion: at least one entry per country with domain data
    assert isinstance(result.fusion_results, dict)
    # UKR has domain A, so fusion should run
    assert "UKR" in result.fusion_results

    # bayesian estimates: per country per domain
    assert isinstance(result.bayesian_estimates, dict)
    assert "UKR" in result.bayesian_estimates
    assert "A" in result.bayesian_estimates["UKR"]
    est = result.bayesian_estimates["UKR"]["A"]
    assert hasattr(est, "map_status")
    assert hasattr(est, "confidence")
    assert hasattr(est, "posterior")

    # uncertainty budgets: per country
    assert isinstance(result.uncertainty_budgets, dict)
    assert "UKR" in result.uncertainty_budgets
    budget = result.uncertainty_budgets["UKR"]
    assert hasattr(budget, "total_uncertainty")
    assert hasattr(budget, "dominant_stage")

    # rule evaluation results: list (may be empty if no rules matched or no YAML)
    assert isinstance(result.rule_evaluation_results, list)

    # dependency graph: populated since features have provenance_source_ids with 2+ sources
    # (or None if all features have only 1 source — graceful)
    assert hasattr(result, "dependency_graph_result")

    # provenance chain: built from lineage records
    assert hasattr(result, "provenance_chain_result")
    if result.provenance_chain_result is not None:
        chain = result.provenance_chain_result
        assert hasattr(chain, "root_sources")
        assert hasattr(chain, "depth")
        assert chain.depth >= 0

    # info epidemiology
    assert isinstance(result.spread_paths_result, list)
    assert isinstance(result.amplification_result, list)
