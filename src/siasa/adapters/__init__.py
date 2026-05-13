"""Source adapter abstractions for SIASA."""

from .base import FetchResult, SourceAdapter
from .fetch_metadata import FetchMetadataRecord
from .world_bank import WorldBankIndicatorsAdapter

__all__ = ["FetchResult", "SourceAdapter", "FetchMetadataRecord", "WorldBankIndicatorsAdapter"]
