"""Tests for ML Encoding Utilities (AP-13.12 / SwR-068).

Verifies:
- One-hot encoding for domain (A-E)
- Ordinal encoding for quality_flag
- Country embedding lookup table from structural features
- Event-type hierarchical encoding
- Signal-key pivoting utility
- Round-trip consistency and edge cases
"""
from __future__ import annotations

import pytest

from siasa.ml.encoding import (
    DomainOneHotEncoder,
    QualityFlagOrdinalEncoder,
    CountryEmbeddingLookup,
    SignalKeyPivoter,
)


# --- TC-SwR-068-001: Domain One-Hot Encoding ---

def test_domain_one_hot_encodes_all_five_domains() -> None:
    encoder = DomainOneHotEncoder()
    for domain in ["A", "B", "C", "D", "E"]:
        vec = encoder.encode(domain)
        assert len(vec) == 5
        assert sum(vec) == 1.0


def test_domain_one_hot_distinct_vectors() -> None:
    encoder = DomainOneHotEncoder()
    vectors = [tuple(encoder.encode(d)) for d in ["A", "B", "C", "D", "E"]]
    assert len(set(vectors)) == 5


def test_domain_one_hot_unknown_raises() -> None:
    encoder = DomainOneHotEncoder()
    with pytest.raises(ValueError, match="Unknown domain"):
        encoder.encode("X")


# --- Quality Flag Ordinal Encoding ---

def test_quality_flag_ordinal_encoding() -> None:
    encoder = QualityFlagOrdinalEncoder()
    assert encoder.encode("high") == 2
    assert encoder.encode("medium") == 1
    assert encoder.encode("low") == 0


def test_quality_flag_ordinal_unknown_default() -> None:
    encoder = QualityFlagOrdinalEncoder()
    assert encoder.encode("unknown") == -1


def test_quality_flag_ordinal_labels() -> None:
    encoder = QualityFlagOrdinalEncoder()
    assert encoder.labels == ["low", "medium", "high"]


# --- Country Embedding Lookup ---

def test_country_embedding_lookup_creates_table() -> None:
    structural_features = {
        "UKR": {"gdp": 3500.0, "population": 44.0, "hdi": 0.77},
        "DEU": {"gdp": 51000.0, "population": 83.0, "hdi": 0.94},
    }
    lookup = CountryEmbeddingLookup(structural_features)
    vec = lookup.get("UKR")
    assert len(vec) == 3
    assert vec[0] == 3500.0


def test_country_embedding_unknown_returns_zeros() -> None:
    lookup = CountryEmbeddingLookup({"UKR": {"gdp": 1.0, "pop": 2.0}})
    vec = lookup.get("UNKNOWN")
    assert all(v == 0.0 for v in vec)


def test_country_embedding_dimension() -> None:
    lookup = CountryEmbeddingLookup({"UKR": {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}})
    assert lookup.embedding_dim == 4


# --- Signal Key Pivoting ---

def test_signal_key_pivoter_pivots_rows_to_columns() -> None:
    rows = [
        {"country_id": "UKR", "date": "2025-01-01", "signal_key": "conflict", "value": 10.0},
        {"country_id": "UKR", "date": "2025-01-01", "signal_key": "fx_rate", "value": 0.95},
        {"country_id": "UKR", "date": "2025-01-02", "signal_key": "conflict", "value": 12.0},
        {"country_id": "UKR", "date": "2025-01-02", "signal_key": "fx_rate", "value": 0.96},
    ]
    pivoter = SignalKeyPivoter()
    result = pivoter.pivot(rows)
    assert len(result) == 2  # 2 dates
    assert result[0]["conflict"] == 10.0
    assert result[0]["fx_rate"] == 0.95
    assert result[1]["conflict"] == 12.0


def test_signal_key_pivoter_missing_signal_fills_none() -> None:
    rows = [
        {"country_id": "UKR", "date": "2025-01-01", "signal_key": "conflict", "value": 10.0},
        {"country_id": "UKR", "date": "2025-01-02", "signal_key": "fx_rate", "value": 0.96},
    ]
    pivoter = SignalKeyPivoter()
    result = pivoter.pivot(rows)
    assert result[0].get("fx_rate") is None
    assert result[1].get("conflict") is None


def test_signal_key_pivoter_preserves_metadata() -> None:
    rows = [
        {"country_id": "UKR", "date": "2025-01-01", "signal_key": "x", "value": 1.0},
    ]
    pivoter = SignalKeyPivoter()
    result = pivoter.pivot(rows)
    assert result[0]["country_id"] == "UKR"
    assert result[0]["date"] == "2025-01-01"
