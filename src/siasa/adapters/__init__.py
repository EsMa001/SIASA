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
from .frankfurter import FrankfurterAdapter
from .voidly import VoidlyAdapter
from .hdx_inform import HDXInformRiskAdapter
from .imf_sdmx import IMFDataMapperAdapter
from .who_gho import WHOGHOAdapter
from .idmc_displacement import IDMCDisplacementAdapter
from .ioda_outages import IODAOutageAdapter
from .ooni_censorship import OONICensorshipAdapter
from .fewsnet import FEWSNETAdapter
from .opensanctions import OpenSanctionsAdapter
from .hdx_hapi import HDXHAPIAdapter

__all__ = [
    "FetchResult",
    "SourceAdapter",
    "FetchMetadataRecord",
    "CISAKEVAdapter",
    "FrankfurterAdapter",
    "HDXInformRiskAdapter",
    "ReliefWebAdapter",
    "VoidlyAdapter",
    "WorldBankIndicatorsAdapter",
    "GDACSAdapter",
    "GDELTDocAdapter",
    "GDELTEventsAdapter",
    "UCDPAdapter",
    "UNHCRPopulationAdapter",
    "IMFDataMapperAdapter",
    "WHOGHOAdapter",
    "IDMCDisplacementAdapter",
    "IODAOutageAdapter",
    "OONICensorshipAdapter",
    "FEWSNETAdapter",
    "OpenSanctionsAdapter",
    "HDXHAPIAdapter",
]
