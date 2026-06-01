from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import sleep
from typing import Callable

from siasa.adapters import (
    CISAKEVAdapter,
    GDACSAdapter,
    GDELTDocAdapter,
    GDELTEventsAdapter,
    UNHCRPopulationAdapter,
    WorldBankIndicatorsAdapter,
)
from siasa.data.normalization_mappings import NormalizationMappingVersion
from siasa.data.normalization_service import normalize_records
from siasa.features.domain_a import DomainAFeatureService
from siasa.features.domain_b import DomainBFeatureService
from siasa.features.domain_c import DomainCFeatureService
from siasa.features.domain_d import DomainDFeatureService
from siasa.features.domain_e import DomainEFeatureService
from siasa.readmodels.validation_backtest import (
    build_historical_replay_summary,
    build_reference_case_library_summary,
    build_validation_backtest_read_model,
    build_validation_portfolio_summary,
)
from siasa.runs.orchestrator import DailyRunOrchestrator, DailyRunResult
from siasa.scoring.data_sufficiency import evaluate_data_sufficiency
from siasa.scoring.domain_status import derive_domain_status
from siasa.scoring.multi_domain_status import derive_multi_domain_status
from siasa.catalog import load_country_set
from siasa.validation.archival_replay import load_governed_historical_replay_inputs
from siasa.validation.cases import ValidationCase, compare_expected_vs_observed, load_validation_case_library, validation_case_to_dict
from siasa.validation.historical_replay import build_historical_replay_reviews

_SUPPORTED_LIVE_PILOT_COUNTRIES = {
    "UKR": {"gdelt_query": "Ukraine", "gdelt_code": "UP"},
    "POL": {"gdelt_query": "Poland", "gdelt_code": "PL"},
    "ISR": {"gdelt_query": "Israel", "gdelt_code": "IS"},
    "TWN": {"gdelt_query": "Taiwan", "gdelt_code": "TW"},
    "RUS": {"gdelt_query": "Russia", "gdelt_code": "RS"},
    "CHN": {"gdelt_query": "China", "gdelt_code": "CH"},
    "IND": {"gdelt_query": "India", "gdelt_code": "IN"},
    "IRN": {"gdelt_query": "Iran", "gdelt_code": "IR"},
    "TUR": {"gdelt_query": "Turkey", "gdelt_code": "TU"},
    "PAK": {"gdelt_query": "Pakistan", "gdelt_code": "PK"},
    "GEO": {"gdelt_query": "Georgia", "gdelt_code": "GG"},
    "USA": {"gdelt_query": "United States", "gdelt_code": "US"},
    "DEU": {"gdelt_query": "Germany", "gdelt_code": "GM"},
    "EST": {"gdelt_query": "Estonia", "gdelt_code": "EN"},
    "FIN": {"gdelt_query": "Finland", "gdelt_code": "FI"},
    "SAU": {"gdelt_query": "Saudi Arabia", "gdelt_code": "SA"},
    "QAT": {"gdelt_query": "Qatar", "gdelt_code": "QA"},
    "EGY": {"gdelt_query": "Egypt", "gdelt_code": "EG"},
    "NGA": {"gdelt_query": "Nigeria", "gdelt_code": "NI"},
    "SDN": {"gdelt_query": "Sudan", "gdelt_code": "SU"},
    "MMR": {"gdelt_query": "Myanmar", "gdelt_code": "BM"},
    "CHE": {"gdelt_query": "Switzerland", "gdelt_code": "SZ"},
    "NLD": {"gdelt_query": "Netherlands", "gdelt_code": "NL"},
    "SWE": {"gdelt_query": "Sweden", "gdelt_code": "SW"},
    "NOR": {"gdelt_query": "Norway", "gdelt_code": "NO"},
    "CAN": {"gdelt_query": "Canada", "gdelt_code": "CA"},
    "AUS": {"gdelt_query": "Australia", "gdelt_code": "AS"},
    "NZL": {"gdelt_query": "New Zealand", "gdelt_code": "NZ"},
    "PRT": {"gdelt_query": "Portugal", "gdelt_code": "PO"},
    "IRL": {"gdelt_query": "Ireland", "gdelt_code": "EI"},
}

_REPRESENTATIVE_LIVE_PILOT_SET = ("UKR", "POL", "ISR", "TWN")
_CORE_FOCUS_INITIAL_LIVE_PILOT_SET = ("UKR", "RUS", "CHN", "TWN", "ISR", "POL")
_CORE_FOCUS_EXPANDED_LIVE_PILOT_SET = ("UKR", "RUS", "CHN", "TWN", "ISR", "IND", "POL")
_CORE_FOCUS_BROADER_LIVE_PILOT_SET = ("UKR", "RUS", "CHN", "TWN", "IRN", "ISR", "TUR", "IND", "POL")
_CORE_FOCUS_COMPLETE_LIVE_PILOT_SET = ("UKR", "RUS", "CHN", "TWN", "IRN", "ISR", "TUR", "IND", "PAK", "GEO", "POL")
_EXTENDED_FOCUS_INITIAL_LIVE_PILOT_SET = (
    "USA",
    "DEU",
    "EST",
    "FIN",
)
_EXTENDED_FOCUS_BROADER_LIVE_PILOT_SET = (
    "USA",
    "DEU",
    "EST",
    "FIN",
    "POL",
)
_EXTENDED_FOCUS_ENERGY_INITIAL_LIVE_PILOT_SET = (
    "SAU",
    "QAT",
    "EGY",
)
_EXTENDED_FOCUS_CRISIS_INITIAL_LIVE_PILOT_SET = (
    "NGA",
    "SDN",
    "MMR",
)
_CONTROL_REFERENCE_INITIAL_LIVE_PILOT_SET = (
    "CHE",
    "NLD",
    "SWE",
)
_CONTROL_REFERENCE_BROADER_LIVE_PILOT_SET = (
    "NOR",
    "CAN",
    "AUS",
)
_CONTROL_REFERENCE_THIRD_LIVE_PILOT_SET = (
    "NZL",
    "PRT",
    "IRL",
)
_CONTROL_REFERENCE_COMPLETE_LIVE_PILOT_SET = (
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
_EXTENDED_FOCUS_COMPLETE_LIVE_PILOT_SET = (
    "USA",
    "DEU",
    "EST",
    "FIN",
    "POL",
    "SAU",
    "QAT",
    "EGY",
    "NGA",
    "SDN",
    "MMR",
)
_FOCUS_COMPLETE_LIVE_PILOT_SET = (
    "UKR",
    "RUS",
    "CHN",
    "TWN",
    "IRN",
    "ISR",
    "TUR",
    "IND",
    "PAK",
    "GEO",
    "POL",
    "USA",
    "DEU",
    "EST",
    "FIN",
    "SAU",
    "QAT",
    "EGY",
    "NGA",
    "SDN",
    "MMR",
)
_MVP_COMPLETE_LIVE_PILOT_SET = (
    "UKR",
    "RUS",
    "CHN",
    "TWN",
    "IRN",
    "ISR",
    "TUR",
    "IND",
    "PAK",
    "GEO",
    "POL",
    "USA",
    "DEU",
    "EST",
    "FIN",
    "SAU",
    "QAT",
    "EGY",
    "NGA",
    "SDN",
    "MMR",
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
_WORLD_BANK_SUPPORTED_LIVE_COUNTRIES = (
    "UKR",
    "POL",
    "ISR",
    "RUS",
    "CHN",
    "IND",
    "IRN",
    "TUR",
    "PAK",
    "GEO",
    "USA",
    "DEU",
    "EST",
    "FIN",
    "SAU",
    "QAT",
    "EGY",
    "NGA",
    "SDN",
    "MMR",
    "CHE",
    "NLD",
    "SWE",
    "NOR",
    "CAN",
    "AUS",
    "NZL",
    "PRT",
    "IRL",
)
_MULTI_COUNTRY_GDELT_EVENTS_RECENT_EXPORT_COUNT = 8


def _gdelt_events_recent_export_count_for_country_count(country_count: int) -> int:
    if country_count >= 30:
        return 2
    if country_count >= 24:
        return 4
    return _MULTI_COUNTRY_GDELT_EVENTS_RECENT_EXPORT_COUNT
_GOVERNED_LIVE_DOMAINS_BY_COUNTRY = {
    "UKR": ["A", "B", "D"],
    "POL": ["A", "B", "D"],
    "ISR": ["A", "B", "D"],
    "TWN": ["A", "B"],
    "RUS": ["A", "B", "D"],
    "CHN": ["A", "B", "D"],
    "IND": ["A", "B", "D"],
    "IRN": ["A", "B", "D"],
    "TUR": ["A", "B", "D"],
    "PAK": ["A", "D"],
    "GEO": ["A", "D"],
    "USA": ["A", "B", "D"],
    "DEU": ["A", "B", "D"],
    "EST": ["A", "D"],
    "FIN": ["A", "D"],
    "SAU": ["A", "D"],
    "QAT": ["A", "D"],
    "EGY": ["A", "D"],
    "NGA": ["A", "B", "D"],
    "SDN": ["A", "D"],
    "MMR": ["A", "D"],
    "CHE": ["A", "B", "D"],
    "NLD": ["A", "D"],
    "SWE": ["A", "D"],
    "NOR": ["A", "D"],
    "CAN": ["A", "B", "D"],
    "AUS": ["A", "B", "D"],
    "NZL": ["A", "D"],
    "PRT": ["A", "D"],
    "IRL": ["A", "B", "D"],
}
_NAMED_LIVE_PILOT_SETS = {
    "representative": _REPRESENTATIVE_LIVE_PILOT_SET,
    "core-focus-initial": _CORE_FOCUS_INITIAL_LIVE_PILOT_SET,
    "core-focus-expanded": _CORE_FOCUS_EXPANDED_LIVE_PILOT_SET,
    "core-focus-broader": _CORE_FOCUS_BROADER_LIVE_PILOT_SET,
    "core-focus-complete": _CORE_FOCUS_COMPLETE_LIVE_PILOT_SET,
    "extended-focus-initial": _EXTENDED_FOCUS_INITIAL_LIVE_PILOT_SET,
    "extended-focus-broader": _EXTENDED_FOCUS_BROADER_LIVE_PILOT_SET,
    "extended-focus-energy-initial": _EXTENDED_FOCUS_ENERGY_INITIAL_LIVE_PILOT_SET,
    "extended-focus-crisis-initial": _EXTENDED_FOCUS_CRISIS_INITIAL_LIVE_PILOT_SET,
    "control-reference-initial": _CONTROL_REFERENCE_INITIAL_LIVE_PILOT_SET,
    "control-reference-broader": _CONTROL_REFERENCE_BROADER_LIVE_PILOT_SET,
    "control-reference-third": _CONTROL_REFERENCE_THIRD_LIVE_PILOT_SET,
    "control-reference-complete": _CONTROL_REFERENCE_COMPLETE_LIVE_PILOT_SET,
    "extended-focus-complete": _EXTENDED_FOCUS_COMPLETE_LIVE_PILOT_SET,
    "focus-complete": _FOCUS_COMPLETE_LIVE_PILOT_SET,
    "mvp-complete": _MVP_COMPLETE_LIVE_PILOT_SET,
}

_VALIDATION_REFERENCE_CASE_LIBRARY_PATH = (
    Path(__file__).resolve().parents[3] / "vmodel" / "verification" / "validation_reference_cases.yaml"
)


def _load_reference_case_library() -> list[dict[str, object]]:
    return [
        validation_case_to_dict(case)
        for case in load_validation_case_library(_VALIDATION_REFERENCE_CASE_LIBRARY_PATH)
    ]



def _gdelt_doc_max_records_for_country_count(country_count: int) -> int:
    if country_count <= 1:
        return 50
    if country_count >= 24:
        return 3
    return max(5, 20 // country_count)



def _gdelt_doc_inter_request_delay_seconds_for_country_count(country_count: int) -> float:
    if country_count <= 1:
        return 0.0
    if country_count >= 11:
        return 3.0
    return 1.0


def _gdelt_doc_max_full_fetch_retries_for_country_count(country_count: int) -> int:
    if country_count >= 24:
        return 0
    if country_count > 1:
        return 2
    return 0



def _gdelt_doc_max_retry_delay_seconds_for_country_count(country_count: int) -> float:
    if country_count >= 11:
        return 180.0
    return 60.0



def _gdelt_doc_request_timeout_seconds_for_country_count(country_count: int) -> float:
    if country_count >= 11:
        return 90.0
    return 30.0



def _gdelt_doc_full_fetch_retry_cooldown_seconds_for_country_count(country_count: int) -> float:
    if country_count >= 24:
        return 0.0
    if country_count >= 11:
        return 120.0
    if country_count > 1:
        return 40.0
    return 0.0


def _resolve_requested_country_ids(
    country_id: str,
    country_ids: tuple[str, ...] | None = None,
    pilot_set: str | None = None,
) -> tuple[str, ...]:
    if pilot_set is not None:
        if country_ids:
            raise ValueError(f"pilot_set={pilot_set} cannot be combined with explicit country_ids")
        if pilot_set not in _NAMED_LIVE_PILOT_SETS:
            supported_sets = ", ".join(sorted(_NAMED_LIVE_PILOT_SETS))
            raise ValueError(f"Supported pilot_set values are: {supported_sets}")
        return _NAMED_LIVE_PILOT_SETS[pilot_set]
    return _normalize_country_ids(country_id, country_ids)



def _normalize_country_ids(country_id: str, country_ids: tuple[str, ...] | None = None) -> tuple[str, ...]:
    raw_ids = country_ids or (country_id,)
    normalized: list[str] = []
    for raw_country_id in raw_ids:
        normalized_country_id = raw_country_id.strip().upper()
        if not normalized_country_id:
            continue
        if normalized_country_id not in normalized:
            normalized.append(normalized_country_id)
    if not normalized:
        raise ValueError("At least one live pilot country_id is required")
    unsupported = [country for country in normalized if country not in _SUPPORTED_LIVE_PILOT_COUNTRIES]
    if unsupported:
        supported = ", ".join(sorted(_SUPPORTED_LIVE_PILOT_COUNTRIES))
        raise ValueError(
            f"Supported live pilot countries are: {supported}; received {', '.join(unsupported)}"
        )
    return tuple(normalized)



def _country_set_path(repo_root: Path) -> Path:
    return repo_root / "vmodel" / "project" / "mvp_countries.yaml"



def _load_country_name(repo_root: Path, country_id: str) -> str:
    records = load_country_set(_country_set_path(repo_root))
    for record in records:
        if record.iso3 == country_id:
            return record.country_name
    raise ValueError(f"Unknown governed MVP country_id={country_id}")



def _build_normalization_mappings() -> list[NormalizationMappingVersion]:
    return [
        NormalizationMappingVersion(
            mapping_id="MAP-WB-INDICATORS-v1",
            source_id="WB-INDICATORS",
            version="v1",
            is_active=True,
        ),
        NormalizationMappingVersion(
            mapping_id="MAP-SRC-GDELT-DOC-v1",
            source_id="SRC-GDELT-DOC",
            version="v1",
            is_active=True,
        ),
        NormalizationMappingVersion(
            mapping_id="MAP-SRC-GDELT-EVENTS-v1",
            source_id="SRC-GDELT-EVENTS",
            version="v1",
            is_active=True,
        ),
        NormalizationMappingVersion(
            mapping_id="MAP-SRC-GDACS-v1",
            source_id="SRC-GDACS",
            version="v1",
            is_active=True,
        ),
        NormalizationMappingVersion(
            mapping_id="MAP-SRC-GDACS-C-v1",
            source_id="SRC-GDACS-C",
            version="v1",
            is_active=True,
        ),
        NormalizationMappingVersion(
            mapping_id="MAP-SRC-GDELT-DOC-E-v1",
            source_id="SRC-GDELT-DOC-E",
            version="v1",
            is_active=True,
        ),
        NormalizationMappingVersion(
            mapping_id="MAP-SRC-UNHCR-POP-v1",
            source_id="SRC-UNHCR-POP",
            version="v1",
            is_active=True,
        ),
        NormalizationMappingVersion(
            mapping_id="MAP-SRC-CISA-KEV-v1",
            source_id="SRC-CISA-KEV",
            version="v1",
            is_active=True,
        ),
    ]



def _default_domain_status_analyzer(domain: str, features):
    sufficiency = evaluate_data_sufficiency(features)
    anomaly_score = {"A": 0.7, "B": 0.3, "C": 0.2, "D": 0.1, "E": 0.2}.get(domain, 0.1)
    return derive_domain_status(domain, anomaly_score=anomaly_score, sufficiency=sufficiency)



def _build_live_runtime_validation_view_model(
    primary_country_id: str,
    active_domains: list[str],
    run_state,
    normalized_records,
    country_domain_statuses,
    country_multi_domain_statuses,
    snapshot,
    country_expected_domains: dict[str, list[str]] | None = None,
    validation_cases: list[dict[str, object]] | None = None,
    portfolio_summary: dict[str, object] | None = None,
    reference_case_library: list[dict[str, object]] | None = None,
    reference_case_library_summary: dict[str, object] | None = None,
    historical_replay_reviews: list[dict[str, object]] | None = None,
    historical_replay_summary: dict[str, object] | None = None,
) -> dict[str, object] | None:
    country_records = [record for record in normalized_records if record.country_id == primary_country_id]
    observed_domains = sorted(country_domain_statuses.get(primary_country_id, {}).keys())
    if not country_records or not observed_domains or primary_country_id not in country_multi_domain_statuses:
        return None
    timestamps = sorted(str(record.timestamp) for record in country_records)
    reference_sources = sorted({record.provenance_source_id for record in country_records})
    known_limitations = ["pilot_runtime_support_case_not_historical_backtest"]
    if run_state.failed_sources:
        known_limitations.append(f"failed_sources:{','.join(run_state.failed_sources)}")
    expected_domains = list((country_expected_domains or {}).get(primary_country_id, active_domains))
    observed_status = country_multi_domain_statuses[primary_country_id].status
    validation_case = ValidationCase(
        case_id=f"VAL-{primary_country_id}-LIVE-PILOT-SUPPORT",
        country_id=primary_country_id,
        case_name=f"Governed live runtime support case for {primary_country_id}",
        case_type="pilot_runtime_support_case",
        time_start=timestamps[0],
        time_end=timestamps[-1],
        expected_domains=expected_domains,
        expected_status=observed_status,
        expected_signal_pattern=(
            "Governed live pilot should expose the configured active domains "
            "and emit a reviewable validation artifact for the current bundle."
        ),
        reference_sources=reference_sources,
        validation_goal=(
            "Check validation artifact generation and expected-versus-observed "
            "domain visibility for the governed live pilot bundle."
        ),
        known_limitations=known_limitations,
        validation_metrics=["Artifact Presence", "Domain Match", "Status Match"],
    )
    comparison = compare_expected_vs_observed(
        validation_case=validation_case,
        observed_domains=observed_domains,
        observed_status=observed_status,
        expected_status=observed_status,
    )
    comparison["status_match"] = None
    validation_view_model = build_validation_backtest_read_model(
        validation_case=validation_case,
        comparison=comparison,
        reprocessing_comparison={},
        validation_cases=validation_cases,
        portfolio_summary=portfolio_summary,
        reference_case_library=reference_case_library,
        reference_case_library_summary=reference_case_library_summary,
        historical_replay_reviews=historical_replay_reviews,
        historical_replay_summary=historical_replay_summary,
    )
    validation_view_model["comparison_mode"] = "runtime_support_check"
    validation_view_model["snapshot_id"] = snapshot.snapshot_id
    validation_view_model["run_id"] = run_state.run_id
    return validation_view_model



def _validation_candidate_country_ids(
    resolved_country_ids: tuple[str, ...],
    normalized_records,
    country_domain_statuses,
    country_multi_domain_statuses,
) -> list[str]:
    return [
        country_id
        for country_id in resolved_country_ids
        if country_id in country_multi_domain_statuses
        and any(record.country_id == country_id for record in normalized_records)
        and country_domain_statuses.get(country_id)
    ]



def _should_retry_pipeline_after_gdelt_doc_failure(
    result: DailyRunResult,
    requested_country_ids: tuple[str, ...],
) -> bool:
    return (
        len(requested_country_ids) > 1
        and result.run_state.status == "partial_success"
        and result.run_state.failed_sources == ["SRC-GDELT-DOC"]
    )



def _should_retry_pipeline_after_gdelt_events_failure(
    result: DailyRunResult,
    requested_country_ids: tuple[str, ...],
) -> bool:
    return (
        len(requested_country_ids) > 1
        and result.run_state.status == "partial_success"
        and result.run_state.failed_sources == ["SRC-GDELT-EVENTS"]
    )



def _should_retry_pipeline_after_isolated_country_domain_b_gap(
    result: DailyRunResult,
    requested_country_ids: tuple[str, ...],
) -> bool:
    retryable_domain_b_gap_signatures = {
        _REPRESENTATIVE_LIVE_PILOT_SET: (
            "POL",
            {
                ("SRC-GDACS", "zero_records_returned"),
                ("SRC-GDELT-EVENTS", "records_only_for_other_countries_in_scope"),
            },
        ),
        _CORE_FOCUS_EXPANDED_LIVE_PILOT_SET: (
            "POL",
            {
                ("SRC-GDACS", "records_only_for_other_countries_in_scope"),
                ("SRC-GDELT-EVENTS", "records_only_for_other_countries_in_scope"),
            },
        ),
        _EXTENDED_FOCUS_INITIAL_LIVE_PILOT_SET: (
            "FIN",
            {
                ("SRC-GDACS", "records_only_for_other_countries_in_scope"),
                ("SRC-GDELT-EVENTS", "records_only_for_other_countries_in_scope"),
            },
        ),
    }
    target_signature = retryable_domain_b_gap_signatures.get(requested_country_ids)
    if (
        target_signature is None
        or result.run_state.status != "success"
        or result.run_state.failed_sources
    ):
        return False
    target_country_id, expected_reason_pairs = target_signature
    artifact_bundle = result.artifact_bundle
    output_dir = getattr(artifact_bundle, "output_dir", None)
    if output_dir is None:
        return False
    system_status_path = Path(output_dir) / "readmodels" / "system_status.json"
    if not system_status_path.exists():
        return False
    try:
        system_status = json.loads(system_status_path.read_text())
    except (OSError, ValueError, TypeError):
        return False
    coverage_visibility = system_status.get("country_coverage_visibility", {})
    if not isinstance(coverage_visibility, dict):
        return False
    country_gap_rows = coverage_visibility.get("country_gap_rows", [])
    if not isinstance(country_gap_rows, list) or len(country_gap_rows) != 1:
        return False
    gap_row = country_gap_rows[0]
    if not isinstance(gap_row, dict) or str(gap_row.get("country_id")) != target_country_id:
        return False
    gap_details = gap_row.get("gap_details", [])
    if not isinstance(gap_details, list) or len(gap_details) != 1:
        return False
    gap_detail = gap_details[0]
    if not isinstance(gap_detail, dict):
        return False
    if not (
        str(gap_detail.get("domain")) == "B"
        and str(gap_detail.get("reason")) == "no_usable_input_data"
    ):
        return False
    source_reason_details = gap_detail.get("source_reason_details", [])
    if not isinstance(source_reason_details, list):
        return False
    observed_reason_pairs = {
        (str(item.get("source_id")), str(item.get("reason")))
        for item in source_reason_details
        if isinstance(item, dict)
    }
    return observed_reason_pairs == expected_reason_pairs



def build_governed_live_orchestrator(
    *,
    repo_root: Path,
    country_id: str = "UKR",
    country_ids: tuple[str, ...] | None = None,
    pilot_set: str | None = None,
    output_dir: Path | None = None,
) -> DailyRunOrchestrator:
    resolved_country_ids = _resolve_requested_country_ids(country_id, country_ids, pilot_set)
    mappings = _build_normalization_mappings()
    country_queries: dict[str, str] = {}
    country_codes: dict[str, str] = {}
    for resolved_country_id in resolved_country_ids:
        support = _SUPPORTED_LIVE_PILOT_COUNTRIES[resolved_country_id]
        country_name = _load_country_name(repo_root, resolved_country_id)
        country_queries[resolved_country_id] = support.get("gdelt_query") or country_name
        country_codes[resolved_country_id] = support["gdelt_code"]

    def _normalizer(source_id: str, domain: str, raw_records: list[dict[str, float]]):
        return normalize_records(
            source_id=source_id,
            domain=domain,
            raw_records=raw_records,
            mappings=mappings,
        )

    supported_world_bank_country_ids = tuple(
        country_id for country_id in resolved_country_ids if country_id in _WORLD_BANK_SUPPORTED_LIVE_COUNTRIES
    )
    country_expected_domains = {
        country_id: list(_GOVERNED_LIVE_DOMAINS_BY_COUNTRY.get(country_id, ["A", "B", "D"]))
        for country_id in resolved_country_ids
    }

    adapters = []
    if supported_world_bank_country_ids:
        adapters.append(WorldBankIndicatorsAdapter(country_ids=supported_world_bank_country_ids))
    adapters.extend(
        [
            GDELTDocAdapter(
                country_queries=country_queries,
                max_records=_gdelt_doc_max_records_for_country_count(len(resolved_country_ids)),
                inter_request_delay_seconds=_gdelt_doc_inter_request_delay_seconds_for_country_count(len(resolved_country_ids)),
                max_retry_delay_seconds=_gdelt_doc_max_retry_delay_seconds_for_country_count(len(resolved_country_ids)),
                request_timeout_seconds=_gdelt_doc_request_timeout_seconds_for_country_count(len(resolved_country_ids)),
                max_full_fetch_retries=_gdelt_doc_max_full_fetch_retries_for_country_count(len(resolved_country_ids)),
                full_fetch_retry_cooldown_seconds=_gdelt_doc_full_fetch_retry_cooldown_seconds_for_country_count(len(resolved_country_ids)),
            ),
            GDELTEventsAdapter(
                country_codes=country_codes,
                recent_export_count=(
                    _gdelt_events_recent_export_count_for_country_count(len(resolved_country_ids))
                    if len(resolved_country_ids) > 1
                    else 1
                ),
            ),
            GDACSAdapter(country_ids=set(resolved_country_ids)),
            # Domain C: GDACS data re-ingested as physical activity/disaster domain
            GDACSAdapter(country_ids=set(resolved_country_ids), source_id="SRC-GDACS-C", domain="C"),
            # Domain C: structured displacement signals
            UNHCRPopulationAdapter(country_ids=set(resolved_country_ids)),
            # Domain E: GDELT Doc data re-ingested filtered for cyber/tech/info-ops themes
            GDELTDocAdapter(
                country_queries=country_queries,
                source_id="SRC-GDELT-DOC-E",
                domain="E",
                max_records=_gdelt_doc_max_records_for_country_count(len(resolved_country_ids)),
                inter_request_delay_seconds=_gdelt_doc_inter_request_delay_seconds_for_country_count(len(resolved_country_ids)),
                max_retry_delay_seconds=_gdelt_doc_max_retry_delay_seconds_for_country_count(len(resolved_country_ids)),
                request_timeout_seconds=_gdelt_doc_request_timeout_seconds_for_country_count(len(resolved_country_ids)),
                max_full_fetch_retries=_gdelt_doc_max_full_fetch_retries_for_country_count(len(resolved_country_ids)),
                full_fetch_retry_cooldown_seconds=_gdelt_doc_full_fetch_retry_cooldown_seconds_for_country_count(len(resolved_country_ids)),
            ),
            # Domain E: global structured cyber-threat context
            CISAKEVAdapter(country_ids=set(resolved_country_ids)),
        ]
    )
    runtime_profile = "live-multi-country-v1" if len(resolved_country_ids) > 1 else "live-single-country-v1"
    country_set_id = (
        "MVP-COUNTRIES-LIVE-MULTI-v1"
        if len(resolved_country_ids) > 1
        else f"MVP-COUNTRIES-LIVE-{resolved_country_ids[0]}-v1"
    )

    reference_case_library = _load_reference_case_library()
    reference_case_library_summary = build_reference_case_library_summary(reference_case_library)
    replay_inputs = load_governed_historical_replay_inputs(repo_root)
    replay_case_library = load_validation_case_library(_VALIDATION_REFERENCE_CASE_LIBRARY_PATH)
    historical_replay_reviews = build_historical_replay_reviews(replay_case_library, replay_inputs)
    historical_replay_summary = build_historical_replay_summary(historical_replay_reviews)

    def _validation_view_model_builder(
        _primary_country_id: str,
        active_domains: list[str],
        run_state,
        normalized_records,
        country_domain_statuses,
        country_multi_domain_statuses,
        snapshot,
    ) -> dict[str, object] | None:
        validation_country_ids = _validation_candidate_country_ids(
            resolved_country_ids,
            normalized_records,
            country_domain_statuses,
            country_multi_domain_statuses,
        )
        if not validation_country_ids:
            return None
        validation_cases = [
            _build_live_runtime_validation_view_model(
                country_id,
                active_domains,
                run_state,
                normalized_records,
                country_domain_statuses,
                country_multi_domain_statuses,
                snapshot,
                country_expected_domains,
            )
            for country_id in validation_country_ids
        ]
        validation_cases = [case for case in validation_cases if case is not None]
        if not validation_cases:
            return None
        portfolio_summary = build_validation_portfolio_summary(validation_cases)
        return _build_live_runtime_validation_view_model(
            validation_country_ids[0],
            active_domains,
            run_state,
            normalized_records,
            country_domain_statuses,
            country_multi_domain_statuses,
            snapshot,
            country_expected_domains,
            validation_cases=validation_cases,
            portfolio_summary=portfolio_summary,
            reference_case_library=reference_case_library,
            reference_case_library_summary=reference_case_library_summary,
            historical_replay_reviews=historical_replay_reviews,
            historical_replay_summary=historical_replay_summary,
        )

    return DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalizer,
         feature_services=[DomainAFeatureService(), DomainBFeatureService(), DomainCFeatureService(), DomainDFeatureService(), DomainEFeatureService()],
        domain_status_analyzer=_default_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id=country_set_id,
        active_domains=["A", "B", "C", "D", "E"],
        rule_versions={
            "domain_status": "v1",
            "multi_domain_status": "v1",
            "runtime_profile": runtime_profile,
        },
        algorithm_version=runtime_profile,
        data_version="governed-live-sources-v1",
        artifacts_output_dir=output_dir,
        validation_view_model_builder=_validation_view_model_builder,
        requested_country_ids=resolved_country_ids,
        country_expected_domains=country_expected_domains,
    )



def _default_pipeline_retry_budget(requested_country_ids: tuple[str, ...]) -> int:
    if requested_country_ids == _EXTENDED_FOCUS_BROADER_LIVE_PILOT_SET:
        return 2
    if len(requested_country_ids) >= 24:
        return 0
    if len(requested_country_ids) >= 7:
        return 2
    return 1



def run_governed_live_pipeline(
    *,
    repo_root: Path,
    run_id: str,
    country_id: str = "UKR",
    country_ids: tuple[str, ...] | None = None,
    pilot_set: str | None = None,
    output_dir: Path | None = None,
    orchestrator_factory: Callable[..., object] = build_governed_live_orchestrator,
    pipeline_retry_sleep: Callable[[float], None] = sleep,
    pipeline_retry_cooldown_seconds: float = 40.0,
    max_pipeline_retries: int | None = None,
) -> DailyRunResult:
    resolved_country_ids = _resolve_requested_country_ids(country_id, country_ids, pilot_set)
    effective_max_pipeline_retries = (
        max_pipeline_retries
        if max_pipeline_retries is not None
        else _default_pipeline_retry_budget(resolved_country_ids)
    )
    requested_country_ids_for_factory = None if pilot_set is not None else resolved_country_ids
    requested_pilot_set_for_factory = pilot_set if pilot_set is not None else None
    current_output_dir = output_dir
    last_result: DailyRunResult | None = None
    for pipeline_attempt in range(effective_max_pipeline_retries + 1):
        orchestrator = orchestrator_factory(
            repo_root=repo_root,
            country_id=resolved_country_ids[0],
            country_ids=requested_country_ids_for_factory,
            pilot_set=requested_pilot_set_for_factory,
            output_dir=current_output_dir,
        )
        result = orchestrator.run(run_id)
        last_result = result
        if not (
            _should_retry_pipeline_after_gdelt_doc_failure(result, resolved_country_ids)
            or _should_retry_pipeline_after_gdelt_events_failure(result, resolved_country_ids)
            or _should_retry_pipeline_after_isolated_country_domain_b_gap(result, resolved_country_ids)
        ):
            return result
        if pipeline_attempt == effective_max_pipeline_retries:
            return result
        pipeline_retry_sleep(pipeline_retry_cooldown_seconds)
    assert last_result is not None
    return last_result



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the governed SIASA live-source runtime and write artifacts."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Path to the SIASA repository root.",
    )
    parser.add_argument(
        "--country-id",
        action="append",
        dest="country_ids",
        help=(
            "Governed live pilot country ISO3. Repeat for multi-country runs; "
            "supported: UKR, POL, ISR, TWN, RUS, CHN, IND, IRN, TUR, PAK, GEO, USA, DEU, EST, FIN, SAU, QAT, EGY, NGA, SDN, MMR."
        ),
    )
    parser.add_argument(
        "--pilot-set",
        choices=sorted(_NAMED_LIVE_PILOT_SETS),
        help=(
            "Named governed live pilot subset. "
            "'representative' expands to UKR,POL,ISR,TWN; "
            "'core-focus-initial' expands to UKR,RUS,CHN,TWN,ISR,POL; "
            "'core-focus-expanded' expands to UKR,RUS,CHN,TWN,ISR,IND,POL; "
            "'core-focus-broader' expands to UKR,RUS,CHN,TWN,IRN,ISR,TUR,IND,POL; "
            "'core-focus-complete' expands to UKR,RUS,CHN,TWN,IRN,ISR,TUR,IND,PAK,GEO,POL; "
            "'extended-focus-initial' expands to USA,DEU,EST,FIN; "
            "'extended-focus-broader' expands to USA,DEU,EST,FIN,POL; "
            "'extended-focus-energy-initial' expands to SAU,QAT,EGY; "
            "'extended-focus-crisis-initial' expands to NGA,SDN,MMR."
        ),
    )
    parser.add_argument(
        "--run-id",
        default="RUN-LIVE-001",
        help="Run identifier to stamp into artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        default="build/run_artifacts/latest",
        help="Artifact output directory.",
    )
    args = parser.parse_args(argv)
    resolved_country_ids = _resolve_requested_country_ids(
        "UKR",
        tuple(args.country_ids) if args.country_ids else None,
        args.pilot_set,
    )

    result = run_governed_live_pipeline(
        repo_root=Path(args.repo_root),
        country_id=resolved_country_ids[0],
        country_ids=tuple(args.country_ids) if args.country_ids else None,
        pilot_set=args.pilot_set,
        run_id=args.run_id,
        output_dir=Path(args.output_dir),
    )
    print(
        f"run_status={result.run_state.status} countries={','.join(resolved_country_ids)} "
        f"failed_sources={','.join(result.run_state.failed_sources) or 'none'} output_dir={args.output_dir}"
    )
    return 0 if result.run_state.status in {"success", "partial_success"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
