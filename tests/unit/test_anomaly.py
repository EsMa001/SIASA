"""Unit tests for ALGO-ANOM-01 (AP-18): feature-driven domain anomaly.

Verifies SwR-048 (relative-baseline anomaly evaluation): the domain anomaly is
derived from the within-window signal series via the AP-17 z-score
(ALGO-ZSCORE-01), coverage-weighted across signals, and upper-bounded — never
from a fixed per-domain constant.
"""
from __future__ import annotations

from siasa.data.normalized_models import NormalizedRecord
from siasa.scoring.anomaly import compute_feature_driven_anomaly
from siasa.scoring.scoring_thresholds import anomaly_upper_bound

# Resolved via the governed getter (SwR-109) — the former module constant is gone.
ANOMALY_UPPER_BOUND = anomaly_upper_bound()


def _rec(
    signal_key: str,
    value: float,
    day: int,
    *,
    domain: str = "B",
    country: str = "AAA",
    source: str = "SRC-1",
    expected_sources: int = 1,
) -> NormalizedRecord:
    return NormalizedRecord(
        normalized_id=f"{domain}-{signal_key}-{day}",
        country_id=country,
        timestamp=f"2026-01-{day:02d}T00:00:00Z",
        domain=domain,
        signal_key=signal_key,
        value=float(value),
        provenance_source_id=source,
        quality_context={"expected_source_count": expected_sources},
    )


def _series(signal_key: str, values: list[float], **kwargs) -> list[NormalizedRecord]:
    return [_rec(signal_key, value, index + 1, **kwargs) for index, value in enumerate(values)]


def test_no_records_returns_zero():
    assert compute_feature_driven_anomaly("B", []) == 0.0


def test_series_below_minimum_history_has_no_anomaly():
    # Three observations are too few to trust a z-score; the signal contributes nothing.
    records = _series("sig", [10.0, 11.0, 12.0])
    assert compute_feature_driven_anomaly("B", records) == 0.0


def test_flat_series_is_not_anomalous():
    records = _series("sig", [10.0, 10.0, 10.0, 10.0, 10.0])
    assert compute_feature_driven_anomaly("B", records) == 0.0


def test_spike_produces_positive_bounded_anomaly():
    calm = _series("sig", [10.0, 10.0, 10.0, 10.0])
    spiked = _series("sig", [10.0, 10.0, 10.0, 25.0])
    assert compute_feature_driven_anomaly("B", calm) == 0.0
    spike_score = compute_feature_driven_anomaly("B", spiked)
    assert spike_score > 0.0
    assert spike_score <= ANOMALY_UPPER_BOUND


def test_larger_deviation_yields_larger_anomaly_in_unsaturated_band():
    # Pin the graded interior (not just 0.0-vs-cap): two distinct, non-zero,
    # non-saturated outputs must strictly order by deviation magnitude.
    baseline = [10.0, 8.0, 12.0, 9.0]
    moderate = compute_feature_driven_anomaly("B", _series("sig", [*baseline, 11.0]))
    stronger = compute_feature_driven_anomaly("B", _series("sig", [*baseline, 12.0]))
    assert 0.0 < moderate < stronger < ANOMALY_UPPER_BOUND


def test_extreme_deviation_is_capped():
    extreme = _series("sig", [10.0, 10.0, 10.0, 100000.0])
    assert compute_feature_driven_anomaly("B", extreme) == ANOMALY_UPPER_BOUND


def test_other_domain_records_are_ignored():
    b_records = _series("b_sig", [10.0, 10.0, 10.0, 25.0], domain="B")
    a_records = _series("a_sig", [1.0, 1.0, 1.0, 99.0], domain="A")
    combined = compute_feature_driven_anomaly("B", b_records + a_records)
    assert combined == compute_feature_driven_anomaly("B", b_records)


def test_coverage_weights_toward_better_covered_signal():
    # z-scores are scale-invariant, so the two signals must differ in SHAPE: one
    # ends on a clear outlier (high |z|), the other on an in-range value (low |z|).
    def score(anomalous_expected: int, calm_expected: int) -> float:
        anomalous = _series("anomalous", [10.0, 8.0, 12.0, 9.0, 22.0], source="S", expected_sources=anomalous_expected)
        calm = _series("calm", [10.0, 8.0, 12.0, 9.0, 11.0], source="S", expected_sources=calm_expected)
        return compute_feature_driven_anomaly("B", anomalous + calm)

    weight_on_anomaly = score(anomalous_expected=1, calm_expected=4)  # anomalous coverage 1.0, calm 0.25
    weight_on_calm = score(anomalous_expected=4, calm_expected=1)  # anomalous coverage 0.25, calm 1.0
    assert weight_on_anomaly > weight_on_calm


def test_is_deterministic_and_rounded():
    records = _series("sig", [10.0, 12.0, 11.0, 13.0, 20.0])
    first = compute_feature_driven_anomaly("B", records)
    second = compute_feature_driven_anomaly("B", records)
    assert first == second
    assert first == round(first, 4)
