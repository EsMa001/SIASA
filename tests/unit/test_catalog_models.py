from pathlib import Path

import pytest

from siasa.catalog.loaders import load_config_entries, load_country_set, load_source_catalog
from siasa.catalog.models import ConfigurationEntry, CountrySetRecord, SourceCatalogRecord

ROOT = Path(__file__).resolve().parents[2]


def test_load_source_catalog_returns_typed_records() -> None:
    records = load_source_catalog(ROOT / "vmodel/project/data_sources.yaml")

    assert records
    assert isinstance(records[0], SourceCatalogRecord)
    assert records[0].domain == "A"
    assert records[0].source_name == "GDELT 2.0 Events/GKG/DOC API"
    assert records[0].status == "Core"


def test_load_country_set_returns_typed_records() -> None:
    countries = load_country_set(ROOT / "vmodel/project/mvp_countries.yaml")

    assert countries
    assert isinstance(countries[0], CountrySetRecord)
    assert countries[0].iso3 == "UKR"
    assert countries[0].priority == "P1"


def test_load_config_entries_returns_typed_records() -> None:
    entries = load_config_entries(ROOT / "vmodel/project/config_tables.yaml")

    assert entries
    assert isinstance(entries[0], ConfigurationEntry)
    assert entries[0].config_type == "Country Priority"


def test_source_catalog_validation_rejects_missing_required_field(tmp_path: Path) -> None:
    broken = tmp_path / "broken_sources.yaml"
    broken.write_text(
        "data_sources:\n- Ebene: A\n  Status: Core\n  Zugriff: frei\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Quelle"):
        load_source_catalog(broken)


def test_country_set_validation_rejects_invalid_iso3(tmp_path: Path) -> None:
    broken = tmp_path / "broken_countries.yaml"
    broken.write_text(
        "mvp_countries:\n- ISO3: UKRA\n  Land: Ukraine\n  Priorität: P1\n  Auswahltyp: Core Focus\n  Region: Europe\n  Begründung: test\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ISO3"):
        load_country_set(broken)


def test_config_entries_group_by_type() -> None:
    entries = load_config_entries(ROOT / "vmodel/project/config_tables.yaml")

    grouped = ConfigurationEntry.group_by_type(entries)

    assert set(grouped) >= {"Country Priority", "Source Status", "Baseline Mode"}
    assert grouped["Country Priority"][0].value == "P1"
