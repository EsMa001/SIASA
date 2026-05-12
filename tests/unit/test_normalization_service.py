from siasa.data.normalization_mappings import NormalizationMappingVersion
from siasa.data.normalization_service import normalize_records


def test_normalize_records_transforms_raw_source_rows_into_normalized_schema_with_mapping_context() -> None:
    mappings = [
        NormalizationMappingVersion(mapping_id="MAP-SRC-A-v2", source_id="SRC-A", version="v2", is_active=True),
    ]

    normalized = normalize_records(
        source_id="SRC-A",
        domain="A",
        raw_records=[
            {
                "country_id": "UKR",
                "timestamp": "2026-05-11T18:00:00Z",
                "signal_key": "article_count",
                "value": 3.0,
                "expected_source_count": 2,
                "freshness_hours": 6,
                "quality_flag": "verified",
            }
        ],
        mappings=mappings,
    )

    assert len(normalized) == 1
    assert normalized[0].normalized_id == "NORM-SRC-A-1"
    assert normalized[0].country_id == "UKR"
    assert normalized[0].timestamp == "2026-05-11T18:00:00Z"
    assert normalized[0].domain == "A"
    assert normalized[0].signal_key == "article_count"
    assert normalized[0].value == 3.0
    assert normalized[0].provenance_source_id == "SRC-A"
    assert normalized[0].quality_context == {
        "expected_source_count": 2,
        "freshness_hours": 6,
        "quality_flag": "verified",
        "mapping_id": "MAP-SRC-A-v2",
        "mapping_version": "v2",
    }


def test_normalize_records_requires_an_active_mapping_for_the_source() -> None:
    mappings = [
        NormalizationMappingVersion(mapping_id="MAP-SRC-A-v1", source_id="SRC-A", version="v1", is_active=False),
    ]

    try:
        normalize_records(
            source_id="SRC-A",
            domain="A",
            raw_records=[
                {
                    "country_id": "UKR",
                    "timestamp": "2026-05-11T18:00:00Z",
                    "signal_key": "article_count",
                    "value": 3.0,
                }
            ],
            mappings=mappings,
        )
    except ValueError as exc:
        assert "active mapping" in str(exc)
    else:
        raise AssertionError("Expected ValueError when no active mapping exists")
