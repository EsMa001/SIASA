from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from siasa.adapters.base import FetchResult, SourceAdapter
from siasa.runs.live_runtime import build_governed_live_orchestrator


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class FakeAdapter(SourceAdapter):
    source_id: str
    domain: str
    _result: FetchResult

    def fetch(self) -> FetchResult:
        return self._result



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
    assert gdelt_events.country_codes == {"UKR": "UP", "POL": "PL"}
    assert gdacs.country_ids == {"UKR", "POL"}



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
            "/opt/hermes/.venv/bin/python",
            "-m",
            "siasa.runs.live_runtime",
            "--help",
        ],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": "src"},
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
            "/opt/hermes/.venv/bin/python",
            "-m",
            "siasa.runs.live_runtime",
            "--country-id",
            "UKR",
            "--country-id",
            "POL",
            "--help",
        ],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": "src"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Governed live pilot country ISO3" in result.stdout



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

    assert [entry["source_id"] for entry in source_coverage["sources"]] == [
        "WB-INDICATORS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "SRC-GDACS",
    ]
    assert all(entry["source_id"] not in {"SRC-A", "SRC-B"} for entry in source_coverage["sources"])
    assert [country["country_id"] for country in world_map["countries"]] == ["POL", "UKR"]
    assert system_status["coverage"]["countries_total"] == 2
