from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizationMappingVersion:
    mapping_id: str
    source_id: str
    version: str
    is_active: bool = False


def resolve_active_mapping(mappings: list[NormalizationMappingVersion], source_id: str) -> NormalizationMappingVersion:
    for mapping in mappings:
        if mapping.source_id == source_id and mapping.is_active:
            return mapping
    raise ValueError(f"No active mapping found for source_id={source_id}; active mapping is required")
