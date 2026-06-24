"""SIASA ML Encoding Utilities (AP-13.12).

Implements:
- SwR-068: Encoding utilities for categorical SIASA features
  - DomainOneHotEncoder: One-hot for domain A-E
  - QualityFlagOrdinalEncoder: Ordinal for quality_flag
  - CountryEmbeddingLookup: Structural feature vectors per country
  - SignalKeyPivoter: Rows (country, date, signal_key, value) → columns
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional, Sequence


class DomainOneHotEncoder:
    """One-hot encoder for SIASA domains (A-E)."""

    DOMAINS = ["A", "B", "C", "D", "E"]

    def __init__(self) -> None:
        self._index = {d: i for i, d in enumerate(self.DOMAINS)}

    def encode(self, domain: str) -> list[float]:
        """Encode a domain string to a one-hot vector.

        Args:
            domain: One of A, B, C, D, E.

        Returns:
            List of 5 floats with exactly one 1.0.

        Raises:
            ValueError: If domain is not recognized.
        """
        if domain not in self._index:
            raise ValueError(f"Unknown domain: {domain!r}. Expected one of {self.DOMAINS}")
        vec = [0.0] * len(self.DOMAINS)
        vec[self._index[domain]] = 1.0
        return vec

    @property
    def dimension(self) -> int:
        return len(self.DOMAINS)


class QualityFlagOrdinalEncoder:
    """Ordinal encoder for quality_flag values."""

    _ORDINAL_MAP = {"low": 0, "medium": 1, "high": 2}

    def encode(self, flag: str) -> int:
        """Encode a quality flag to an ordinal integer.

        Args:
            flag: One of 'low', 'medium', 'high'.

        Returns:
            Ordinal integer (0, 1, 2) or -1 for unknown.
        """
        return self._ORDINAL_MAP.get(flag, -1)

    @property
    def labels(self) -> list[str]:
        """Return labels in ordinal order."""
        return sorted(self._ORDINAL_MAP.keys(), key=lambda k: self._ORDINAL_MAP[k])


class CountryEmbeddingLookup:
    """Lookup table mapping country IDs to structural feature vectors.

    Uses pre-computed structural features (GDP, population, HDI, etc.)
    as country representations for ML models.
    """

    def __init__(self, structural_features: dict[str, dict[str, float]]) -> None:
        """Initialize with structural features per country.

        Args:
            structural_features: Dict mapping country_id → {feature_name: value}.
                All countries must have the same feature keys.
        """
        self._features = structural_features
        if structural_features:
            first_key = next(iter(structural_features))
            self._feature_names = sorted(structural_features[first_key].keys())
            self._dim = len(self._feature_names)
        else:
            self._feature_names = []
            self._dim = 0

    def get(self, country_id: str) -> list[float]:
        """Get the embedding vector for a country.

        Args:
            country_id: ISO-3 country code.

        Returns:
            List of floats representing the country's structural features.
            Returns zeros for unknown countries.
        """
        if country_id in self._features:
            return [self._features[country_id].get(f, 0.0) for f in self._feature_names]
        return [0.0] * self._dim

    @property
    def embedding_dim(self) -> int:
        """Return the dimensionality of the embedding vector."""
        return self._dim

    @property
    def feature_names(self) -> list[str]:
        """Return the ordered feature names."""
        return list(self._feature_names)


class SignalKeyPivoter:
    """Pivot long-format signal rows into wide-format feature columns.

    Converts rows of (country_id, date, signal_key, value) into
    rows of (country_id, date, signal_a, signal_b, ...).
    """

    def pivot(
        self,
        rows: list[dict[str, Any]],
        group_keys: Optional[Sequence[str]] = None,
    ) -> list[dict[str, Any]]:
        """Pivot signal-key rows into columnar format.

        Args:
            rows: List of dicts with keys country_id, date, signal_key, value.
            group_keys: Keys to group by. Default: ["country_id", "date"].

        Returns:
            List of dicts with signal keys as columns. Missing signals are None.
        """
        if group_keys is None:
            group_keys = ["country_id", "date"]

        # Collect all signal keys
        all_signals: set[str] = set()
        for row in rows:
            all_signals.add(row["signal_key"])

        # Group rows
        groups: dict[tuple, dict[str, Any]] = {}
        for row in rows:
            group_key = tuple(row[k] for k in group_keys)
            if group_key not in groups:
                groups[group_key] = {k: row[k] for k in group_keys}
                for sig in all_signals:
                    groups[group_key][sig] = None
            groups[group_key][row["signal_key"]] = row["value"]

        # Sort by group key for deterministic output
        return [groups[k] for k in sorted(groups.keys())]
