"""Source adapter abstractions for SIASA."""

from .base import FetchResult, SourceAdapter
from .fetch_metadata import FetchMetadataRecord
from .cisa_kev import CISAKEVAdapter
from .gdacs import GDACSAdapter
from .gdelt_doc import GDELTDocAdapter
from .gdelt_events import GDELTEventsAdapter
from .reliefweb import ReliefWebAdapter
from .ucdp import UCDPAdapter
from .unhcr import UNHCRPopulationAdapter
from .world_bank import WorldBankIndicatorsAdapter

__all__ = [
    "FetchResult",
    "SourceAdapter",
    "FetchMetadataRecord",
    "CISAKEVAdapter",
    "ReliefWebAdapter",
    "WorldBankIndicatorsAdapter",
    "GDACSAdapter",
    "GDELTDocAdapter",
    "GDELTEventsAdapter",
    "UCDPAdapter",
    "UNHCRPopulationAdapter",
]
