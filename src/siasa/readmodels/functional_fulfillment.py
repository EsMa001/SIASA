from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

_ALLOWED_STATUSES = {"Done", "Partial", "Weak", "Missing", "Deferred by intent"}
_DEFAULT_WEIGHTS = {
    "Done": 1.0,
    "Partial": 0.6,
    "Weak": 0.3,
    "Missing": 0.0,
    "Deferred by intent": 0.2,
}


@dataclass(frozen=True)
class FunctionalFulfillmentEstimate:
    capability_count: int
    status_counts: dict[str, int]
    weighted_percent: float


def estimate_functional_fulfillment_from_statuses(
    statuses: list[str],
    *,
    weights: dict[str, float] | None = None,
) -> FunctionalFulfillmentEstimate:
    if not statuses:
        raise ValueError("At least one capability status is required")
    invalid = sorted({status for status in statuses if status not in _ALLOWED_STATUSES})
    if invalid:
        raise ValueError(f"Unsupported capability statuses: {', '.join(invalid)}")

    effective_weights = dict(_DEFAULT_WEIGHTS)
    if weights is not None:
        effective_weights.update(weights)

    weighted_sum = sum(effective_weights[status] for status in statuses)
    percent = round((weighted_sum / len(statuses)) * 100.0, 1)
    return FunctionalFulfillmentEstimate(
        capability_count=len(statuses),
        status_counts=dict(Counter(statuses)),
        weighted_percent=percent,
    )


def extract_capability_statuses_from_matrix_markdown(markdown_text: str) -> list[str]:
    statuses: list[str] = []
    in_capability_table = False

    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## 2. Current project-lead capability matrix"):
            in_capability_table = True
            continue
        if in_capability_table and stripped.startswith("## 3. Current work-package steering view"):
            break
        if not in_capability_table:
            continue
        if not stripped.startswith("|"):
            continue
        if "Capability | Stakeholder focus | Current status" in stripped:
            continue
        if stripped.startswith("| ---"):
            continue

        columns = [column.strip() for column in stripped.strip("|").split("|")]
        if len(columns) < 3:
            continue
        current_status = columns[2]
        if current_status in _ALLOWED_STATUSES:
            statuses.append(current_status)

    return statuses
