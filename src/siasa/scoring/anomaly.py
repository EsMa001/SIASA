"""ALGO-ANOM-01 (AP-18): feature-driven domain anomaly.

Closes finding F1 (anomaly_score was a fixed per-domain constant). Per SwR-048,
the domain anomaly is derived from data, not from a lookup table: for each
``signal_key`` in the domain's within-window record series the latest value is
z-scored against the window mean/std via :func:`compute_zscore`
(ALGO-ZSCORE-01, AP-17). The per-signal absolute z-scores are aggregated as a
coverage-weighted mean and capped at the governed ``anomaly.upper_bound``
threshold (resolved per call via :func:`anomaly_upper_bound`, SwR-109).

V1 limitation (recorded gap per AGENTS.md rule 7): the z-score uses the current
bundle's within-window series. A single-snapshot bundle has one observation per
signal, so the anomaly honestly reads ~0 there; the value only becomes strongly
informative once AP-26 supplies point-in-time daily windows and AP-30 backfills
real historical depth. On short windows the include-latest z-score saturates fast
(max |z| ~ sqrt(n-1)), so with the default constants the value reads near-binary
(0.0 or the cap); the graded D2/D3 band widens as windows grow. Thresholds/bounds
are project-owner authority.
"""
from __future__ import annotations

from siasa.data.normalized_models import NormalizedRecord
from siasa.features.multi_resolution import compute_zscore
from siasa.scoring.scoring_thresholds import anomaly_min_series_points, anomaly_upper_bound

# Owner-governed thresholds, sourced from vmodel/project/scoring_thresholds.yaml (AP-24).
# Resolved PER CALL (SwR-109): binding them to module constants at import time made
# override_thresholds — and with it every sensitivity sweep and test — silently
# ineffective for this family (audit finding A-02).


def _window_mean_std(values: list[float]) -> tuple[float, float]:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return mean, variance ** 0.5


def _signal_coverage(signal_records: list[NormalizedRecord]) -> float:
    """Provenance-source coverage for one signal, mirroring ``build_feature_value``."""
    sources = {record.provenance_source_id for record in signal_records if record.provenance_source_id}
    expected = max(
        (int(record.quality_context.get("expected_source_count", 0) or 0) for record in signal_records),
        default=0,
    )
    if expected <= 0:
        expected = len(sources) or 1
    return min(1.0, len(sources) / expected)


def compute_feature_driven_anomaly(domain: str, records: list[NormalizedRecord]) -> float:
    """Return the coverage-weighted, upper-bounded anomaly for ``domain``.

    The value is deterministic and rounded; it depends only on the supplied
    records, so two identical inputs yield bit-identical results.
    """
    upper_bound = anomaly_upper_bound()
    min_series_points = anomaly_min_series_points()

    domain_records = [record for record in records if record.domain == domain]
    if not domain_records:
        return 0.0

    by_signal: dict[str, list[NormalizedRecord]] = {}
    for record in domain_records:
        by_signal.setdefault(record.signal_key, []).append(record)

    weighted_sum = 0.0
    weight_total = 0.0
    for signal_key in sorted(by_signal):
        signal_records = sorted(by_signal[signal_key], key=lambda record: (str(record.timestamp), record.normalized_id))
        values = [float(record.value) for record in signal_records]
        if len(values) < min_series_points:
            continue
        mean, std = _window_mean_std(values)
        zscore = compute_zscore(values[-1], mean, std)
        if zscore is None:
            continue
        coverage = _signal_coverage(signal_records)
        if coverage <= 0:
            continue
        weighted_sum += abs(zscore) * coverage
        weight_total += coverage

    if weight_total <= 0:
        return 0.0
    return round(min(weighted_sum / weight_total, upper_bound), 4)
