from siasa.data.normalization_mappings import NormalizationMappingVersion, resolve_active_mapping
from siasa.data.normalization_service import normalize_records
from siasa.data.normalized_models import NormalizedRecord
from siasa.data.raw_models import RawRecord


def test_raw_record_supports_payload_storage() -> None:
    record = RawRecord(
        raw_record_id="RAW-001",
        source_id="SRC-A",
        fetched_at="2026-05-11T14:00:00Z",
        storage_mode="payload",
        raw_payload={"headline": "test"},
    )

    assert record.storage_mode == "payload"
    assert record.raw_payload == {"headline": "test"}


def test_raw_record_supports_reference_storage() -> None:
    record = RawRecord(
        raw_record_id="RAW-002",
        source_id="SRC-A",
        fetched_at="2026-05-11T14:00:00Z",
        storage_mode="reference",
        raw_reference="s3://bucket/object.json",
    )

    assert record.storage_mode == "reference"
    assert record.raw_reference == "s3://bucket/object.json"


def test_raw_record_rejects_missing_payload_for_payload_mode() -> None:
    try:
        RawRecord(
            raw_record_id="RAW-003",
            source_id="SRC-A",
            fetched_at="2026-05-11T14:00:00Z",
            storage_mode="payload",
        )
    except ValueError as exc:
        assert "raw_payload" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing payload")


def test_normalized_record_captures_provenance_and_quality_context() -> None:
    record = NormalizedRecord(
        normalized_id="NORM-001",
        country_id="UKR",
        timestamp="2026-05-11T14:00:00Z",
        domain="A",
        signal_key="news_volume",
        value=12.5,
        provenance_source_id="SRC-A",
        quality_context={"coverage": "high"},
    )

    assert record.country_id == "UKR"
    assert record.provenance_source_id == "SRC-A"
    assert record.quality_context["coverage"] == "high"


def test_normalization_mapping_version_resolves_active_mapping() -> None:
    mappings = [
        NormalizationMappingVersion(mapping_id="MAP-001", source_id="SRC-A", version="v1", is_active=False),
        NormalizationMappingVersion(mapping_id="MAP-002", source_id="SRC-A", version="v2", is_active=True),
    ]

    active = resolve_active_mapping(mappings, "SRC-A")

    assert active.mapping_id == "MAP-002"
    assert active.version == "v2"


def test_normalization_mapping_version_requires_active_mapping() -> None:
    mappings = [NormalizationMappingVersion(mapping_id="MAP-001", source_id="SRC-A", version="v1", is_active=False)]

    try:
        resolve_active_mapping(mappings, "SRC-A")
    except ValueError as exc:
        assert "active mapping" in str(exc)
    else:
        raise AssertionError("Expected ValueError when no active mapping exists")


def test_normalize_records_keeps_mapping_version_in_quality_context() -> None:
    mappings = [NormalizationMappingVersion(mapping_id="MAP-001", source_id="SRC-A", version="v3", is_active=True)]

    normalized = normalize_records(
        source_id="SRC-A",
        domain="B",
        raw_records=[
            {
                "country_id": "UKR",
                "timestamp": "2026-05-11T14:00:00Z",
                "signal_key": "conflict_event_count",
                "value": 4.0,
            }
        ],
        mappings=mappings,
    )

    assert normalized[0].quality_context["mapping_version"] == "v3"
    assert normalized[0].quality_context["mapping_id"] == "MAP-001"
