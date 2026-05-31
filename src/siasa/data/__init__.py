"""Raw and normalized data models for SIASA."""

from .normalization_mappings import NormalizationMappingVersion, resolve_active_mapping
from .normalization_service import normalize_records
from .normalized_models import NormalizedRecord
from .raw_models import RawRecord
from .storage import (
    CountryDomainScoreEntry,
    RunHistoryEntry,
    SourceExecutionEntry,
    load_country_domain_time_series,
    load_latest_country_scores,
    load_recent_runs,
    load_source_results_for_run,
    persist_country_domain_scores,
    persist_operational_latest_run,
)

__all__ = [
    "RawRecord",
    "NormalizedRecord",
    "NormalizationMappingVersion",
    "resolve_active_mapping",
    "normalize_records",
    "RunHistoryEntry",
    "SourceExecutionEntry",
    "CountryDomainScoreEntry",
    "persist_operational_latest_run",
    "persist_country_domain_scores",
    "load_recent_runs",
    "load_source_results_for_run",
    "load_country_domain_time_series",
    "load_latest_country_scores",
]
