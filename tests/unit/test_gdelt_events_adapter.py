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


class SequenceBytesFetcher:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        assert isinstance(response, bytes)
        return response


def _empty_export_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("20230415000000.export.CSV", "")
    return buffer.getvalue()


def test_gdelt_events_adapter_selects_export_files_within_window() -> None:
    # AP-30.1 / SwR-096: a date window selects the dated export files from the masterfilelist.
    masterlist = "\n".join(
        [
            "100 hash http://data.gdeltproject.org/gdeltv2/20230415000000.export.CSV.zip",
            "100 hash http://data.gdeltproject.org/gdeltv2/20230420000000.export.CSV.zip",
            "100 hash http://data.gdeltproject.org/gdeltv2/20240101000000.export.CSV.zip",
        ]
    )
    text = StubTextFetcher(masterlist)
    by = SequenceBytesFetcher([_empty_export_zip(), _empty_export_zip()])
    adapter = GDELTEventsAdapter(
        country_codes={"UA": "UKR"},
        fetch_text=text,
        fetch_bytes=by,
        date_window=(datetime(2023, 4, 1, tzinfo=UTC), datetime(2023, 5, 1, tzinfo=UTC)),
    )
    adapter.fetch()
    assert text.urls[0].endswith("masterfilelist.txt")
    assert len(by.urls) == 2  # only the two in-window exports
    assert by.urls[0].endswith("20230415000000.export.CSV.zip")
    assert all("2024" not in url for url in by.urls)


def test_gdelt_events_adapter_live_path_uses_lastupdate() -> None:
    lastupdate = "100 hash http://data.gdeltproject.org/gdeltv2/20240101000000.export.CSV.zip"
    text = StubTextFetcher(lastupdate)
    by = SequenceBytesFetcher([_empty_export_zip()])
    GDELTEventsAdapter(country_codes={"UA": "UKR"}, fetch_text=text, fetch_bytes=by).fetch()
    assert text.urls[0].endswith("lastupdate.txt")


class FakeRateLimitError(RuntimeError):
    def __init__(self, message: str, *, retry_after: str | None = None) -> None:
        super().__init__(message)
        self.code = 429
        self.headers = {} if retry_after is None else {"Retry-After": retry_after}


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


def test_gdelt_events_adapter_aggregates_recent_export_window_for_multi_country_coverage() -> None:
    export_url = "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP", "POL": "PL", "TWN": "TW"},
        fetch_text=StubTextFetcher(f"100 abc {export_url}\n"),
        fetch_bytes=SequenceBytesFetcher(
            [
                _build_export_zip(
                    [
                        _event_row(event_root_code="19", quad_class="4", action_geo_country_code="UP", date_added="20260513110000"),
                    ]
                ),
                _build_export_zip(
                    [
                        _event_row(event_root_code="14", quad_class="3", action_geo_country_code="PL", date_added="20260513104500"),
                    ]
                ),
                _build_export_zip(
                    [
                        _event_row(event_root_code="11", quad_class="3", action_geo_country_code="TW", date_added="20260513103000"),
                    ]
                ),
            ]
        ),
        recent_export_count=3,
        now_provider=lambda: datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert result.diagnostics == "gdelt_events_fetch_ok countries=3 exports=3 records=4"
    assert result.records == [
        {
            "country_id": "POL",
            "timestamp": "2026-05-13T10:45:00Z",
            "signal_key": "protest_event_count",
            "value": 1.0,
            "expected_source_count": 1,
            "freshness_hours": 1,
            "quality_flag": "gdelt_events_export",
        },
        {
            "country_id": "TWN",
            "timestamp": "2026-05-13T10:30:00Z",
            "signal_key": "conflict_event_count",
            "value": 1.0,
            "expected_source_count": 1,
            "freshness_hours": 1,
            "quality_flag": "gdelt_events_export",
        },
        {
            "country_id": "UKR",
            "timestamp": "2026-05-13T11:00:00Z",
            "signal_key": "conflict_event_count",
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


def test_gdelt_events_adapter_derives_recent_export_urls_from_latest_export() -> None:
    adapter = GDELTEventsAdapter(country_codes={"UKR": "UP"}, recent_export_count=3, export_interval_minutes=15)

    assert adapter._recent_export_urls_from_latest(
        "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    ) == [
        "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip",
        "http://data.gdeltproject.org/gdeltv2/20260513124500.export.CSV.zip",
        "http://data.gdeltproject.org/gdeltv2/20260513123000.export.CSV.zip",
    ]


def test_gdelt_events_adapter_keeps_successful_recent_exports_when_an_older_window_fetch_fails() -> None:
    export_url = "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP", "POL": "PL"},
        fetch_text=StubTextFetcher(f"100 abc {export_url}\n"),
        fetch_bytes=SequenceBytesFetcher(
            [
                _build_export_zip(
                    [
                        _event_row(event_root_code="19", quad_class="4", action_geo_country_code="UP", date_added="20260513110000"),
                    ]
                ),
                RuntimeError("older window unavailable"),
            ]
        ),
        recent_export_count=2,
        max_retries=0,
        now_provider=lambda: datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert result.records == [
        {
            "country_id": "UKR",
            "timestamp": "2026-05-13T11:00:00Z",
            "signal_key": "conflict_event_count",
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
    assert "exports=1 records=2" in result.diagnostics
    assert "degraded_exports=1" in result.diagnostics
    assert "older window unavailable" in result.diagnostics


def test_gdelt_events_adapter_continues_past_a_missing_middle_export_window() -> None:
    export_url = "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP", "POL": "PL"},
        fetch_text=StubTextFetcher(f"100 abc {export_url}\n"),
        fetch_bytes=SequenceBytesFetcher(
            [
                _build_export_zip(
                    [
                        _event_row(event_root_code="19", quad_class="4", action_geo_country_code="UP", date_added="20260513110000"),
                    ]
                ),
                RuntimeError("middle window unavailable"),
                _build_export_zip(
                    [
                        _event_row(event_root_code="14", quad_class="3", action_geo_country_code="PL", date_added="20260513103000"),
                    ]
                ),
            ]
        ),
        recent_export_count=3,
        max_retries=0,
        now_provider=lambda: datetime(2026, 5, 13, 12, 0, tzinfo=UTC),
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert result.records == [
        {
            "country_id": "POL",
            "timestamp": "2026-05-13T10:30:00Z",
            "signal_key": "protest_event_count",
            "value": 1.0,
            "expected_source_count": 1,
            "freshness_hours": 1,
            "quality_flag": "gdelt_events_export",
        },
        {
            "country_id": "UKR",
            "timestamp": "2026-05-13T11:00:00Z",
            "signal_key": "conflict_event_count",
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
    assert "exports=2 records=3" in result.diagnostics
    assert "degraded_exports=1" in result.diagnostics
    assert "middle window unavailable" in result.diagnostics


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



def test_gdelt_events_adapter_honors_numeric_retry_after_for_rate_limit_backoff() -> None:
    export_url = "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    sleep_calls: list[float] = []
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
        fetch_text=StubTextFetcher(f"100 abc {export_url}\n"),
        fetch_bytes=SequenceBytesFetcher(
            [
                FakeRateLimitError("HTTP 429: Too Many Requests", retry_after="7"),
                _build_export_zip([]),
            ]
        ),
        retry_sleep=sleep_calls.append,
        max_retries=2,
        retry_backoff_seconds=1.0,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert sleep_calls == [7.0]



def test_gdelt_events_adapter_honors_http_date_retry_after_for_rate_limit_backoff() -> None:
    export_url = "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    sleep_calls: list[float] = []
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
        fetch_text=StubTextFetcher(f"100 abc {export_url}\n"),
        fetch_bytes=SequenceBytesFetcher(
            [
                FakeRateLimitError(
                    "HTTP 429: Too Many Requests",
                    retry_after="Wed, 13 May 2026 08:00:07 GMT",
                ),
                _build_export_zip([]),
            ]
        ),
        retry_sleep=sleep_calls.append,
        max_retries=2,
        retry_backoff_seconds=1.0,
        now_provider=lambda: datetime(2026, 5, 13, 8, 0, 0, tzinfo=UTC),
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert sleep_calls == [7.0]


def test_gdelt_events_adapter_caps_retry_after_backoff_to_max_retry_delay_seconds() -> None:
    export_url = "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    sleep_calls: list[float] = []
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
        fetch_text=StubTextFetcher(f"100 abc {export_url}\n"),
        fetch_bytes=SequenceBytesFetcher(
            [
                FakeRateLimitError("HTTP 429: Too Many Requests", retry_after="9999"),
                _build_export_zip([]),
            ]
        ),
        retry_sleep=sleep_calls.append,
        max_retries=1,
        max_retry_delay_seconds=12.0,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert sleep_calls == [12.0]


def test_gdelt_events_adapter_returns_failed_fetch_result_for_invalid_recent_export_window_configuration() -> None:
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
        fetch_text=StubTextFetcher("100 abc http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip\n"),
        recent_export_count=0,
    )

    result = adapter.fetch()

    assert result.records == []
    assert result.is_success is False
    assert "recent_export_count must be >= 1" in result.diagnostics
