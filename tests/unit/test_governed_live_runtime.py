from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from siasa.adapters.base import FetchResult, SourceAdapter
from siasa.runs import live_runtime
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



def test_build_governed_live_orchestrator_supports_core_focus_initial_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="core-focus-initial",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == ("UKR", "RUS", "CHN", "ISR", "POL")
    assert orchestrator.country_expected_domains == {
        "UKR": ["A", "B", "D"],
        "RUS": ["A", "B", "D"],
        "CHN": ["A", "B", "D"],
        "TWN": ["A", "B"],
        "ISR": ["A", "B", "D"],
        "POL": ["A", "B", "D"],
    }
    assert gdelt_doc.country_queries == {
        "UKR": "Ukraine",
        "RUS": "Russia",
        "CHN": "China",
        "TWN": "Taiwan",
        "ISR": "Israel",
        "POL": "Poland",
    }
    assert gdelt_doc.max_records == 5
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "UKR": "UP",
        "RUS": "RS",
        "CHN": "CH",
        "TWN": "TW",
        "ISR": "IS",
        "POL": "PL",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {"UKR", "RUS", "CHN", "TWN", "ISR", "POL"}



def test_build_governed_live_orchestrator_supports_core_focus_expanded_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="core-focus-expanded",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == ("UKR", "RUS", "CHN", "ISR", "IND", "POL")
    assert orchestrator.country_expected_domains == {
        "UKR": ["A", "B", "D"],
        "RUS": ["A", "B", "D"],
        "CHN": ["A", "B", "D"],
        "TWN": ["A", "B"],
        "ISR": ["A", "B", "D"],
        "IND": ["A", "B", "D"],
        "POL": ["A", "B", "D"],
    }
    assert gdelt_doc.country_queries == {
        "UKR": "Ukraine",
        "RUS": "Russia",
        "CHN": "China",
        "TWN": "Taiwan",
        "ISR": "Israel",
        "IND": "India",
        "POL": "Poland",
    }
    assert gdelt_doc.max_records == 5
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "UKR": "UP",
        "RUS": "RS",
        "CHN": "CH",
        "TWN": "TW",
        "ISR": "IS",
        "IND": "IN",
        "POL": "PL",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {"UKR", "RUS", "CHN", "TWN", "ISR", "IND", "POL"}



def test_build_governed_live_orchestrator_supports_core_focus_broader_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="core-focus-broader",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == ("UKR", "RUS", "CHN", "IRN", "ISR", "TUR", "IND", "POL")
    assert orchestrator.country_expected_domains == {
        "UKR": ["A", "B", "D"],
        "RUS": ["A", "B", "D"],
        "CHN": ["A", "B", "D"],
        "TWN": ["A", "B"],
        "IRN": ["A", "B", "D"],
        "ISR": ["A", "B", "D"],
        "TUR": ["A", "B", "D"],
        "IND": ["A", "B", "D"],
        "POL": ["A", "B", "D"],
    }
    assert gdelt_doc.country_queries == {
        "UKR": "Ukraine",
        "RUS": "Russia",
        "CHN": "China",
        "TWN": "Taiwan",
        "IRN": "Iran",
        "ISR": "Israel",
        "TUR": "Turkey",
        "IND": "India",
        "POL": "Poland",
    }
    assert gdelt_doc.max_records == 5
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "UKR": "UP",
        "RUS": "RS",
        "CHN": "CH",
        "TWN": "TW",
        "IRN": "IR",
        "ISR": "IS",
        "TUR": "TU",
        "IND": "IN",
        "POL": "PL",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {"UKR", "RUS", "CHN", "TWN", "IRN", "ISR", "TUR", "IND", "POL"}



def test_build_governed_live_orchestrator_supports_core_focus_complete_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="core-focus-complete",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == ("UKR", "RUS", "CHN", "IRN", "ISR", "TUR", "IND", "PAK", "GEO", "POL")
    assert orchestrator.country_expected_domains == {
        "UKR": ["A", "B", "D"],
        "RUS": ["A", "B", "D"],
        "CHN": ["A", "B", "D"],
        "TWN": ["A", "B"],
        "IRN": ["A", "B", "D"],
        "ISR": ["A", "B", "D"],
        "TUR": ["A", "B", "D"],
        "IND": ["A", "B", "D"],
        "PAK": ["A", "B", "D"],
        "GEO": ["A", "B", "D"],
        "POL": ["A", "B", "D"],
    }
    assert gdelt_doc.country_queries == {
        "UKR": "Ukraine",
        "RUS": "Russia",
        "CHN": "China",
        "TWN": "Taiwan",
        "IRN": "Iran",
        "ISR": "Israel",
        "TUR": "Turkey",
        "IND": "India",
        "PAK": "Pakistan",
        "GEO": "Georgia",
        "POL": "Poland",
    }
    assert gdelt_doc.max_records == 5
    assert gdelt_doc.inter_request_delay_seconds == 2.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "UKR": "UP",
        "RUS": "RS",
        "CHN": "CH",
        "TWN": "TW",
        "IRN": "IR",
        "ISR": "IS",
        "TUR": "TU",
        "IND": "IN",
        "PAK": "PK",
        "GEO": "GG",
        "POL": "PL",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {"UKR", "RUS", "CHN", "TWN", "IRN", "ISR", "TUR", "IND", "PAK", "GEO", "POL"}



def test_build_governed_live_orchestrator_supports_extended_focus_initial_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="extended-focus-initial",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == (
        "USA",
        "DEU",
        "EST",
        "FIN",
    )
    assert orchestrator.country_expected_domains == {
        "USA": ["A", "B", "D"],
        "DEU": ["A", "B", "D"],
        "EST": ["A", "B", "D"],
        "FIN": ["A", "D"],
    }
    assert gdelt_doc.country_queries == {
        "USA": "United States",
        "DEU": "Germany",
        "EST": "Estonia",
        "FIN": "Finland",
    }
    assert gdelt_doc.max_records == 5
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "USA": "US",
        "DEU": "GM",
        "EST": "EN",
        "FIN": "FI",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {
        "USA",
        "DEU",
        "EST",
        "FIN",
    }



def test_build_governed_live_orchestrator_supports_extended_focus_broader_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="extended-focus-broader",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == (
        "USA",
        "DEU",
        "EST",
        "FIN",
        "POL",
    )
    assert orchestrator.country_expected_domains == {
        "USA": ["A", "B", "D"],
        "DEU": ["A", "B", "D"],
        "EST": ["A", "B", "D"],
        "FIN": ["A", "D"],
        "POL": ["A", "B", "D"],
    }
    assert gdelt_doc.country_queries == {
        "USA": "United States",
        "DEU": "Germany",
        "EST": "Estonia",
        "FIN": "Finland",
        "POL": "Poland",
    }
    assert gdelt_doc.max_records == 5
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "USA": "US",
        "DEU": "GM",
        "EST": "EN",
        "FIN": "FI",
        "POL": "PL",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {
        "USA",
        "DEU",
        "EST",
        "FIN",
        "POL",
    }



def test_build_governed_live_orchestrator_supports_extended_focus_energy_initial_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="extended-focus-energy-initial",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == (
        "SAU",
        "QAT",
        "EGY",
    )
    assert orchestrator.country_expected_domains == {
        "SAU": ["A", "B", "D"],
        "QAT": ["A", "B", "D"],
        "EGY": ["A", "B", "D"],
    }
    assert gdelt_doc.country_queries == {
        "SAU": "Saudi Arabia",
        "QAT": "Qatar",
        "EGY": "Egypt",
    }
    assert gdelt_doc.max_records == 6
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "SAU": "SA",
        "QAT": "QA",
        "EGY": "EG",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {
        "SAU",
        "QAT",
        "EGY",
    }



def test_build_governed_live_orchestrator_supports_extended_focus_crisis_initial_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="extended-focus-crisis-initial",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == (
        "NGA",
        "SDN",
        "MMR",
    )
    assert orchestrator.country_expected_domains == {
        "NGA": ["A", "B", "D"],
        "SDN": ["A", "B", "D"],
        "MMR": ["A", "B", "D"],
    }
    assert gdelt_doc.country_queries == {
        "NGA": "Nigeria",
        "SDN": "Sudan",
        "MMR": "Myanmar",
    }
    assert gdelt_doc.max_records == 6
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "NGA": "NI",
        "SDN": "SU",
        "MMR": "BM",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {
        "NGA",
        "SDN",
        "MMR",
    }



def test_build_governed_live_orchestrator_supports_control_reference_initial_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="control-reference-initial",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == (
        "CHE",
        "NLD",
        "SWE",
    )
    assert orchestrator.country_expected_domains == {
        "CHE": ["A", "B", "D"],
        "NLD": ["A", "B", "D"],
        "SWE": ["A", "B", "D"],
    }
    assert gdelt_doc.country_queries == {
        "CHE": "Switzerland",
        "NLD": "Netherlands",
        "SWE": "Sweden",
    }
    assert gdelt_doc.max_records == 6
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "CHE": "SZ",
        "NLD": "NL",
        "SWE": "SW",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {
        "CHE",
        "NLD",
        "SWE",
    }



def test_build_governed_live_orchestrator_supports_control_reference_broader_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="control-reference-broader",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == (
        "NOR",
        "CAN",
        "AUS",
    )
    assert orchestrator.country_expected_domains == {
        "NOR": ["A", "D"],
        "CAN": ["A", "B", "D"],
        "AUS": ["A", "B", "D"],
    }
    assert gdelt_doc.country_queries == {
        "NOR": "Norway",
        "CAN": "Canada",
        "AUS": "Australia",
    }
    assert gdelt_doc.max_records == 6
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "NOR": "NO",
        "CAN": "CA",
        "AUS": "AS",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {
        "NOR",
        "CAN",
        "AUS",
    }



def test_build_governed_live_orchestrator_supports_control_reference_third_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="control-reference-third",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == (
        "NZL",
        "PRT",
        "IRL",
    )
    assert orchestrator.country_expected_domains == {
        "NZL": ["A", "B", "D"],
        "PRT": ["A", "D"],
        "IRL": ["A", "B", "D"],
    }
    assert gdelt_doc.country_queries == {
        "NZL": "New Zealand",
        "PRT": "Portugal",
        "IRL": "Ireland",
    }
    assert gdelt_doc.max_records == 6
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "NZL": "NZ",
        "PRT": "PO",
        "IRL": "EI",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {
        "NZL",
        "PRT",
        "IRL",
    }



def test_build_governed_live_orchestrator_supports_control_reference_complete_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="control-reference-complete",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == (
        "NOR",
        "CHE",
        "SWE",
        "NLD",
        "IRL",
        "PRT",
        "NZL",
        "CAN",
        "AUS",
    )
    assert orchestrator.country_expected_domains == {
        "NOR": ["A", "D"],
        "CHE": ["A", "B", "D"],
        "SWE": ["A", "B", "D"],
        "NLD": ["A", "B", "D"],
        "IRL": ["A", "B", "D"],
        "PRT": ["A", "D"],
        "NZL": ["A", "B", "D"],
        "CAN": ["A", "B", "D"],
        "AUS": ["A", "B", "D"],
    }
    assert gdelt_doc.country_queries == {
        "NOR": "Norway",
        "CHE": "Switzerland",
        "SWE": "Sweden",
        "NLD": "Netherlands",
        "IRL": "Ireland",
        "PRT": "Portugal",
        "NZL": "New Zealand",
        "CAN": "Canada",
        "AUS": "Australia",
    }
    assert gdelt_doc.max_records == 5
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {
        "NOR": "NO",
        "CHE": "SZ",
        "SWE": "SW",
        "NLD": "NL",
        "IRL": "EI",
        "PRT": "PO",
        "NZL": "NZ",
        "CAN": "CA",
        "AUS": "AS",
    }
    assert gdelt_events.recent_export_count == 8
    assert gdacs.country_ids == {
        "NOR",
        "CHE",
        "SWE",
        "NLD",
        "IRL",
        "PRT",
        "NZL",
        "CAN",
        "AUS",
    }



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
        build_governed_live_orchestrator(repo_root=REPO_ROOT, country_id="ZZZ")
    except ValueError as exc:
        assert "Supported live pilot countries" in str(exc)
        assert "ZZZ" in str(exc)
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



def test_governed_live_runtime_module_accepts_core_focus_initial_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "core-focus-initial",
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
    assert "core-focus-initial" in result.stdout



def test_governed_live_runtime_module_accepts_core_focus_expanded_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "core-focus-expanded",
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
    assert "core-focus-expanded" in result.stdout



def test_governed_live_runtime_module_accepts_core_focus_broader_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "core-focus-broader",
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
    assert "core-focus-broader" in result.stdout



def test_governed_live_runtime_module_accepts_core_focus_complete_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "core-focus-complete",
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
    assert "core-focus-complete" in result.stdout



def test_governed_live_runtime_module_accepts_extended_focus_initial_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "extended-focus-initial",
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
    assert "extended-focus-initial" in result.stdout



def test_governed_live_runtime_module_accepts_extended_focus_broader_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "extended-focus-broader",
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
    assert "extended-focus-broader" in result.stdout



def test_governed_live_runtime_module_accepts_extended_focus_energy_initial_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "extended-focus-energy-initial",
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
    assert "extended-focus-energy-initial" in result.stdout



def test_governed_live_runtime_module_accepts_extended_focus_crisis_initial_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "extended-focus-crisis-initial",
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
    assert "extended-focus-crisis-initial" in result.stdout



def test_governed_live_runtime_module_accepts_control_reference_initial_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "control-reference-initial",
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
    assert "control-reference-initial" in result.stdout



def test_governed_live_runtime_module_accepts_control_reference_broader_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "control-reference-broader",
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
    assert "control-reference-broader" in result.stdout



def test_governed_live_runtime_module_accepts_control_reference_third_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "control-reference-third",
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
    assert "control-reference-third" in result.stdout



def test_governed_live_runtime_module_accepts_control_reference_complete_pilot_set_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "siasa.runs.live_runtime",
            "--pilot-set",
            "control-reference-complete",
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
    assert "control-reference-complete" in result.stdout



def test_main_preserves_named_pilot_set_when_running_pipeline(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_governed_live_pipeline(**kwargs):
        captured.update(kwargs)
        return FakePipelineResult(FakePipelineRunState("RUN-CLI", "success", []))

    monkeypatch.setattr(live_runtime, "run_governed_live_pipeline", fake_run_governed_live_pipeline)

    exit_code = live_runtime.main([
        "--pilot-set",
        "core-focus-initial",
        "--run-id",
        "RUN-CLI",
        "--output-dir",
        "build/run_artifacts/_cli_core_focus_initial",
    ])

    assert exit_code == 0
    assert captured["pilot_set"] == "core-focus-initial"
    assert captured["country_ids"] is None
    assert captured["country_id"] == "UKR"



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



def test_run_governed_live_pipeline_retries_after_gdelt_events_only_partial_success_for_multi_country() -> None:
    sleep_calls: list[float] = []
    first = FakePipelineResult(FakePipelineRunState("RUN-1", "partial_success", ["SRC-GDELT-EVENTS"]))
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



def test_run_governed_live_pipeline_uses_extra_default_retry_budget_for_core_focus_expanded_gdelt_doc_recovery() -> None:
    sleep_calls: list[float] = []
    first = FakePipelineResult(FakePipelineRunState("RUN-EXP-RETRY", "partial_success", ["SRC-GDELT-DOC"]))
    second = FakePipelineResult(FakePipelineRunState("RUN-EXP-RETRY", "partial_success", ["SRC-GDELT-DOC"]))
    third = FakePipelineResult(FakePipelineRunState("RUN-EXP-RETRY", "success", []))
    factory = SequenceOrchestratorFactory([first, second, third])

    result = run_governed_live_pipeline(
        repo_root=REPO_ROOT,
        run_id="RUN-EXP-RETRY",
        pilot_set="core-focus-expanded",
        orchestrator_factory=factory,
        pipeline_retry_sleep=sleep_calls.append,
        pipeline_retry_cooldown_seconds=40.0,
    )

    assert result.run_state.status == "success"
    assert sleep_calls == [40.0, 40.0]
    assert len(factory.calls) == 3



def test_run_governed_live_pipeline_uses_extra_default_retry_budget_for_extended_focus_broader_gdelt_doc_recovery() -> None:
    sleep_calls: list[float] = []
    first = FakePipelineResult(FakePipelineRunState("RUN-EXT-BROAD-RETRY", "partial_success", ["SRC-GDELT-DOC"]))
    second = FakePipelineResult(FakePipelineRunState("RUN-EXT-BROAD-RETRY", "partial_success", ["SRC-GDELT-DOC"]))
    third = FakePipelineResult(FakePipelineRunState("RUN-EXT-BROAD-RETRY", "success", []))
    factory = SequenceOrchestratorFactory([first, second, third])

    result = run_governed_live_pipeline(
        repo_root=REPO_ROOT,
        run_id="RUN-EXT-BROAD-RETRY",
        pilot_set="extended-focus-broader",
        orchestrator_factory=factory,
        pipeline_retry_sleep=sleep_calls.append,
        pipeline_retry_cooldown_seconds=40.0,
    )

    assert result.run_state.status == "success"
    assert sleep_calls == [40.0, 40.0]
    assert len(factory.calls) == 3



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



def test_run_governed_live_pipeline_retries_after_isolated_pol_domain_b_gap_for_core_focus_expanded_set(tmp_path: Path) -> None:
    readmodels_dir = tmp_path / "first-expanded" / "readmodels"
    readmodels_dir.mkdir(parents=True)
    (readmodels_dir / "system_status.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-EXP-1",
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
                                        {"source_id": "SRC-GDACS", "reason": "records_only_for_other_countries_in_scope"},
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
    sleep_calls: list[float] = []
    first = FakePipelineResult(
        FakePipelineRunState("RUN-EXP-1", "success", []),
        artifact_bundle=FakeArtifactBundle(output_dir=tmp_path / "first-expanded"),
    )
    second_dir = tmp_path / "second-expanded" / "readmodels"
    second_dir.mkdir(parents=True)
    (second_dir / "system_status.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-EXP-1",
                "run_status": "success",
                "failed_sources": [],
                "country_coverage_visibility": {"country_gap_rows": []},
            }
        )
    )
    second = FakePipelineResult(
        FakePipelineRunState("RUN-EXP-1", "success", []),
        artifact_bundle=FakeArtifactBundle(output_dir=tmp_path / "second-expanded"),
    )
    factory = SequenceOrchestratorFactory([first, second])

    result = run_governed_live_pipeline(
        repo_root=REPO_ROOT,
        run_id="RUN-EXP-1",
        pilot_set="core-focus-expanded",
        orchestrator_factory=factory,
        pipeline_retry_sleep=sleep_calls.append,
        pipeline_retry_cooldown_seconds=40.0,
        max_pipeline_retries=1,
    )

    assert result.artifact_bundle is second.artifact_bundle
    assert sleep_calls == [40.0]
    assert len(factory.calls) == 2



def test_run_governed_live_pipeline_retries_after_isolated_fin_domain_b_gap_for_extended_focus_initial_set(tmp_path: Path) -> None:
    readmodels_dir = tmp_path / "first-extended" / "readmodels"
    readmodels_dir.mkdir(parents=True)
    (readmodels_dir / "system_status.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-EXT-1",
                "run_status": "success",
                "failed_sources": [],
                "country_coverage_visibility": {
                    "country_gap_rows": [
                        {
                            "country_id": "FIN",
                            "missing_domains": ["B"],
                            "gap_details": [
                                {
                                    "domain": "B",
                                    "reason": "no_usable_input_data",
                                    "source_reason_details": [
                                        {"source_id": "SRC-GDACS", "reason": "records_only_for_other_countries_in_scope"},
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
    sleep_calls: list[float] = []
    first = FakePipelineResult(
        FakePipelineRunState("RUN-EXT-1", "success", []),
        artifact_bundle=FakeArtifactBundle(output_dir=tmp_path / "first-extended"),
    )
    second_dir = tmp_path / "second-extended" / "readmodels"
    second_dir.mkdir(parents=True)
    (second_dir / "system_status.json").write_text(
        json.dumps(
            {
                "run_id": "RUN-EXT-1",
                "run_status": "success",
                "failed_sources": [],
                "country_coverage_visibility": {"country_gap_rows": []},
            }
        )
    )
    second = FakePipelineResult(
        FakePipelineRunState("RUN-EXT-1", "success", []),
        artifact_bundle=FakeArtifactBundle(output_dir=tmp_path / "second-extended"),
    )
    factory = SequenceOrchestratorFactory([first, second])

    result = run_governed_live_pipeline(
        repo_root=REPO_ROOT,
        run_id="RUN-EXT-1",
        pilot_set="extended-focus-initial",
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
    assert validation_backtest["portfolio_summary"] == {
        "case_count": 2,
        "countries_covered": ["POL", "UKR"],
        "review_verdict_counts": {"support_check": 2},
        "cases_with_gaps": [],
    }
    assert validation_backtest["reference_case_library_summary"] == {
        "case_count": 23,
        "countries_covered": ["CHN", "DEU", "EGY", "EST", "FIN", "GEO", "IND", "IRN", "ISR", "MMR", "NGA", "PAK", "POL", "QAT", "RUS", "SAU", "SDN", "TUR", "TWN", "UKR", "USA"],
        "case_type_counts": {
            "disinformation_spike": 1,
            "hybrid_pressure": 3,
            "military_escalation": 1,
            "strategic_posturing": 18,
        },
        "time_range": {"start": "2022-02-01", "end": "2024-10-31"},
    }
    assert validation_backtest["historical_reference_review_summary"] == {
        "case_count": 23,
        "countries_covered": ["CHN", "DEU", "EGY", "EST", "FIN", "GEO", "IND", "IRN", "ISR", "MMR", "NGA", "PAK", "POL", "QAT", "RUS", "SAU", "SDN", "TUR", "TWN", "UKR", "USA"],
        "review_verdict_counts": {
            "historical_alignment_confirmed": 20,
            "historical_alignment_mismatch": 1,
            "historical_alignment_with_gaps": 2,
        },
        "evidence_tier_counts": {
            "corroborated_multi_source": 19,
            "curated_public_source": 1,
            "provisional": 1,
            "verified_multi_source": 2,
        },
        "average_evidence_score": 0.79,
    }
    assert [review["case_id"] for review in validation_backtest["historical_reference_reviews"]] == [
        "VAL-UKR-2022-001",
        "VAL-RUS-2024-001",
        "VAL-CHN-2024-001",
        "VAL-IND-2024-001",
        "VAL-IRN-2024-001",
        "VAL-TUR-2024-001",
        "VAL-USA-2024-001",
        "VAL-DEU-2024-001",
        "VAL-EST-2024-001",
        "VAL-FIN-2024-001",
        "VAL-SAU-2024-001",
        "VAL-QAT-2024-001",
        "VAL-EGY-2024-001",
        "VAL-NGA-2024-001",
        "VAL-SDN-2024-001",
        "VAL-MMR-2024-001",
        "VAL-POL-2023-001",
        "VAL-POL-2024-002",
        "VAL-ISR-2023-001",
        "VAL-ISR-2024-002",
        "VAL-PAK-2024-001",
        "VAL-GEO-2024-001",
        "VAL-TWN-2024-001",
    ]
    assert validation_backtest["historical_replay_summary"] == {
        "case_count": 23,
        "countries_covered": ["CHN", "DEU", "EGY", "EST", "FIN", "GEO", "IND", "IRN", "ISR", "MMR", "NGA", "PAK", "POL", "QAT", "RUS", "SAU", "SDN", "TUR", "TWN", "UKR", "USA"],
        "review_verdict_counts": {
            "replay_match": 21,
            "replay_match_with_gaps": 1,
            "replay_mismatch": 1,
        },
        "status_match_count": 22,
        "average_domain_match_ratio": 0.96,
        "average_replay_evidence_score": 0.96,
        "average_replay_source_coverage_ratio": 0.96,
        "average_replay_provenance_completeness_ratio": 1.0,
        "replay_input_record_total": 171,
        "archival_data_file_count": 23,
        "replay_evidence_tier_counts": {
            "strong_replay_evidence": 1,
            "verified_replay_evidence": 21,
            "weak_replay_evidence": 1,
        },
        "replay_input_source_coverage_counts": {
            "SRC-GDACS": 22,
            "SRC-GDELT-DOC": 23,
            "SRC-GDELT-EVENTS": 22,
            "WB-INDICATORS": 20,
        },
        "review_basis_counts": {
            "provider_backed_archival_replay": 23,
        },
        "attention_case_count": 2,
        "attention_level_counts": {
            "high": 1,
            "medium": 1,
        },
        "attention_reason_counts": {
            "domain_coverage_gap": 1,
            "status_mismatch_and_domain_gap": 1,
        },
        "attention_owner_counts": {
            "runtime/source coverage": 1,
            "validation governance": 1,
        },
        "attention_country_summary": [
            {
                "country_id": "ISR",
                "attention_case_count": 1,
                "highest_attention_level": "high",
                "case_ids": ["VAL-ISR-2024-002"],
            },
            {
                "country_id": "POL",
                "attention_case_count": 1,
                "highest_attention_level": "medium",
                "case_ids": ["VAL-POL-2024-002"],
            },
        ],
        "attention_cases": [
            {
                "case_id": "VAL-ISR-2024-002",
                "country_id": "ISR",
                "review_verdict": "replay_mismatch",
                "attention_level": "high",
                "attention_reason": "status_mismatch_and_domain_gap",
                "owner_hint": "validation governance",
                "replay_evidence_tier": "weak_replay_evidence",
                "replay_source_coverage_ratio": 0.25,
                "missing_expected_domains": ["B", "D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review reference-case expectation alignment and archival replay provenance before using this case as a strong validation signal.",
            },
            {
                "case_id": "VAL-POL-2024-002",
                "country_id": "POL",
                "review_verdict": "replay_match_with_gaps",
                "attention_level": "medium",
                "attention_reason": "domain_coverage_gap",
                "owner_hint": "runtime/source coverage",
                "replay_evidence_tier": "strong_replay_evidence",
                "replay_source_coverage_ratio": 0.75,
                "missing_expected_domains": ["D"],
                "unexpected_observed_domains": [],
                "suggested_next_action": "Review missing expected domains and source coverage before treating this replay as fully representative.",
            },
        ],
    }
    assert [review["case_id"] for review in validation_backtest["historical_replay_reviews"]] == [
        "VAL-UKR-2022-001",
        "VAL-RUS-2024-001",
        "VAL-CHN-2024-001",
        "VAL-IND-2024-001",
        "VAL-IRN-2024-001",
        "VAL-TUR-2024-001",
        "VAL-USA-2024-001",
        "VAL-DEU-2024-001",
        "VAL-EST-2024-001",
        "VAL-FIN-2024-001",
        "VAL-SAU-2024-001",
        "VAL-QAT-2024-001",
        "VAL-EGY-2024-001",
        "VAL-NGA-2024-001",
        "VAL-SDN-2024-001",
        "VAL-MMR-2024-001",
        "VAL-POL-2023-001",
        "VAL-POL-2024-002",
        "VAL-ISR-2023-001",
        "VAL-ISR-2024-002",
        "VAL-PAK-2024-001",
        "VAL-GEO-2024-001",
        "VAL-TWN-2024-001",
    ]
    assert validation_backtest["historical_replay_reviews"][0]["replay_input_source_ids"] == [
        "SRC-GDACS",
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "WB-INDICATORS",
    ]
    assert validation_backtest["historical_replay_reviews"][0]["archival_data_files"] == [
        "archival_replay_inputs/VAL-UKR-2022-001.json"
    ]
    assert validation_backtest["historical_replay_reviews"][0]["replay_evidence_score"] == 1.0
    assert validation_backtest["historical_replay_reviews"][0]["replay_evidence_tier"] == "verified_replay_evidence"
    assert [case["case_id"] for case in validation_backtest["reference_case_library"]] == [
        "VAL-UKR-2022-001",
        "VAL-RUS-2024-001",
        "VAL-CHN-2024-001",
        "VAL-IND-2024-001",
        "VAL-IRN-2024-001",
        "VAL-TUR-2024-001",
        "VAL-USA-2024-001",
        "VAL-DEU-2024-001",
        "VAL-EST-2024-001",
        "VAL-FIN-2024-001",
        "VAL-SAU-2024-001",
        "VAL-QAT-2024-001",
        "VAL-EGY-2024-001",
        "VAL-NGA-2024-001",
        "VAL-SDN-2024-001",
        "VAL-MMR-2024-001",
        "VAL-POL-2023-001",
        "VAL-POL-2024-002",
        "VAL-ISR-2023-001",
        "VAL-ISR-2024-002",
        "VAL-PAK-2024-001",
        "VAL-GEO-2024-001",
        "VAL-TWN-2024-001",
    ]
    assert [case["country_id"] for case in validation_backtest["validation_cases"]] == ["UKR", "POL"]
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
