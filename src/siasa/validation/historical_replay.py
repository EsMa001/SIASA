from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from siasa.data.normalized_models import NormalizedRecord
from siasa.features.domain_a import DomainAFeatureService
from siasa.features.domain_b import DomainBFeatureService
from siasa.features.domain_d import DomainDFeatureService
from siasa.scoring.data_sufficiency import evaluate_data_sufficiency
from siasa.scoring.domain_status import derive_domain_status
from siasa.scoring.multi_domain_status import derive_multi_domain_status
from siasa.validation.cases import ValidationCase, compare_expected_vs_observed


@dataclass(frozen=True)
class HistoricalReplayInput:
    case_id: str
    review_basis: str
    normalized_records: list[NormalizedRecord]
    replay_input_source_ids: list[str] = field(default_factory=list)
    replay_input_country_ids: list[str] = field(default_factory=list)
    archival_data_files: list[str] = field(default_factory=list)
    provenance_notes: str = ""
    known_limitations: list[str] = field(default_factory=list)


_FEATURE_SERVICES = (DomainAFeatureService(), DomainBFeatureService(), DomainDFeatureService())
_DOMAIN_ANOMALY_SCORES = {"A": 0.7, "B": 0.3, "D": 0.1}



def _normalized_record_source_ids(normalized_records: list[NormalizedRecord]) -> list[str]:
    return sorted({str(record.provenance_source_id) for record in normalized_records if record.provenance_source_id})



def _normalized_record_country_ids(normalized_records: list[NormalizedRecord]) -> list[str]:
    return sorted({str(record.country_id) for record in normalized_records if record.country_id})


def _replay_source_coverage_ratio(validation_case: ValidationCase, replay_input: HistoricalReplayInput) -> float:
    expected_sources = {str(source_id) for source_id in validation_case.reference_sources if str(source_id)}
    if not expected_sources:
        return 1.0
    observed_sources = {str(source_id) for source_id in replay_input.replay_input_source_ids if str(source_id)}
    return round(len(expected_sources & observed_sources) / len(expected_sources), 2)


def _replay_provenance_completeness_ratio(replay_input: HistoricalReplayInput) -> float:
    checks = [
        bool(replay_input.replay_input_source_ids),
        bool(replay_input.replay_input_country_ids),
    ]
    if replay_input.review_basis == "provider_backed_archival_replay":
        checks.extend(
            [
                bool(replay_input.archival_data_files),
                bool(replay_input.provenance_notes),
                bool(replay_input.known_limitations),
            ]
        )
    return round(sum(1 for check in checks if check) / len(checks), 2) if checks else 0.0


def _replay_evidence_score(
    *,
    status_match: bool,
    domain_match_ratio: float,
    replay_source_coverage_ratio: float,
    replay_provenance_completeness_ratio: float,
) -> float:
    score = (
        (0.4 if status_match else 0.0)
        + (0.3 * domain_match_ratio)
        + (0.2 * replay_source_coverage_ratio)
        + (0.1 * replay_provenance_completeness_ratio)
    )
    return round(score, 2)


def _replay_evidence_tier(replay_evidence_score: float) -> str:
    if replay_evidence_score >= 0.95:
        return "verified_replay_evidence"
    if replay_evidence_score >= 0.75:
        return "strong_replay_evidence"
    if replay_evidence_score >= 0.5:
        return "partial_replay_evidence"
    return "weak_replay_evidence"



def load_historical_replay_inputs(path: Path) -> dict[str, HistoricalReplayInput]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    replay_cases = data.get("replay_cases", [])
    if not isinstance(replay_cases, list):
        raise ValueError("replay_cases must be a list")

    loaded: dict[str, HistoricalReplayInput] = {}
    for case_record in replay_cases:
        if not isinstance(case_record, dict):
            continue
        case_id = str(case_record.get("case_id", "")).strip()
        if not case_id:
            raise ValueError("historical replay case_id is required")
        review_basis = str(case_record.get("review_basis", "fixture_backed_historical_replay"))
        raw_records = case_record.get("normalized_records", [])
        if not isinstance(raw_records, list):
            raise ValueError(f"normalized_records must be a list for case_id={case_id}")
        normalized_records: list[NormalizedRecord] = []
        for index, record in enumerate(raw_records, start=1):
            if not isinstance(record, dict):
                continue
            normalized_records.append(
                NormalizedRecord(
                    normalized_id=str(record.get("normalized_id") or f"REPLAY-{case_id}-{index}"),
                    country_id=str(record["country_id"]),
                    timestamp=str(record.get("timestamp") or ""),
                    domain=str(record["domain"]),
                    signal_key=str(record["signal_key"]),
                    value=float(record["value"]),
                    provenance_source_id=str(record["provenance_source_id"]),
                    quality_context=dict(record.get("quality_context", {})) if isinstance(record.get("quality_context", {}), dict) else {},
                )
            )
        loaded[case_id] = HistoricalReplayInput(
            case_id=case_id,
            review_basis=review_basis,
            normalized_records=normalized_records,
            replay_input_source_ids=_normalized_record_source_ids(normalized_records),
            replay_input_country_ids=_normalized_record_country_ids(normalized_records),
        )
    return loaded



def _derive_country_replay_status(normalized_records: list[NormalizedRecord], country_id: str) -> tuple[list[str], str]:
    features = [
        feature
        for service in _FEATURE_SERVICES
        for feature in service.compute(normalized_records)
        if feature.country_id == country_id
    ]
    domain_results = []
    for domain in sorted({feature.domain for feature in features}):
        domain_features = [feature for feature in features if feature.domain == domain]
        if not domain_features:
            continue
        domain_results.append(
            derive_domain_status(
                domain,
                anomaly_score=_DOMAIN_ANOMALY_SCORES.get(domain, 0.1),
                sufficiency=evaluate_data_sufficiency(domain_features),
            )
        )
    replayed_domains = [result.domain for result in domain_results]
    replayed_status = derive_multi_domain_status(domain_results).status if domain_results else "S6"
    return replayed_domains, replayed_status



def build_historical_replay_reviews(
    reference_case_library: list[ValidationCase],
    replay_inputs_by_case_id: dict[str, HistoricalReplayInput],
) -> list[dict[str, object]]:
    reviews: list[dict[str, object]] = []
    for validation_case in reference_case_library:
        replay_input = replay_inputs_by_case_id.get(validation_case.case_id)
        if replay_input is None:
            continue
        replayed_domains, replayed_status = _derive_country_replay_status(
            replay_input.normalized_records,
            validation_case.country_id,
        )
        comparison = compare_expected_vs_observed(
            validation_case=validation_case,
            observed_domains=replayed_domains,
            observed_status=replayed_status,
            expected_status=validation_case.expected_status,
        )
        missing_expected_domains = [
            domain for domain in validation_case.expected_domains if domain not in replayed_domains
        ]
        unexpected_observed_domains = [
            domain for domain in replayed_domains if domain not in validation_case.expected_domains
        ]
        status_match = bool(comparison["status_match"])
        replay_source_coverage_ratio = _replay_source_coverage_ratio(validation_case, replay_input)
        replay_provenance_completeness_ratio = _replay_provenance_completeness_ratio(replay_input)
        replay_evidence_score = _replay_evidence_score(
            status_match=status_match,
            domain_match_ratio=float(comparison["domain_match_ratio"]),
            replay_source_coverage_ratio=replay_source_coverage_ratio,
            replay_provenance_completeness_ratio=replay_provenance_completeness_ratio,
        )
        replay_evidence_tier = _replay_evidence_tier(replay_evidence_score)
        review_verdict = (
            "replay_match"
            if status_match and not missing_expected_domains and not unexpected_observed_domains
            else "replay_match_with_gaps"
            if status_match
            else "replay_mismatch"
        )
        reviews.append(
            {
                "case_id": validation_case.case_id,
                "country_id": validation_case.country_id,
                "review_basis": replay_input.review_basis,
                "replay_input_source_ids": list(replay_input.replay_input_source_ids),
                "replay_input_country_ids": list(replay_input.replay_input_country_ids),
                "archival_data_files": list(replay_input.archival_data_files),
                "provenance_notes": replay_input.provenance_notes,
                "replay_known_limitations": list(replay_input.known_limitations),
                "replay_source_coverage_ratio": replay_source_coverage_ratio,
                "replay_provenance_completeness_ratio": replay_provenance_completeness_ratio,
                "replay_evidence_score": replay_evidence_score,
                "replay_evidence_tier": replay_evidence_tier,
                "replayed_status": replayed_status,
                "expected_status": validation_case.expected_status,
                "status_match": status_match,
                "expected_domains": list(validation_case.expected_domains),
                "replayed_domains": replayed_domains,
                "domain_match_ratio": comparison["domain_match_ratio"],
                "review_verdict": review_verdict,
                "missing_expected_domains": missing_expected_domains,
                "unexpected_observed_domains": unexpected_observed_domains,
                "replay_input_record_count": len(replay_input.normalized_records),
            }
        )
    return reviews
