from __future__ import annotations

from dataclasses import dataclass

from siasa.adapters.base import FetchResult, SourceAdapter
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
