from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from siasa.data.normalized_models import NormalizedRecord


FeatureHook = Callable[[list[NormalizedRecord]], list["FeatureValue"]]


@dataclass(frozen=True)
class FeatureValue:
    feature_id: str
    country_id: str
    domain: str
    value: Any
    provenance_source_ids: list[str]
    coverage: float
    confidence_inputs: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.coverage <= 1.0:
            raise ValueError("coverage must be between 0.0 and 1.0")
        if not self.feature_id:
            raise ValueError("feature_id is required")


class FeatureService(ABC):
    domain: str

    @abstractmethod
    def compute(self, records: list[NormalizedRecord]) -> list[FeatureValue]:
        """Compute feature values from normalized records."""


class FeatureServiceRegistry:
    def __init__(self) -> None:
        self._optional_hooks: dict[str, FeatureHook] = {}

    def register_optional_hook(self, domain: str, hook: FeatureHook) -> None:
        self._optional_hooks[domain] = hook

    def has_optional_hook(self, domain: str) -> bool:
        return domain in self._optional_hooks

    def execute_optional_hook(self, domain: str, records: list[NormalizedRecord]) -> list["FeatureValue"]:
        hook = self._optional_hooks.get(domain)
        if hook is None:
            return []
        return hook(records)


def build_feature_value(
    feature_id: str,
    domain: str,
    value: Any,
    records: list[NormalizedRecord],
    freshness_records: list[NormalizedRecord] | None = None,
) -> FeatureValue:
    if not records:
        raise ValueError("records are required to build a feature value")

    confidence_records = freshness_records or records

    provenance_source_ids = sorted({record.provenance_source_id for record in records})
    expected_source_count = max(
        int(record.quality_context.get("expected_source_count", 0) or 0) for record in records
    )
    if expected_source_count <= 0:
        expected_source_count = len(provenance_source_ids) or 1

    freshness_values = [record.quality_context.get("freshness_hours") for record in confidence_records]
    freshness_hours = max(
        float(value) for value in freshness_values if isinstance(value, int | float)
    ) if any(isinstance(value, int | float) for value in freshness_values) else None

    confidence_inputs = {
        "record_count": len(records),
        "source_count": len(provenance_source_ids),
    }
    if freshness_hours is not None:
        confidence_inputs["freshness_hours"] = int(freshness_hours) if freshness_hours.is_integer() else freshness_hours

    freshness_horizon_values = [record.quality_context.get("freshness_horizon_hours") for record in confidence_records]
    if any(isinstance(value, int | float) for value in freshness_horizon_values):
        freshness_horizon_hours = max(
            float(value) for value in freshness_horizon_values if isinstance(value, int | float)
        )
        confidence_inputs["freshness_horizon_hours"] = (
            int(freshness_horizon_hours)
            if freshness_horizon_hours.is_integer()
            else freshness_horizon_hours
        )

    return FeatureValue(
        feature_id=feature_id,
        country_id=records[0].country_id,
        domain=domain,
        value=value,
        provenance_source_ids=provenance_source_ids,
        coverage=min(1.0, len(provenance_source_ids) / expected_source_count),
        confidence_inputs=confidence_inputs,
    )


def mean_signal(records: list[NormalizedRecord], signal_key: str) -> float | None:
    values = [record.value for record in records if record.signal_key == signal_key]
    if not values:
        return None
    return sum(values) / len(values)


def sum_signal(records: list[NormalizedRecord], signal_key: str) -> float:
    return sum(record.value for record in records if record.signal_key == signal_key)


def topic_distribution(records: list[NormalizedRecord]) -> dict[str, float]:
    topic_values: dict[str, float] = {}
    total = 0.0
    for record in records:
        if not record.signal_key.startswith("topic:"):
            continue
        topic = record.signal_key.split(":", 1)[1]
        topic_values[topic] = topic_values.get(topic, 0.0) + record.value
        total += record.value

    if total == 0.0:
        return {}

    return {topic: value / total for topic, value in sorted(topic_values.items())}
