"""Source adapter abstractions for SIASA."""

from .base import FetchResult, SourceAdapter
from .fetch_metadata import FetchMetadataRecord

__all__ = ["FetchResult", "SourceAdapter", "FetchMetadataRecord"]
