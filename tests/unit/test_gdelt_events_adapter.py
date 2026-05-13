from __future__ import annotations

from datetime import UTC, datetime
import io
import zipfile

from siasa.adapters.base import FetchResult
from siasa.adapters.gdelt_events import GDELTEventsAdapter
from siasa.data.normalization_mappings import NormalizationMappingVersion
from siasa.data.normalization_service import normalize_records
from siasa.features.domain_b import DomainBFeatureService


class StubTextFetcher:
    def __init__(self, text: str, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.urls: list[str] = []

    def __call__(self, url: str) -> str:
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        return self.text


class StubBytesFetcher:
    def __init__(self, payload: bytes, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        return self.payload


def _build_export_zip(rows: list[list[str]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        csv_payload = "\n".join("\t".join(row) for row in rows)
        archive.writestr("20260513130000.export.CSV", csv_payload)
    return buffer.getvalue()


def _event_row(*, event_root_code: str, quad_class: str, action_geo_country_code: str, date_added: str) -> list[str]:
    row = [""] * 61
    row[0] = "1300000000"
    row[1] = "20260513"
    row[28] = event_root_code
    row[29] = quad_class
    row[53] = action_geo_country_code
    row[59] = date_added
    row[60] = "https://example.test/article"
    return row


def test_gdelt_events_adapter_fetch_aggregates_country_level_domain_b_signals() -> None:
    export_url = "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
        fetch_text=StubTextFetcher(f"100 abc {export_url}\n"),
        fetch_bytes=StubBytesFetcher(
            _build_export_zip(
                [
                    _event_row(event_root_code="14", quad_class="3", action_geo_country_code="UP", date_added="20260513110000"),
                    _event_row(event_root_code="19", quad_class="4", action_geo_country_code="UP", date_added="20260513100000"),
                    _event_row(event_root_code="19", quad_class="3", action_geo_country_code="UP", date_added="20260513090000"),
                    _event_row(event_root_code="14", quad_class="3", action_geo_country_code="PL", date_added="20260513080000"),
                ]
            )
        ),
        now_provider=lambda: datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
    )

    result = adapter.fetch()

    assert isinstance(result, FetchResult)
    assert result.is_success is True
    assert result.records == [
        {
            "country_id": "UKR",
            "timestamp": "2026-05-13T11:00:00Z",
            "signal_key": "conflict_event_count",
            "value": 2.0,
            "expected_source_count": 1,
            "freshness_hours": 1,
            "quality_flag": "gdelt_events_export",
        },
        {
            "country_id": "UKR",
            "timestamp": "2026-05-13T11:00:00Z",
            "signal_key": "protest_event_count",
            "value": 1.0,
            "expected_source_count": 1,
            "freshness_hours": 1,
            "quality_flag": "gdelt_events_export",
        },
        {
            "country_id": "UKR",
            "timestamp": "2026-05-13T11:00:00Z",
            "signal_key": "violent_event_count",
            "value": 1.0,
            "expected_source_count": 1,
            "freshness_hours": 1,
            "quality_flag": "gdelt_events_export",
        },
    ]


def test_gdelt_events_adapter_supports_domain_b_feature_computation() -> None:
    export_url = "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
        fetch_text=StubTextFetcher(f"100 abc {export_url}\n"),
        fetch_bytes=StubBytesFetcher(
            _build_export_zip(
                [
                    _event_row(event_root_code="14", quad_class="3", action_geo_country_code="UP", date_added="20260513110000"),
                    _event_row(event_root_code="19", quad_class="4", action_geo_country_code="UP", date_added="20260513100000"),
                    _event_row(event_root_code="19", quad_class="3", action_geo_country_code="UP", date_added="20260513090000"),
                ]
            )
        ),
        now_provider=lambda: datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
    )

    result = adapter.fetch()
    normalized = normalize_records(
        source_id=adapter.source_id,
        domain=adapter.domain,
        raw_records=result.records,
        mappings=[
            NormalizationMappingVersion(
                mapping_id="MAP-GDELT-EVENTS-v1",
                source_id=adapter.source_id,
                version="v1",
                is_active=True,
            )
        ],
    )
    features = {feature.feature_id: feature for feature in DomainBFeatureService().compute(normalized)}

    assert features["B_event_count"].value == 4.0
    assert features["B_violent_event_count"].value == 1.0
    assert features["B_protest_event_count"].value == 1.0
    assert features["B_violent_event_share"].value == 0.25


def test_gdelt_events_adapter_returns_failed_fetch_result_when_export_discovery_fails() -> None:
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
        fetch_text=StubTextFetcher("", error=RuntimeError("lastupdate unavailable")),
        fetch_bytes=StubBytesFetcher(b""),
    )

    result = adapter.fetch()

    assert result.records == []
    assert result.is_success is False
    assert "lastupdate unavailable" in result.diagnostics
