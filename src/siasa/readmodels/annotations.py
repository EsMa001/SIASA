from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict

from siasa.annotations.models import AnnotationRecord


def build_annotations_view_model(annotations: list[AnnotationRecord]) -> dict[str, object]:
    by_scope: dict[str, list[str]] = defaultdict(list)
    by_linked_item: dict[str, list[str]] = defaultdict(list)
    serialized_annotations: list[dict[str, object]] = []

    for annotation in annotations:
        serialized_annotations.append(asdict(annotation))
        by_scope[annotation.scope].append(annotation.annotation_id)
        for linked_item in annotation.linked_items:
            by_linked_item[str(linked_item)].append(annotation.annotation_id)

    return {
        "annotations": serialized_annotations,
        "by_scope": dict(sorted(by_scope.items())),
        "by_linked_item": dict(sorted(by_linked_item.items())),
    }
