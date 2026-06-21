from __future__ import annotations

from pathlib import Path

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


def test_capability_matrix_steering_view_does_not_overclaim_replay_attention_follow_ons() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    matrix_markdown = (repo_root / "docs/plans/siasa-capability-fulfillment-matrix.md").read_text(encoding="utf-8")
    plan_markdown = (repo_root / "docs/plans/siasa-master-plan.md").read_text(encoding="utf-8")

    # The central master plan is the single steering source and names the validation epic.
    assert "AP-05" in plan_markdown
    assert "validation realism depth / analyst handoff refinement" in plan_markdown.lower()

    # The evidence companion still carries the concrete replay-attention evidence line ...
    assert "VAL-WP-012 replay-attention visible-slice CSV export" in matrix_markdown

    # ... without reintroducing stale "next interpretation extension" overclaims.
    stale_overclaims = [
        "P1 validation interpretation extension: replay-attention export naming metadata",
        "P1 validation interpretation extension: replay-attention copy-to-clipboard CSV",
        "P1 validation interpretation extension: replay-attention visible severity breakdown",
        "P1 validation interpretation extension: enriched replay-attention CSV export with handoff evidence fields",
        "P1 validation interpretation extension: replay-attention advanced triage presets for weak-evidence and mismatch slices",
    ]
    for claim in stale_overclaims:
        assert claim not in matrix_markdown


def test_central_plan_declares_default_next_track_and_avoids_stale_frontier() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    plan_markdown = (repo_root / "docs/plans/siasa-master-plan.md").read_text(encoding="utf-8")

    expected_track = "validation realism depth / analyst handoff refinement"
    assert expected_track in plan_markdown.lower()

    stale_frontier_phrases = [
        "next serial planning focus should now be chosen after AP-27 closure review",
        "next large package families (now G4/G2-trigger/G5",
    ]
    for phrase in stale_frontier_phrases:
        assert phrase not in plan_markdown
