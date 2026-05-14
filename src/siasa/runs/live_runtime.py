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
from siasa.runs.orchestrator import DailyRunOrchestrator, DailyRunResult
from siasa.scoring.data_sufficiency import evaluate_data_sufficiency
from siasa.scoring.domain_status import derive_domain_status
from siasa.scoring.multi_domain_status import derive_multi_domain_status
from siasa.catalog import load_country_set

_SUPPORTED_LIVE_PILOT_COUNTRIES = {
    "UKR": {"gdelt_query": "Ukraine", "gdelt_code": "UP"},
    "POL": {"gdelt_query": "Poland", "gdelt_code": "PL"},
    "ISR": {"gdelt_query": "Israel", "gdelt_code": "IS"},
    "TWN": {"gdelt_query": "Taiwan", "gdelt_code": "TW"},
}



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



def build_governed_live_orchestrator(
    *,
    repo_root: Path,
    country_id: str = "UKR",
    output_dir: Path | None = None,
) -> DailyRunOrchestrator:
    country_id = country_id.upper()
    support = _SUPPORTED_LIVE_PILOT_COUNTRIES.get(country_id)
    if support is None:
        supported = ", ".join(sorted(_SUPPORTED_LIVE_PILOT_COUNTRIES))
        raise ValueError(
            f"Supported live pilot countries are: {supported}; received {country_id}"
        )

    country_name = _load_country_name(repo_root, country_id)
    mappings = _build_normalization_mappings()
    doc_query = support.get("gdelt_query") or country_name
    gdelt_code = support["gdelt_code"]

    def _normalizer(source_id: str, domain: str, raw_records: list[dict[str, float]]):
        return normalize_records(
            source_id=source_id,
            domain=domain,
            raw_records=raw_records,
            mappings=mappings,
        )

    adapters = [
        WorldBankIndicatorsAdapter(country_ids=(country_id,)),
        GDELTDocAdapter(country_queries={country_id: doc_query}),
        GDELTEventsAdapter(country_codes={country_id: gdelt_code}),
        GDACSAdapter(country_ids={country_id}),
    ]
    return DailyRunOrchestrator(
        adapters=adapters,
        normalizer=_normalizer,
        feature_services=[DomainAFeatureService(), DomainBFeatureService(), DomainDFeatureService()],
        domain_status_analyzer=_default_domain_status_analyzer,
        multi_domain_status_analyzer=derive_multi_domain_status,
        country_set_id=f"MVP-COUNTRIES-LIVE-{country_id}-v1",
        active_domains=["A", "B", "D"],
        rule_versions={
            "domain_status": "v1",
            "multi_domain_status": "v1",
            "runtime_profile": "live-single-country-v1",
        },
        algorithm_version="live-single-country-v1",
        data_version="governed-live-sources-v1",
        artifacts_output_dir=output_dir,
    )



def run_governed_live_pipeline(
    *,
    repo_root: Path,
    run_id: str,
    country_id: str = "UKR",
    output_dir: Path | None = None,
) -> DailyRunResult:
    orchestrator = build_governed_live_orchestrator(
        repo_root=repo_root,
        country_id=country_id,
        output_dir=output_dir,
    )
    return orchestrator.run(run_id)



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the governed SIASA live-source single-country pilot and write artifacts."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Path to the SIASA repository root.",
    )
    parser.add_argument(
        "--country-id",
        default="UKR",
        help="Governed live pilot country ISO3. Currently supported: UKR, POL, ISR, TWN.",
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

    result = run_governed_live_pipeline(
        repo_root=Path(args.repo_root),
        country_id=args.country_id,
        run_id=args.run_id,
        output_dir=Path(args.output_dir),
    )
    print(
        f"run_status={result.run_state.status} failed_sources={','.join(result.run_state.failed_sources) or 'none'} "
        f"output_dir={args.output_dir}"
    )
    return 0 if result.run_state.status in {"success", "partial_success"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
