from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from siasa.adapters import GDACSAdapter, GDELTDocAdapter, GDELTEventsAdapter, WorldBankIndicatorsAdapter
from siasa.data.normalization_mappings import NormalizationMappingVersion
from siasa.data.normalization_service import normalize_records
from siasa.features.domain_a import DomainAFeatureService
from siasa.features.domain_b import DomainBFeatureService
from siasa.features.domain_d import DomainDFeatureService
from siasa.readmodels.validation_backtest import build_validation_backtest_read_model
from siasa.runs.orchestrator import DailyRunOrchestrator, DailyRunResult
from siasa.scoring.data_sufficiency import evaluate_data_sufficiency
from siasa.scoring.domain_status import derive_domain_status
from siasa.scoring.multi_domain_status import derive_multi_domain_status
from siasa.catalog import load_country_set
from siasa.validation.cases import ValidationCase, compare_expected_vs_observed

_SUPPORTED_LIVE_PILOT_COUNTRIES = {
    "UKR": {"gdelt_query": "Ukraine", "gdelt_code": "UP"},
    "POL": {"gdelt_query": "Poland", "gdelt_code": "PL"},
    "ISR": {"gdelt_query": "Israel", "gdelt_code": "IS"},
    "TWN": {"gdelt_query": "Taiwan", "gdelt_code": "TW"},
}



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
    ]



def _default_domain_status_analyzer(domain: str, features):
    sufficiency = evaluate_data_sufficiency(features)
    anomaly_score = {"A": 0.7, "B": 0.3, "D": 0.1}.get(domain, 0.1)
    return derive_domain_status(domain, anomaly_score=anomaly_score, sufficiency=sufficiency)



def _build_live_runtime_validation_view_model(
    primary_country_id: str,
    active_domains: list[str],
    run_state,
    normalized_records,
    country_domain_statuses,
    country_multi_domain_statuses,
    snapshot,
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
    validation_case = ValidationCase(
        case_id=f"VAL-{primary_country_id}-LIVE-PILOT-SUPPORT",
        country_id=primary_country_id,
        case_name=f"Governed live runtime support case for {primary_country_id}",
        case_type="pilot_runtime_support_case",
        time_start=timestamps[0],
        time_end=timestamps[-1],
        expected_domains=list(active_domains),
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
    observed_status = country_multi_domain_statuses[primary_country_id].status
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
    )
    validation_view_model["comparison_mode"] = "runtime_support_check"
    validation_view_model["snapshot_id"] = snapshot.snapshot_id
    validation_view_model["run_id"] = run_state.run_id
    return validation_view_model



def build_governed_live_orchestrator(
    *,
    repo_root: Path,
    country_id: str = "UKR",
    country_ids: tuple[str, ...] | None = None,
    output_dir: Path | None = None,
) -> DailyRunOrchestrator:
    resolved_country_ids = _normalize_country_ids(country_id, country_ids)
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

    adapters = [
        WorldBankIndicatorsAdapter(country_ids=resolved_country_ids),
        GDELTDocAdapter(country_queries=country_queries),
        GDELTEventsAdapter(country_codes=country_codes),
        GDACSAdapter(country_ids=set(resolved_country_ids)),
    ]
    runtime_profile = "live-multi-country-v1" if len(resolved_country_ids) > 1 else "live-single-country-v1"
    country_set_id = (
        "MVP-COUNTRIES-LIVE-MULTI-v1"
        if len(resolved_country_ids) > 1
        else f"MVP-COUNTRIES-LIVE-{resolved_country_ids[0]}-v1"
    )

    def _validation_view_model_builder(
        _primary_country_id: str,
        active_domains: list[str],
        run_state,
        normalized_records,
        country_domain_statuses,
        country_multi_domain_statuses,
        snapshot,
    ) -> dict[str, object] | None:
        validation_country_id = next(
            (
                country_id
                for country_id in resolved_country_ids
                if country_id in country_multi_domain_statuses
                and any(record.country_id == country_id for record in normalized_records)
                and country_domain_statuses.get(country_id)
            ),
            None,
        )
        if validation_country_id is None:
            return None
        return _build_live_runtime_validation_view_model(
            validation_country_id,
            active_domains,
            run_state,
            normalized_records,
            country_domain_statuses,
            country_multi_domain_statuses,
            snapshot,
        )

    return DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalizer,
        feature_services=[DomainAFeatureService(), DomainBFeatureService(), DomainDFeatureService()],
        domain_status_analyzer=_default_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id=country_set_id,
        active_domains=["A", "B", "D"],
        rule_versions={
            "domain_status": "v1",
            "multi_domain_status": "v1",
            "runtime_profile": runtime_profile,
        },
        algorithm_version=runtime_profile,
        data_version="governed-live-sources-v1",
        artifacts_output_dir=output_dir,
        validation_view_model_builder=_validation_view_model_builder,
    )



def run_governed_live_pipeline(
    *,
    repo_root: Path,
    run_id: str,
    country_id: str = "UKR",
    country_ids: tuple[str, ...] | None = None,
    output_dir: Path | None = None,
) -> DailyRunResult:
    orchestrator = build_governed_live_orchestrator(
        repo_root=repo_root,
        country_id=country_id,
        country_ids=country_ids,
        output_dir=output_dir,
    )
    return orchestrator.run(run_id)



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
            "supported: UKR, POL, ISR, TWN."
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
    resolved_country_ids = _normalize_country_ids("UKR", tuple(args.country_ids) if args.country_ids else None)

    result = run_governed_live_pipeline(
        repo_root=Path(args.repo_root),
        country_id=resolved_country_ids[0],
        country_ids=resolved_country_ids,
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
