from __future__ import annotations

from siasa.readmodels.functional_fulfillment import (
    estimate_functional_fulfillment_from_statuses,
    extract_capability_statuses_from_matrix_markdown,
)


def test_extract_capability_statuses_from_matrix_markdown_reads_only_capability_table() -> None:
    markdown = """
## 2. Current project-lead capability matrix
| Capability | Stakeholder focus | Current status | Notes |
| --- | --- | --- | --- |
| A | X | Done | n/a |
| B | X | Partial | n/a |
| C | X | Weak | n/a |

## 3. Current work-package steering view
| Work package | Purpose | Current state | Evidence |
| --- | --- | --- | --- |
| WP-1 | Y | Done | n/a |
"""
    assert extract_capability_statuses_from_matrix_markdown(markdown) == ["Done", "Partial", "Weak"]


def test_estimate_functional_fulfillment_from_statuses_uses_default_weights() -> None:
    estimate = estimate_functional_fulfillment_from_statuses(["Done", "Done", "Partial", "Weak"])
    assert estimate.capability_count == 4
    assert estimate.status_counts == {"Done": 2, "Partial": 1, "Weak": 1}
    assert estimate.weighted_percent == 72.5


def test_estimate_functional_fulfillment_rejects_unknown_status() -> None:
    try:
        estimate_functional_fulfillment_from_statuses(["Done", "Unknown"])
    except ValueError as exc:
        assert "Unsupported capability statuses" in str(exc)
    else:
        raise AssertionError("Expected unsupported status to raise ValueError")
