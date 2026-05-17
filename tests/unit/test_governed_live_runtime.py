from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from siasa.adapters.base import FetchResult, SourceAdapter
from siasa.runs.live_runtime import build_governed_live_orchestrator, run_governed_live_pipeline


REPO_ROOT = Path(__file__).resolve().parents[2]
_SUBPROCESS_ENV = {**os.environ, "PYTHONPATH": "src"}


@dataclass
class FakeAdapter(SourceAdapter):
    source_id: str
    domain: str
    _result: FetchResult

    def fetch(self) -> FetchResult:
        return self._result


@dataclass
class FakePipelineRunState:
    run_id: str
    status: str
    failed_sources: list[str]


@dataclass
class FakePipelineResult:
    run_state: FakePipelineRunState
    artifact_bundle: object | None = None


@dataclass
class FakeArtifactBundle:
    output_dir: Path


class SequenceOrchestratorFactory:
    def __init__(self, results: list[FakePipelineResult]) -> None:
        self.results = list(results)
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        result = self.results.pop(0)

        class _FakeOrchestrator:
            def run(self, run_id: str):
                return result

        return _FakeOrchestrator()


class ValidatingSequenceOrchestratorFactory(SequenceOrchestratorFactory):
    def __call__(self, **kwargs):
        if kwargs.get("pilot_set") == "representative" and kwargs.get("country_ids") is not None:
            raise AssertionError("pilot_set=representative must not be combined with explicit country_ids")
        return super().__call__(**kwargs)



def test_build_governed_live_orchestrator_uses_real_source_adapters_for_supported_country() -> None:
    orchestrator = build_governed_live_orchestrator(repo_root=REPO_ROOT, country_id="UKR")

    assert [adapter.source_id for adapter in orchestrator.adapters] == [
        "WB-INDICATORS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "SRC-GDACS",
    ]
    assert orchestrator.active_domains == ["A", "B", "D"]
    assert orchestrator.country_set_id == "MVP-COUNTRIES-LIVE-UKR-v1"


def test_build_governed_live_orchestrator_skips_world_bank_for_twn_only_runtime_scope() -> None:
    orchestrator = build_governed_live_orchestrator(repo_root=REPO_ROOT, country_id="TWN")

    assert [adapter.source_id for adapter in orchestrator.adapters] == [
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "SRC-GDACS",
    ]
    assert orchestrator.country_expected_domains == {"TWN": ["A", "B"]}



def test_build_governed_live_orchestrator_supports_multi_country_live_pilot() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        country_ids=("UKR", "POL"),
    )

    assert orchestrator.country_set_id == "MVP-COUNTRIES-LIVE-MULTI-v1"
    assert orchestrator.rule_versions["runtime_profile"] == "live-multi-country-v1"
    assert orchestrator.algorithm_version == "live-multi-country-v1"

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == ("UKR", "POL")
    assert gdelt_doc.country_queries == {"UKR": "Ukraine", "POL": "Poland"}
    assert gdelt_doc.max_records == 10
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {"UKR": "UP", "POL": "PL"}
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {"UKR", "POL"}



def test_build_governed_live_orchestrator_supports_representative_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="representative",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == ("UKR", "POL", "ISR")
    assert orchestrator.country_expected_domains == {
        "UKR": ["A", "B", "D"],
        "POL": ["A", "B", "D"],
        "ISR": ["A", "B", "D"],
        "TWN": ["A", "B"],
    }
    assert gdelt_doc.country_queries == {
        "UKR": "Ukraine",
        "POL": "Poland",
        "ISR": "Israel",
        "TWN": "Taiwan",
    }
    assert gdelt_doc.max_records == 5
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "UKR": "UP",
        "POL": "PL",
        "ISR": "IS",
        "TWN": "TW",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {"UKR", "POL", "ISR", "TWN"}



def test_build_governed_live_orchestrator_rejects_combined_pilot_set_and_explicit_countries() -> None:
    try:
        build_governed_live_orchestrator(
            repo_root=REPO_ROOT,
            country_ids=("UKR", "POL"),
            pilot_set="representative",
        )
    except ValueError as exc:
        assert "cannot be combined" in str(exc)
    else:
        raise AssertionError("Expected representative pilot set with explicit countries to raise ValueError")



def test_build_governed_live_orchestrator_rejects_unsupported_country_for_gdelt_events() -> None:
    try:
        build_governed_live_orchestrator(repo_root=REPO_ROOT, country_id="CHE")
    except ValueError as exc:
        assert "Supported live pilot countries" in str(exc)
        assert "CHE" in str(exc)
    else:
        raise AssertionError("Expected unsupported live pilot country to raise ValueError")



def test_governed_live_runtime_module_executes_main_for_help() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--help",
        ],
        cwd=REPO_ROOT,
        env=_SUBPROCESS_ENV,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Run the governed SIASA live-source runtime" in result.stdout
    assert "--country-id" in result.stdout



def test_governed_live_runtime_module_accepts_repeated_country_ids_for_multi_country_run() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--country-id",
            "UKR",
            "--country-id",
            "POL",
            "--help",
        ],
        cwd=REPO_ROOT,
        env=_SUBPROCESS_ENV,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Governed live pilot country ISO3" in result.stdout



def test_governed_live_runtime_module_accepts_representative_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "representative",
            "--help",
        ],
        cwd=REPO_ROOT,
        env=_SUBPROCESS_ENV,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--pilot-set" in result.stdout
    assert "representative" in result.stdout



def test_run_governed_live_pipeline_retries_after_gdelt_doc_only_partial_success_for_multi_country() -> None:
    sleep_calls: list[float] = []
    first = FakePipelineResult(FakePipelineRunState("RUN-1", "partial_success", ["SRC-GDELT-DOC"]))
    second = FakePipelineResult(FakePipelineRunState("RUN-1", "success", []))
    factory = SequenceOrchestratorFactory([first, second])

    result = run_governed_live_pipeline(
        repo_root=REPO_ROOT,
        run_id="RUN-1",
        pilot_set="representative",
        orchestrator_factory=factory,
        pipeline_retry_sleep=sleep_calls.append,
        pipeline_retry_cooldown_seconds=40.0,
        max_pipeline_retries=1,
    )

    assert result.run_state.status == "success"
    assert sleep_calls == [40.0]
    assert len(factory.calls) == 2



def test_run_governed_live_pipeline_retries_after_isolated_pol_domain_b_gap_for_multi_country(tmp_path: Path) -> None:
    def _write_system_status(output_dir: Path, country_gap_rows: list[dict[str, object]]) -> FakeArtifactBundle:
        readmodels_dir = output_dir / "readmodels"
        readmodels_dir.mkdir(parents=True)
        (readmodels_dir / "system_status.json").write_text(
            json.dumps(
                {
                    "run_id": "RUN-1",
                    "run_status": "success",
                    "failed_sources": [],
                    "country_coverage_visibility": {"country_gap_rows": country_gap_rows},
                }
            )
        )
        return FakeArtifactBundle(output_dir=output_dir)

    sleep_calls: list[float] = []
    first = FakePipelineResult(
        FakePipelineRunState("RUN-1", "success", []),
        artifact_bundle=_write_system_status(
            tmp_path / "first",
            [
                {
                    "country_id": "POL",
                    "missing_domains": ["B"],
                    "gap_details": [
                        {
                            "domain": "B",
                            "reason": "no_usable_input_data",
                            "source_reason_details": [
                                {"source_id": "SRC-GDACS", "reason": "zero_records_returned"},
                                {"source_id": "SRC-GDELT-EVENTS", "reason": "records_only_for_other_countries_in_scope"},
                            ],
                        }
                    ],
                }
            ],
        ),
    )
    second = FakePipelineResult(
        FakePipelineRunState("RUN-1", "success", []),
        artifact_bundle=_write_system_status(tmp_path / "second", []),
    )
    factory = SequenceOrchestratorFactory([first, second])

    result = run_governed_live_pipeline(
        repo_root=REPO_ROOT,
        run_id="RUN-1",
        pilot_set="representative",
        orchestrator_factory=factory,
        pipeline_retry_sleep=sleep_calls.append,
        pipeline_retry_cooldown_seconds=40.0,
        max_pipeline_retries=1,
    )

    assert result.artifact_bundle is second.artifact_bundle
    assert sleep_calls == [40.0]
    assert len(factory.calls) == 2



def test_run_governed_live_pipeline_does_not_retry_for_non_target_country_gap(tmp_path: Path) -> None:
    readmodels_dir = tmp_path / "single" / "readmodels"
    readmodels_dir.mkdir(parents=True)
    (readmodels_dir / "system_status.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-3",
                "run_status": "success",
                "failed_sources": [],
                "country_coverage_visibility": {
                    "country_gap_rows": [
                        {
                            "country_id": "POL",
                            "missing_domains": ["B"],
                            "gap_details": [
                                {
                                    "domain": "B",
                                    "reason": "no_usable_input_data",
                                    "source_reason_details": [
                                        {"source_id": "SRC-GDACS", "reason": "zero_records_returned"},
                                        {"source_id": "SRC-GDELT-EVENTS", "reason": "source_failed_this_run"},
                                    ],
                                }
                            ],
                        }
                    ]
                },
            }
        )
    )
    result_payload = FakePipelineResult(
        FakePipelineRunState("RUN-3", "success", []),
        artifact_bundle=FakeArtifactBundle(output_dir=tmp_path / "single"),
    )
    factory = SequenceOrchestratorFactory([result_payload])

    result = run_governed_live_pipeline(
        repo_root=REPO_ROOT,
        run_id="RUN-3",
        pilot_set="representative",
        orchestrator_factory=factory,
        max_pipeline_retries=1,
    )

    assert result is result_payload
    assert len(factory.calls) == 1



def test_run_governed_live_pipeline_does_not_retry_pol_gap_for_non_representative_multi_country_run(tmp_path: Path) -> None:
    readmodels_dir = tmp_path / "non-representative" / "readmodels"
    readmodels_dir.mkdir(parents=True)
    (readmodels_dir / "system_status.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-4",
                "run_status": "success",
                "failed_sources": [],
                "country_coverage_visibility": {
                    "country_gap_rows": [
                        {
                            "country_id": "POL",
                            "missing_domains": ["B"],
                            "gap_details": [
                                {
                                    "domain": "B",
                                    "reason": "no_usable_input_data",
                                    "source_reason_details": [
                                        {"source_id": "SRC-GDACS", "reason": "zero_records_returned"},
                                        {"source_id": "SRC-GDELT-EVENTS", "reason": "records_only_for_other_countries_in_scope"},
                                    ],
                                }
                            ],
                        }
                    ]
                },
            }
        )
    )
    result_payload = FakePipelineResult(
        FakePipelineRunState("RUN-4", "success", []),
        artifact_bundle=FakeArtifactBundle(output_dir=tmp_path / "non-representative"),
    )
    factory = SequenceOrchestratorFactory([result_payload])

    result = run_governed_live_pipeline(
        repo_root=REPO_ROOT,
        run_id="RUN-4",
        country_id="UKR",
        country_ids=("UKR", "POL"),
        orchestrator_factory=factory,
        max_pipeline_retries=1,
    )

    assert result is result_payload
    assert len(factory.calls) == 1



def test_run_governed_live_pipeline_does_not_mix_representative_pilot_set_with_explicit_country_ids_for_factory() -> None:
    factory = ValidatingSequenceOrchestratorFactory(
        [FakePipelineResult(FakePipelineRunState("RUN-2", "success", []))]
    )

    result = run_governed_live_pipeline(
        repo_root=REPO_ROOT,
        run_id="RUN-2",
        pilot_set="representative",
        orchestrator_factory=factory,
        max_pipeline_retries=0,
    )

    assert result.run_state.status == "success"
    assert factory.calls[0]["pilot_set"] == "representative"
    assert factory.calls[0]["country_ids"] is None



def test_governed_live_orchestrator_can_write_artifacts_with_real_source_ids(tmp_path: Path) -> None:
    output_dir = tmp_path / "live-runtime"
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        country_ids=("UKR", "POL"),
        output_dir=output_dir,
    )
    orchestrator.adapters = [
        FakeAdapter(
            source_id="WB-INDICATORS",
            domain="D",
            _result=FetchResult(
                records=[
                    {
                        "country_id": "UKR",
                        "timestamp": "2026-05-14",
                        "signal_key": "gdp_growth",
                        "value": 2.1,
                        "freshness_hours": 24,
                        "quality_flag": "world_bank_api",
                    },
                    {
                        "country_id": "UKR",
                        "timestamp": "2026-05-14",
                        "signal_key": "energy_price_stress",
                        "value": 0.4,
                        "freshness_hours": 24,
                        "quality_flag": "world_bank_api",
                    },
                    {
                        "country_id": "POL",
                        "timestamp": "2026-05-14",
                        "signal_key": "gdp_growth",
                        "value": 1.8,
                        "freshness_hours": 24,
                        "quality_flag": "world_bank_api",
                    },
                    {
                        "country_id": "POL",
                        "timestamp": "2026-05-14",
                        "signal_key": "energy_price_stress",
                        "value": 0.2,
                        "freshness_hours": 24,
                        "quality_flag": "world_bank_api",
                    },
                ],
                diagnostics="world_bank_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDELT-DOC",
            domain="A",
            _result=FetchResult(
                records=[
                    {
                        "country_id": "UKR",
                        "timestamp": "2026-05-14T10:00:00Z",
                        "signal_key": "article_count",
                        "value": 10.0,
                        "freshness_hours": 2,
                        "quality_flag": "gdelt_doc_api",
                    },
                    {
                        "country_id": "UKR",
                        "timestamp": "2026-05-14T10:00:00Z",
                        "signal_key": "tone",
                        "value": -1.2,
                        "freshness_hours": 2,
                        "quality_flag": "gdelt_doc_api",
                    },
                    {
                        "country_id": "POL",
                        "timestamp": "2026-05-14T11:00:00Z",
                        "signal_key": "article_count",
                        "value": 8.0,
                        "freshness_hours": 1,
                        "quality_flag": "gdelt_doc_api",
                    },
                    {
                        "country_id": "POL",
                        "timestamp": "2026-05-14T11:00:00Z",
                        "signal_key": "tone",
                        "value": -0.4,
                        "freshness_hours": 1,
                        "quality_flag": "gdelt_doc_api",
                    },
                ],
                diagnostics="gdelt_doc_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDELT-EVENTS",
            domain="B",
            _result=FetchResult(
                records=[
                    {
                        "country_id": "UKR",
                        "timestamp": "2026-05-14T10:00:00Z",
                        "signal_key": "conflict_event_count",
                        "value": 3.0,
                        "freshness_hours": 1,
                        "quality_flag": "gdelt_events_export",
                    },
                    {
                        "country_id": "UKR",
                        "timestamp": "2026-05-14T10:00:00Z",
                        "signal_key": "violent_event_count",
                        "value": 1.0,
                        "freshness_hours": 1,
                        "quality_flag": "gdelt_events_export",
                    },
                    {
                        "country_id": "POL",
                        "timestamp": "2026-05-14T11:00:00Z",
                        "signal_key": "protest_event_count",
                        "value": 2.0,
                        "freshness_hours": 1,
                        "quality_flag": "gdelt_events_export",
                    },
                ],
                diagnostics="gdelt_events_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDACS",
            domain="B",
            _result=FetchResult(
                records=[
                    {
                        "country_id": "UKR",
                        "timestamp": "2026-05-14T09:00:00Z",
                        "signal_key": "disaster_alert_level",
                        "value": 2.0,
                        "freshness_hours": 4,
                        "quality_flag": "gdacs_rss",
                    },
                    {
                        "country_id": "POL",
                        "timestamp": "2026-05-14T09:30:00Z",
                        "signal_key": "disaster_alert_level",
                        "value": 1.0,
                        "freshness_hours": 3,
                        "quality_flag": "gdacs_rss",
                    },
                ],
                diagnostics="gdacs_fetch_ok",
                is_success=True,
            ),
        ),
    ]

    result = orchestrator.run("RUN-LIVE-MULTI-001")

    assert result.run_state.status == "success"

    source_coverage = json.loads((output_dir / "readmodels" / "source_coverage.json").read_text())
    world_map = json.loads((output_dir / "readmodels" / "world_map.json").read_text())
    system_status = json.loads((output_dir / "readmodels" / "system_status.json").read_text())
    validation_backtest = json.loads((output_dir / "readmodels" / "validation_backtest.json").read_text())
    pol_profile = json.loads((output_dir / "readmodels" / "country_profiles" / "POL.json").read_text())

    assert [entry["source_id"] for entry in source_coverage["sources"]] == [
        "WB-INDICATORS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "SRC-GDACS",
    ]
    assert all(entry["source_id"] not in {"SRC-A", "SRC-B"} for entry in source_coverage["sources"])
    assert [country["country_id"] for country in world_map["countries"]] == ["POL", "UKR"]
    assert system_status["coverage"]["countries_total"] == 2
    assert validation_backtest["country_id"] == "UKR"
    assert validation_backtest["comparison_mode"] == "runtime_support_check"
    assert validation_backtest["expected_domains"] == ["A", "B", "D"]
    assert validation_backtest["observed_domains"] == ["A", "B", "D"]
    assert validation_backtest["status_match"] is None
    assert validation_backtest["review_verdict"] == "support_check"
    assert "pilot_runtime_support_case_not_historical_backtest" in validation_backtest["known_limitations"]
    assert pol_profile["country_context"] == {
        "country_name": "Poland",
        "priority": "P2",
        "selection_type": "Extended Focus",
        "region": "Europe / NATO East",
        "rationale": "NATO-Ostflanke, Ukraine-/Russlandbezug",
    }
    assert pol_profile["source_depth"] == {"source_ids": ["SRC-GDACS", "SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"], "source_count": 4}
    assert pol_profile["domain_gap_summary"] == {"expected_domains": ["A", "B", "D"], "observed_domains": ["A", "B", "D"], "missing_domains": []}
    assert pol_profile["trends"]["yearly"]



def test_governed_live_runtime_representative_scope_excludes_twn_domain_d_from_expected_domains(tmp_path: Path) -> None:
    output_dir = tmp_path / "live-runtime-representative-scope"
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="representative",
        output_dir=output_dir,
    )
    orchestrator.adapters = [
        FakeAdapter(
            source_id="WB-INDICATORS",
            domain="D",
            _result=FetchResult(
                records=[
                    {"country_id": "UKR", "timestamp": "2026-05-14", "signal_key": "gdp_growth", "value": 2.1, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                    {"country_id": "UKR", "timestamp": "2026-05-14", "signal_key": "energy_price_stress", "value": 0.4, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                    {"country_id": "POL", "timestamp": "2026-05-14", "signal_key": "gdp_growth", "value": 1.8, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                    {"country_id": "POL", "timestamp": "2026-05-14", "signal_key": "energy_price_stress", "value": 0.2, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                    {"country_id": "ISR", "timestamp": "2026-05-14", "signal_key": "gdp_growth", "value": 0.9, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                    {"country_id": "ISR", "timestamp": "2026-05-14", "signal_key": "energy_price_stress", "value": 0.5, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                ],
                diagnostics="world_bank_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDELT-DOC",
            domain="A",
            _result=FetchResult(
                records=[
                    {"country_id": "UKR", "timestamp": "2026-05-14T10:00:00Z", "signal_key": "article_count", "value": 10.0, "freshness_hours": 2, "quality_flag": "gdelt_doc_api"},
                    {"country_id": "UKR", "timestamp": "2026-05-14T10:00:00Z", "signal_key": "tone", "value": -1.2, "freshness_hours": 2, "quality_flag": "gdelt_doc_api"},
                    {"country_id": "POL", "timestamp": "2026-05-14T11:00:00Z", "signal_key": "article_count", "value": 8.0, "freshness_hours": 1, "quality_flag": "gdelt_doc_api"},
                    {"country_id": "POL", "timestamp": "2026-05-14T11:00:00Z", "signal_key": "tone", "value": -0.4, "freshness_hours": 1, "quality_flag": "gdelt_doc_api"},
                    {"country_id": "ISR", "timestamp": "2026-05-14T12:00:00Z", "signal_key": "article_count", "value": 9.0, "freshness_hours": 1, "quality_flag": "gdelt_doc_api"},
                    {"country_id": "ISR", "timestamp": "2026-05-14T12:00:00Z", "signal_key": "tone", "value": -0.6, "freshness_hours": 1, "quality_flag": "gdelt_doc_api"},
                    {"country_id": "TWN", "timestamp": "2026-05-14T13:00:00Z", "signal_key": "article_count", "value": 7.0, "freshness_hours": 1, "quality_flag": "gdelt_doc_api"},
                    {"country_id": "TWN", "timestamp": "2026-05-14T13:00:00Z", "signal_key": "tone", "value": -0.5, "freshness_hours": 1, "quality_flag": "gdelt_doc_api"},
                ],
                diagnostics="gdelt_doc_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDELT-EVENTS",
            domain="B",
            _result=FetchResult(
                records=[
                    {"country_id": "UKR", "timestamp": "2026-05-14T10:00:00Z", "signal_key": "conflict_event_count", "value": 3.0, "freshness_hours": 1, "quality_flag": "gdelt_events_export"},
                    {"country_id": "UKR", "timestamp": "2026-05-14T10:00:00Z", "signal_key": "violent_event_count", "value": 1.0, "freshness_hours": 1, "quality_flag": "gdelt_events_export"},
                    {"country_id": "POL", "timestamp": "2026-05-14T11:00:00Z", "signal_key": "protest_event_count", "value": 2.0, "freshness_hours": 1, "quality_flag": "gdelt_events_export"},
                    {"country_id": "ISR", "timestamp": "2026-05-14T12:00:00Z", "signal_key": "conflict_event_count", "value": 1.0, "freshness_hours": 1, "quality_flag": "gdelt_events_export"},
                    {"country_id": "TWN", "timestamp": "2026-05-14T13:00:00Z", "signal_key": "protest_event_count", "value": 1.0, "freshness_hours": 1, "quality_flag": "gdelt_events_export"},
                ],
                diagnostics="gdelt_events_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDACS",
            domain="B",
            _result=FetchResult(
                records=[
                    {"country_id": "UKR", "timestamp": "2026-05-14T09:00:00Z", "signal_key": "disaster_alert_level", "value": 2.0, "freshness_hours": 4, "quality_flag": "gdacs_rss"},
                    {"country_id": "POL", "timestamp": "2026-05-14T09:30:00Z", "signal_key": "disaster_alert_level", "value": 1.0, "freshness_hours": 3, "quality_flag": "gdacs_rss"},
                    {"country_id": "ISR", "timestamp": "2026-05-14T10:30:00Z", "signal_key": "disaster_alert_level", "value": 1.0, "freshness_hours": 2, "quality_flag": "gdacs_rss"},
                    {"country_id": "TWN", "timestamp": "2026-05-14T11:30:00Z", "signal_key": "disaster_alert_level", "value": 1.0, "freshness_hours": 2, "quality_flag": "gdacs_rss"},
                ],
                diagnostics="gdacs_fetch_ok",
                is_success=True,
            ),
        ),
    ]

    result = orchestrator.run("RUN-LIVE-REP-SCOPE-001")

    world_map = json.loads((output_dir / "readmodels" / "world_map.json").read_text())
    twn_profile = json.loads((output_dir / "readmodels" / "country_profiles" / "TWN.json").read_text())

    assert result.run_state.status == "success"
    assert twn_profile["configured_domains"] == ["A", "B"]
    assert twn_profile["domain_gap_summary"] == {"expected_domains": ["A", "B"], "observed_domains": ["A", "B"], "missing_domains": []}
    assert next(country for country in world_map["countries"] if country["country_id"] == "TWN")["active_domains"] == ["A", "B"]



def test_governed_live_runtime_validation_artifact_uses_first_configured_country(tmp_path: Path) -> None:
    output_dir = tmp_path / "live-runtime-ordered"
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        country_ids=("UKR", "POL"),
        output_dir=output_dir,
    )
    orchestrator.adapters = [
        FakeAdapter(
            source_id="WB-INDICATORS",
            domain="D",
            _result=FetchResult(
                records=[
                    {"country_id": "POL", "timestamp": "2026-05-14", "signal_key": "gdp_growth", "value": 1.8, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                    {"country_id": "POL", "timestamp": "2026-05-14", "signal_key": "energy_price_stress", "value": 0.2, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                    {"country_id": "UKR", "timestamp": "2026-05-14", "signal_key": "gdp_growth", "value": 2.1, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                    {"country_id": "UKR", "timestamp": "2026-05-14", "signal_key": "energy_price_stress", "value": 0.4, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                ],
                diagnostics="world_bank_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDELT-DOC",
            domain="A",
            _result=FetchResult(
                records=[
                    {"country_id": "POL", "timestamp": "2026-05-14T11:00:00Z", "signal_key": "article_count", "value": 8.0, "freshness_hours": 1, "quality_flag": "gdelt_doc_api"},
                    {"country_id": "POL", "timestamp": "2026-05-14T11:00:00Z", "signal_key": "tone", "value": -0.4, "freshness_hours": 1, "quality_flag": "gdelt_doc_api"},
                    {"country_id": "UKR", "timestamp": "2026-05-14T10:00:00Z", "signal_key": "article_count", "value": 10.0, "freshness_hours": 2, "quality_flag": "gdelt_doc_api"},
                    {"country_id": "UKR", "timestamp": "2026-05-14T10:00:00Z", "signal_key": "tone", "value": -1.2, "freshness_hours": 2, "quality_flag": "gdelt_doc_api"},
                ],
                diagnostics="gdelt_doc_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDELT-EVENTS",
            domain="B",
            _result=FetchResult(
                records=[
                    {"country_id": "POL", "timestamp": "2026-05-14T11:00:00Z", "signal_key": "protest_event_count", "value": 2.0, "freshness_hours": 1, "quality_flag": "gdelt_events_export"},
                    {"country_id": "UKR", "timestamp": "2026-05-14T10:00:00Z", "signal_key": "conflict_event_count", "value": 3.0, "freshness_hours": 1, "quality_flag": "gdelt_events_export"},
                    {"country_id": "UKR", "timestamp": "2026-05-14T10:00:00Z", "signal_key": "violent_event_count", "value": 1.0, "freshness_hours": 1, "quality_flag": "gdelt_events_export"},
                ],
                diagnostics="gdelt_events_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDACS",
            domain="B",
            _result=FetchResult(
                records=[
                    {"country_id": "POL", "timestamp": "2026-05-14T09:30:00Z", "signal_key": "disaster_alert_level", "value": 1.0, "freshness_hours": 3, "quality_flag": "gdacs_rss"},
                    {"country_id": "UKR", "timestamp": "2026-05-14T09:00:00Z", "signal_key": "disaster_alert_level", "value": 2.0, "freshness_hours": 4, "quality_flag": "gdacs_rss"},
                ],
                diagnostics="gdacs_fetch_ok",
                is_success=True,
            ),
        ),
    ]

    result = orchestrator.run("RUN-LIVE-MULTI-ORDER-001")

    assert result.run_state.status == "success"
    validation_backtest = json.loads((output_dir / "readmodels" / "validation_backtest.json").read_text())
    assert validation_backtest["country_id"] == "UKR"



def test_governed_live_runtime_validation_artifact_falls_back_to_next_configured_country_with_data(tmp_path: Path) -> None:
    output_dir = tmp_path / "live-runtime-fallback"
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        country_ids=("UKR", "POL"),
        output_dir=output_dir,
    )
    orchestrator.adapters = [
        FakeAdapter(
            source_id="WB-INDICATORS",
            domain="D",
            _result=FetchResult(
                records=[
                    {"country_id": "POL", "timestamp": "2026-05-14", "signal_key": "gdp_growth", "value": 1.8, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                    {"country_id": "POL", "timestamp": "2026-05-14", "signal_key": "energy_price_stress", "value": 0.2, "freshness_hours": 24, "quality_flag": "world_bank_api"},
                ],
                diagnostics="world_bank_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDELT-DOC",
            domain="A",
            _result=FetchResult(
                records=[
                    {"country_id": "POL", "timestamp": "2026-05-14T11:00:00Z", "signal_key": "article_count", "value": 8.0, "freshness_hours": 1, "quality_flag": "gdelt_doc_api"},
                    {"country_id": "POL", "timestamp": "2026-05-14T11:00:00Z", "signal_key": "tone", "value": -0.4, "freshness_hours": 1, "quality_flag": "gdelt_doc_api"},
                ],
                diagnostics="gdelt_doc_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDELT-EVENTS",
            domain="B",
            _result=FetchResult(
                records=[
                    {"country_id": "POL", "timestamp": "2026-05-14T11:00:00Z", "signal_key": "protest_event_count", "value": 2.0, "freshness_hours": 1, "quality_flag": "gdelt_events_export"},
                ],
                diagnostics="gdelt_events_fetch_ok",
                is_success=True,
            ),
        ),
        FakeAdapter(
            source_id="SRC-GDACS",
            domain="B",
            _result=FetchResult(
                records=[
                    {"country_id": "POL", "timestamp": "2026-05-14T09:30:00Z", "signal_key": "disaster_alert_level", "value": 1.0, "freshness_hours": 3, "quality_flag": "gdacs_rss"},
                ],
                diagnostics="gdacs_fetch_ok",
                is_success=True,
            ),
        ),
    ]

    result = orchestrator.run("RUN-LIVE-MULTI-FALLBACK-001")

    assert result.run_state.status == "success"
    validation_backtest = json.loads((output_dir / "readmodels" / "validation_backtest.json").read_text())
    assert validation_backtest["country_id"] == "POL"
    assert validation_backtest["review_verdict"] == "support_check"
