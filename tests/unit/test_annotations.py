from siasa.annotations.models import AnnotationRecord, attach_annotations_without_overwrite


def test_annotation_model_persists_scope_type_author_text_tags_review_and_links() -> None:
    annotation = AnnotationRecord(
        annotation_id="ANN-2026-000123",
        created_at="2026-05-11T18:00:00Z",
        author="analyst",
        scope="country",
        annotation_type="context_note",
        severity_assessment="relevant",
        confidence_assessment="medium",
        text="News spike appears driven by replicated agency report.",
        tags=["source_dependency", "possible_false_positive"],
        linked_items=["SRC-GDELT", "EVENT-CLUSTER-456"],
        review_status="draft",
    )

    assert annotation.scope == "country"
    assert annotation.annotation_type == "context_note"
    assert annotation.tags == ["source_dependency", "possible_false_positive"]
    assert annotation.linked_items == ["SRC-GDELT", "EVENT-CLUSTER-456"]
    assert annotation.review_status == "draft"


def test_annotations_are_stored_alongside_generated_status_without_overwrite() -> None:
    annotation = AnnotationRecord(
        annotation_id="ANN-2026-000124",
        created_at="2026-05-11T18:05:00Z",
        author="analyst",
        scope="snapshot",
        annotation_type="review_note",
        severity_assessment="uncertain",
        confidence_assessment="low",
        text="Partial success likely affected event completeness.",
        tags=["partial_success"],
        linked_items=["SNAP-RUN-001-v1"],
        review_status="unreviewed",
    )

    enriched = attach_annotations_without_overwrite(
        generated_status={"country_id": "UKR", "multi_domain_status": "S3"},
        annotations=[annotation],
    )

    assert enriched["generated_status"]["multi_domain_status"] == "S3"
    assert enriched["annotations"][0].annotation_id == "ANN-2026-000124"
