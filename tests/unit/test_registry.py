"""Tests for SIASA Data Registry — Country and Signal registries (AP-13.2).

Verifies:
- SwR-057: Country registry completeness and validation
- SwR-058: Signal registry completeness and metadata validation
"""
from __future__ import annotations

from pathlib import Path

from siasa.data.registry import (
    CountryRegistryEntry,
    SignalRegistryEntry,
    load_country_registry,
    load_signal_registry,
    validate_country_registry,
    validate_signal_registry,
    KNOWN_ACTIVE_SIGNAL_KEYS,
)


# ---------------------------------------------------------------------------
# SwR-057: Country registry
# ---------------------------------------------------------------------------

def test_country_registry_entry_has_required_fields() -> None:
    """CountryRegistryEntry must contain all fields from SwR-057."""
    entry = CountryRegistryEntry(
        canonical_id="DEU",
        iso2="DE",
        name_en="Germany",
        region="Europe",
        subregion="Western Europe",
        active_in_siasa=True,
    )
    assert entry.canonical_id == "DEU"
    assert entry.iso2 == "DE"
    assert entry.name_en == "Germany"
    assert entry.region == "Europe"
    assert entry.active_in_siasa is True


def test_load_country_registry_returns_entries() -> None:
    """load_country_registry must return a non-empty list of entries (SwR-057)."""
    entries = load_country_registry()
    assert len(entries) >= 30  # At least MVP country count
    # All entries must have ISO3 canonical_id
    assert all(len(e.canonical_id) == 3 for e in entries)


def test_country_registry_covers_all_governed_pilot_countries() -> None:
    """Registry must contain all countries from _SUPPORTED_LIVE_PILOT_COUNTRIES (SwR-057)."""
    from siasa.runs.live_runtime import _SUPPORTED_LIVE_PILOT_COUNTRIES
    entries = load_country_registry()
    registry_ids = {e.canonical_id for e in entries}
    pilot_ids = set(_SUPPORTED_LIVE_PILOT_COUNTRIES.keys())
    missing = pilot_ids - registry_ids
    assert missing == set(), f"Pilot countries missing from registry: {missing}"


def test_country_registry_has_no_duplicate_ids() -> None:
    """No duplicate canonical_id in the registry (SwR-057)."""
    entries = load_country_registry()
    ids = [e.canonical_id for e in entries]
    assert len(ids) == len(set(ids)), f"Duplicates: {[x for x in ids if ids.count(x) > 1]}"


def test_validate_country_registry_passes() -> None:
    """validate_country_registry must not raise on the shipped registry (SwR-057)."""
    entries = load_country_registry()
    issues = validate_country_registry(entries)
    assert issues == [], f"Validation issues: {issues}"


# ---------------------------------------------------------------------------
# SwR-058: Signal registry
# ---------------------------------------------------------------------------

def test_signal_registry_entry_has_required_fields() -> None:
    """SignalRegistryEntry must contain all metadata fields from SwR-058."""
    entry = SignalRegistryEntry(
        signal_key="conflict_event_count",
        domain="B",
        source_id="SRC-GDELT-EVENTS",
        description="Count of conflict events from GDELT",
        unit="count",
        native_granularity="15min",
        aggregation_method="sum",
    )
    assert entry.signal_key == "conflict_event_count"
    assert entry.domain == "B"
    assert entry.aggregation_method == "sum"


def test_load_signal_registry_returns_entries() -> None:
    """load_signal_registry must return a non-empty list (SwR-058)."""
    entries = load_signal_registry()
    assert len(entries) >= 15  # At least core signals
    # Each entry has a non-empty signal_key
    assert all(e.signal_key for e in entries)


def test_signal_registry_covers_known_active_keys() -> None:
    """Registry must contain all KNOWN_ACTIVE_SIGNAL_KEYS (SwR-058)."""
    entries = load_signal_registry()
    registry_keys = {e.signal_key for e in entries}
    missing = KNOWN_ACTIVE_SIGNAL_KEYS - registry_keys
    assert missing == set(), f"Active signal keys missing from registry: {missing}"


def test_signal_registry_has_no_duplicate_keys() -> None:
    """No duplicate signal_key in the registry (SwR-058)."""
    entries = load_signal_registry()
    keys = [e.signal_key for e in entries]
    assert len(keys) == len(set(keys)), f"Duplicates: {[x for x in keys if keys.count(x) > 1]}"


def test_signal_registry_aggregation_methods_are_valid() -> None:
    """aggregation_method must be one of the allowed values (SwR-058)."""
    allowed = {"sum", "mean", "max", "last", "count", "none"}
    entries = load_signal_registry()
    for entry in entries:
        assert entry.aggregation_method in allowed, (
            f"{entry.signal_key}: invalid aggregation_method '{entry.aggregation_method}'"
        )


def test_validate_signal_registry_passes() -> None:
    """validate_signal_registry must not raise on the shipped registry (SwR-058)."""
    entries = load_signal_registry()
    issues = validate_signal_registry(entries)
    assert issues == [], f"Validation issues: {issues}"
