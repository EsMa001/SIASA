from __future__ import annotations

from pathlib import Path
import yaml

from .models import ConfigurationEntry, CountrySetRecord, SourceCatalogRecord


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected top-level mapping in {path}")
    return data


def load_source_catalog(path: Path) -> list[SourceCatalogRecord]:
    payload = _load_yaml(path)
    rows = payload.get("data_sources", [])
    records: list[SourceCatalogRecord] = []
    for row in rows:
        records.append(
            SourceCatalogRecord(
                domain=(row.get("Ebene") or "").strip(),
                source_name=(row.get("Quelle") or "").strip(),
                status=(row.get("Status") or "").strip(),
                signals=(row.get("Signale") or "").strip(),
                access=(row.get("Zugriff") or "").strip(),
                history=(row.get("Historie") or "").strip(),
                note=(row.get("Bemerkung") or "").strip(),
            )
        )
    return records


def load_country_set(path: Path) -> list[CountrySetRecord]:
    payload = _load_yaml(path)
    rows = payload.get("mvp_countries", [])
    records: list[CountrySetRecord] = []
    for row in rows:
        records.append(
            CountrySetRecord(
                iso3=(row.get("ISO3") or "").strip(),
                country_name=(row.get("Land") or "").strip(),
                priority=(row.get("Priorität") or "").strip(),
                selection_type=(row.get("Auswahltyp") or "").strip(),
                region=(row.get("Region") or "").strip(),
                rationale=(row.get("Begründung") or "").strip(),
            )
        )
    return records


def load_config_entries(path: Path) -> list[ConfigurationEntry]:
    payload = _load_yaml(path)
    rows = payload.get("config_tables", [])
    records: list[ConfigurationEntry] = []
    for row in rows:
        records.append(
            ConfigurationEntry(
                config_type=(row.get("Konfigurationstyp") or "").strip(),
                value=(row.get("Wert") or "").strip(),
                meaning=(row.get("Bedeutung") or "").strip(),
                decision=(row.get("Festlegung") or "").strip(),
            )
        )
    return records
