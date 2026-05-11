from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_ALLOWED_SCOPES = {"country", "domain", "signal", "event", "snapshot"}
_ALLOWED_REVIEW_STATUS = {"unreviewed", "draft", "reviewed", "accepted", "rejected"}


@dataclass(frozen=True)
class AnnotationRecord:
    annotation_id: str
    created_at: str
    author: str
    scope: str
    annotation_type: str
    severity_assessment: str
    confidence_assessment: str
    text: str
    tags: list[str]
    linked_items: list[str]
    review_status: str

    def __post_init__(self) -> None:
        if self.scope not in _ALLOWED_SCOPES:
            raise ValueError("scope is not governed")
        if self.review_status not in _ALLOWED_REVIEW_STATUS:
            raise ValueError("review_status is not governed")
        if not self.annotation_id or not self.author:
            raise ValueError("annotation_id and author are required")


def attach_annotations_without_overwrite(
    generated_status: dict[str, Any],
    annotations: list[AnnotationRecord],
) -> dict[str, Any]:
    return {
        "generated_status": dict(generated_status),
        "annotations": list(annotations),
    }
