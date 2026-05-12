from __future__ import annotations

from typing import Any

from .normalization_mappings import NormalizationMappingVersion, resolve_active_mapping
from .normalized_models import NormalizedRecord


_ALLOWED_QUALITY_FIELDS = {"expected_source_count", "freshness_hours", "quality_flag", "period"}


def normalize_records(
    *,
    source_id: str,
    domain: str,
    raw_records: list[dict[str, Any]],
    mappings: list[NormalizationMappingVersion],
) -> list[NormalizedRecord]:
    mapping = resolve_active_mapping(mappings, source_id)
    normalized: list[NormalizedRecord] = []
    for index, raw_record in enumerate(raw_records, start=1):
        quality_context = {
            key: raw_record[key]
            for key in _ALLOWED_QUALITY_FIELDS
            if key in raw_record and raw_record[key] is not None
        }
        quality_context["mapping_id"] = mapping.mapping_id
        quality_context["mapping_version"] = mapping.version
        normalized.append(
            NormalizedRecord(
                normalized_id=f"NORM-{source_id}-{index}",
                country_id=str(raw_record["country_id"]),
                timestamp=str(raw_record.get("timestamp") or raw_record.get("period") or ""),
                domain=domain,
                signal_key=str(raw_record["signal_key"]),
                value=float(raw_record["value"]),
                provenance_source_id=source_id,
                quality_context=quality_context,
            )
        )
    return normalized
