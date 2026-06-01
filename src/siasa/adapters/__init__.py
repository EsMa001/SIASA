"""Source adapter abstractions for SIASA."""

from .base import FetchResult, SourceAdapter
from .fetch_metadata import FetchMetadataRecord
from .gdacs import GDACSAdapter
from .gdelt_doc import GDELTDocAdapter
from .gdelt_events import GDELTEventsAdapter
from .ucdp import UCDPAdapter
from .unhcr import UNHCRPopulationAdapter
from .world_bank import WorldBankIndicatorsAdapter

__all__ = [
    "FetchResult",
    "SourceAdapter",
    "FetchMetadataRecord",
    "WorldBankIndicatorsAdapter",
    "GDACSAdapter",
    "GDELTDocAdapter",
    "GDELTEventsAdapter",
    "UCDPAdapter",
    "UNHCRPopulationAdapter",
]
