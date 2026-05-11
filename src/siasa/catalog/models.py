from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
import re


@dataclass(frozen=True)
class SourceCatalogRecord:
    domain: str
    source_name: str
    status: str
    signals: str
    access: str
    history: str
    note: str = ""

    def __post_init__(self) -> None:
        if not self.source_name:
            raise ValueError("Quelle is required")
        if not self.domain:
            raise ValueError("Ebene is required")


@dataclass(frozen=True)
class CountrySetRecord:
    iso3: str
    country_name: str
    priority: str
    selection_type: str
    region: str
    rationale: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z]{3}", self.iso3):
            raise ValueError("ISO3 must be exactly three uppercase letters")
        if not self.country_name:
            raise ValueError("Land is required")


@dataclass(frozen=True)
class ConfigurationEntry:
    config_type: str
    value: str
    meaning: str
    decision: str

    def __post_init__(self) -> None:
        if not self.config_type:
            raise ValueError("Konfigurationstyp is required")
        if not self.value:
            raise ValueError("Wert is required")

    @staticmethod
    def group_by_type(entries: list["ConfigurationEntry"]) -> dict[str, list["ConfigurationEntry"]]:
        grouped: dict[str, list[ConfigurationEntry]] = defaultdict(list)
        for entry in entries:
            grouped[entry.config_type].append(entry)
        return dict(grouped)
