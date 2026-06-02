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
        "SRC-UCDP-GED",
        "SRC-GDACS",
        "SRC-GDACS-C",
        "SRC-UNHCR-POP",
        "SRC-GDELT-DOC-E",
        "SRC-CISA-KEV",
    ]
    assert orchestrator.active_domains == ["A", "B", "C", "D", "E"]
    assert orchestrator.country_set_id == "MVP-COUNTRIES-LIVE-UKR-v1"


def test_build_governed_live_orchestrator_skips_world_bank_for_twn_only_runtime_scope() -> None:
    orchestrator = build_governed_live_orchestrator(repo_root=REPO_ROOT, country_id="TWN")

    assert [adapter.source_id for adapter in orchestrator.adapters] == [
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "SRC-GDACS",
        "SRC-GDACS-C",
        "SRC-UNHCR-POP",
        "SRC-GDELT-DOC-E",
        "SRC-CISA-KEV",
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
    ucdp = orchestrator.adapters[3]
    gdacs = orchestrator.adapters[4]

    assert world_bank.country_ids == ("UKR", "POL")
    assert gdelt_doc.country_queries == {"UKR": "Ukraine", "POL": "Poland"}
    assert gdelt_doc.max_records == 10
    assert gdelt_doc.inter_request_delay_seconds == 1.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 40.0
    assert gdelt_events.country_codes == {"UKR": "UP", "POL": "PL"}
    assert gdelt_events.recent_export_count == 8
    assert ucdp.country_ids == {"UKR", "POL"}
    assert set(gdacs.country_ids) == {"UKR", "POL"}



def test_build_governed_live_orchestrator_supports_representative_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="representative",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    ucdp = orchestrator.adapters[3]
    gdacs = orchestrator.adapters[4]

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
    assert ucdp.country_ids == {"UKR", "POL", "ISR"}
    assert set(gdacs.country_ids) == {"UKR", "POL", "ISR", "TWN"}



def test_build_governed_live_orchestrator_supports_core_focus_initial_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="core-focus-initial",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    ucdp = orchestrator.adapters[3]
    gdacs = orchestrator.adapters[4]

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
    assert set(gdacs.country_ids) == {"UKR", "RUS", "CHN", "TWN", "ISR", "POL"}



def test_build_governed_live_orchestrator_supports_core_focus_expanded_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="core-focus-expanded",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    ucdp = orchestrator.adapters[3]
    gdacs = orchestrator.adapters[4]

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
    assert set(gdacs.country_ids) == {"UKR", "RUS", "CHN", "TWN", "ISR", "IND", "POL"}



def test_build_governed_live_orchestrator_supports_core_focus_broader_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="core-focus-broader",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    ucdp = orchestrator.adapters[3]
    gdacs = orchestrator.adapters[4]

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
    assert set(gdacs.country_ids) == {"UKR", "RUS", "CHN", "TWN", "IRN", "ISR", "TUR", "IND", "POL"}



def test_build_governed_live_orchestrator_supports_core_focus_complete_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="core-focus-complete",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    ucdp = orchestrator.adapters[3]
    gdacs = orchestrator.adapters[4]

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
        "PAK": ["A", "D"],
        "GEO": ["A", "D"],
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
    assert gdelt_doc.inter_request_delay_seconds == 3.0
    assert gdelt_doc.max_retry_delay_seconds == 180.0
    assert gdelt_doc.request_timeout_seconds == 90.0
    assert gdelt_doc.max_full_fetch_retries == 2
    assert gdelt_doc.full_fetch_retry_cooldown_seconds == 120.0
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
    assert set(gdacs.country_ids) == {"UKR", "RUS", "CHN", "TWN", "IRN", "ISR", "TUR", "IND", "PAK", "GEO", "POL"}



def test_build_governed_live_orchestrator_supports_extended_focus_initial_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="extended-focus-initial",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    ucdp = orchestrator.adapters[3]
    gdacs = orchestrator.adapters[4]

    assert world_bank.country_ids == (
        "USA",
        "DEU",
        "EST",
        "FIN",
    )
    assert orchestrator.country_expected_domains == {
        "USA": ["A", "B", "D"],
        "DEU": ["A", "B", "D"],
        "EST": ["A", "D"],
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
    assert set(gdacs.country_ids) == {
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
    ucdp = orchestrator.adapters[3]
    gdacs = orchestrator.adapters[4]

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
        "EST": ["A", "D"],
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
    assert set(gdacs.country_ids) == {
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

    assert world_bank.country_ids == ("SAU", "QAT", "EGY")
    assert orchestrator.country_expected_domains == {
        "SAU": ["A", "D"],
        "QAT": ["A", "D"],
        "EGY": ["A", "D"],
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
    assert set(gdacs.country_ids) == {"SAU", "QAT", "EGY"}



def test_build_governed_live_orchestrator_supports_extended_focus_crisis_initial_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="extended-focus-crisis-initial",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == ("NGA", "SDN", "MMR")
    assert orchestrator.country_expected_domains == {
        "NGA": ["A", "B", "D"],
        "SDN": ["A", "D"],
        "MMR": ["A", "D"],
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
    assert set(gdacs.country_ids) == {"NGA", "SDN", "MMR"}



def test_build_governed_live_orchestrator_supports_control_reference_initial_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="control-reference-initial",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == ("CHE", "NLD", "SWE")
    assert orchestrator.country_expected_domains == {
        "CHE": ["A", "B", "D"],
        "NLD": ["A", "D"],
        "SWE": ["A", "D"],
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
    assert set(gdacs.country_ids) == {"CHE", "NLD", "SWE"}



def test_build_governed_live_orchestrator_supports_control_reference_broader_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="control-reference-broader",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == ("NOR", "CAN", "AUS")
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
    assert set(gdacs.country_ids) == {"NOR", "CAN", "AUS"}



def test_build_governed_live_orchestrator_supports_control_reference_third_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="control-reference-third",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == ("NZL", "PRT", "IRL")
    assert orchestrator.country_expected_domains == {
        "NZL": ["A", "D"],
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
    assert set(gdacs.country_ids) == {"NZL", "PRT", "IRL"}



def test_build_governed_live_orchestrator_supports_control_reference_complete_pilot_set() -> None:
    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="control-reference-complete",
    )

    world_bank = orchestrator.adapters[0]
    gdelt_doc = orchestrator.adapters[1]
    gdelt_events = orchestrator.adapters[2]
    gdacs = orchestrator.adapters[3]

    assert world_bank.country_ids == ("NOR", "CHE", "SWE", "NLD", "IRL", "PRT", "NZL", "CAN", "AUS")
    assert orchestrator.country_expected_domains == {
        "NOR": ["A", "D"],
        "CHE": ["A", "B", "D"],
        "SWE": ["A", "D"],
        "NLD": ["A", "D"],
        "IRL": ["A", "B", "D"],
        "PRT": ["A", "D"],
        "NZL": ["A", "D"],
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
    assert set(gdacs.country_ids) == {"NOR", "CHE", "SWE", "NLD", "IRL", "PRT", "NZL", "CAN", "AUS"}



def test_build_governed_live_orchestrator_skips_reliefweb_without_appname(monkeypatch) -> None:
    monkeypatch.delenv("RELIEFWEB_APPNAME", raising=False)

    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="representative",
    )

    assert all(getattr(adapter, "source_id", None) != "SRC-RELIEFWEB" for adapter in orchestrator.adapters)



def test_build_governed_live_orchestrator_includes_reliefweb_when_appname_configured(monkeypatch) -> None:
    monkeypatch.setenv("RELIEFWEB_APPNAME", "siasa-approved")

    orchestrator = build_governed_live_orchestrator(
        repo_root=REPO_ROOT,
        pilot_set="representative",
    )

    reliefweb = next(
        adapter for adapter in orchestrator.adapters if getattr(adapter, "source_id", None) == "SRC-RELIEFWEB"
    )

    assert reliefweb.domain == "C"
    assert reliefweb.country_ids == {"UKR", "POL", "ISR", "TWN"}



def test_run_governed_live_pipeline_passes_control_reference_pilot_set_without_explicit_country_ids() -> None:
    factory = SequenceOrchestratorFactory(
        [
            FakePipelineResult(
                run_state=FakePipelineRunState(
                    run_id="RUN-CTRL-REF-001",
                    status="success",
                    failed_sources=[],
                )
            )
        ]
    )

    result = run_governed_live_pipeline(
        repo_root=REPO_ROOT,
        run_id="RUN-CTRL-REF-001",
        pilot_set="control-reference-initial",
        orchestrator_factory=factory,
        pipeline_retry_sleep=lambda _: None,
    )

    assert result.run_state.status == "success"
    assert factory.calls == [
        {
            "repo_root": REPO_ROOT,
            "country_id": "CHE",
            "country_ids": None,
            "pilot_set": "control-reference-initial",
            "output_dir": None,
        }
    ]



def test_live_runtime_cli_help_lists_control_reference_pilot_sets() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "siasa.runs.live_runtime", "--help"],
        cwd=REPO_ROOT,
        env=_SUBPROCESS_ENV,
        capture_output=True,
        text=True,
        check=True,
    )

    stdout = completed.stdout
    assert "control-reference-initial" in stdout
    assert "control-reference-broader" in stdout
    assert "control-reference-third" in stdout
    assert "control-reference-complete" in stdout
