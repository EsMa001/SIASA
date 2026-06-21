"""AP-07 probe-driven robustness tests for GDELT adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.error import URLError

from siasa.adapters.gdelt_doc import GDELTDocAdapter
from siasa.adapters.gdelt_events import GDELTEventsAdapter
from siasa.adapters.retry_utils import _retry_delay_seconds, is_retryable_error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class SequenceFetcher:
    """Callable that yields successive responses or raises exceptions."""

    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.urls: list[str] = []

    def __call__(self, url: str) -> object:
        self.urls.append(url)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeHTTPError(RuntimeError):
    """Simulates an HTTP error with a status code and optional headers."""

    def __init__(self, message: str, code: int, *, retry_after: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.headers = {} if retry_after is None else {"Retry-After": retry_after}


class FakeRateLimitError(FakeHTTPError):
    def __init__(self, message: str = "HTTP 429", *, retry_after: str | None = None) -> None:
        super().__init__(message, 429, retry_after=retry_after)


class FakeServerError(FakeHTTPError):
    def __init__(self, message: str = "HTTP 503", code: int = 503, *, retry_after: str | None = None) -> None:
        super().__init__(message, code, retry_after=retry_after)


NOW = datetime(2026, 5, 13, 8, 0, tzinfo=UTC)


def _make_article(seendate: str = "20260513T060000Z", title: str = "Test") -> dict:
    return {
        "url": "https://example.test/a",
        "title": title,
        "seendate": seendate,
        "domain": "example.test",
        "language": "English",
        "sourcecountry": "United States",
    }


def _ok_payload(articles: list[dict] | None = None) -> dict:
    return {"articles": articles or [_make_article()]}


# ===========================================================================
# 1. is_retryable_error tests
# ===========================================================================

def test_is_retryable_error_http_429() -> None:
    assert is_retryable_error(FakeRateLimitError()) is True


def test_is_retryable_error_http_500() -> None:
    assert is_retryable_error(FakeServerError(code=500)) is True


def test_is_retryable_error_http_502() -> None:
    assert is_retryable_error(FakeServerError(code=502)) is True


def test_is_retryable_error_http_503() -> None:
    assert is_retryable_error(FakeServerError(code=503)) is True


def test_is_retryable_error_http_504() -> None:
    assert is_retryable_error(FakeServerError(code=504)) is True


def test_is_retryable_error_http_400_not_retryable() -> None:
    assert is_retryable_error(FakeHTTPError("Bad request", 400)) is False


def test_is_retryable_error_http_404_not_retryable() -> None:
    assert is_retryable_error(FakeHTTPError("Not found", 404)) is False


def test_is_retryable_error_timeout() -> None:
    assert is_retryable_error(TimeoutError("timed out")) is True


def test_is_retryable_error_connection_error() -> None:
    assert is_retryable_error(ConnectionError("refused")) is True


def test_is_retryable_error_url_error() -> None:
    assert is_retryable_error(URLError("network down")) is True


def test_is_retryable_error_generic_runtime_error_not_retryable() -> None:
    assert is_retryable_error(RuntimeError("unknown")) is False


def test_is_retryable_error_value_error_not_retryable() -> None:
    assert is_retryable_error(ValueError("bad data")) is False


# ===========================================================================
# 2. Shared retry delay calculation tests
# ===========================================================================

def test_retry_delay_returns_default_for_non_http_error() -> None:
    assert _retry_delay_seconds(RuntimeError("fail"), 2.0, NOW) == 2.0


def test_retry_delay_respects_retry_after_on_429() -> None:
    exc = FakeRateLimitError(retry_after="10")
    assert _retry_delay_seconds(exc, 1.0, NOW) == 10.0


def test_retry_delay_respects_retry_after_on_503() -> None:
    exc = FakeServerError(code=503, retry_after="15")
    assert _retry_delay_seconds(exc, 1.0, NOW) == 15.0


def test_retry_delay_uses_default_when_retry_after_smaller() -> None:
    exc = FakeRateLimitError(retry_after="0.5")
    assert _retry_delay_seconds(exc, 5.0, NOW) == 5.0


def test_retry_delay_parses_http_date_retry_after() -> None:
    exc = FakeRateLimitError(retry_after="Wed, 13 May 2026 08:00:07 GMT")
    delay = _retry_delay_seconds(exc, 1.0, NOW)
    assert delay == 7.0


def test_retry_delay_returns_default_for_unparseable_retry_after() -> None:
    exc = FakeRateLimitError(retry_after="not-a-number-or-date")
    assert _retry_delay_seconds(exc, 3.0, NOW) == 3.0


def test_retry_delay_returns_default_for_4xx_non_429() -> None:
    exc = FakeHTTPError("Not found", 404, retry_after="10")
    assert _retry_delay_seconds(exc, 2.0, NOW) == 2.0


# ===========================================================================
# 3. GDELTDocAdapter per-country fault isolation
# ===========================================================================

def test_doc_adapter_per_country_fault_isolation_partial_result() -> None:
    """If one country query fails, the adapter returns partial results for others."""
    fetcher = SequenceFetcher([
        RuntimeError("UKR failed"),  # UKR fails
        _ok_payload(),               # POL succeeds
    ])
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine", "POL": "poland"},
        fetch_json=fetcher,
        now_provider=lambda: NOW,
        retry_sleep=lambda _: None,
        max_retries=0,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 1
    assert result.records[0]["country_id"] == "POL"
    assert "degraded_countries=1" in result.diagnostics
    assert "UKR" in result.diagnostics


def test_doc_adapter_all_countries_fail_returns_failure() -> None:
    """If all countries fail, adapter returns is_success=False."""
    fetcher = SequenceFetcher([
        RuntimeError("UKR failed"),
        RuntimeError("POL failed"),
    ])
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine", "POL": "poland"},
        fetch_json=fetcher,
        now_provider=lambda: NOW,
        retry_sleep=lambda _: None,
        max_retries=0,
    )

    result = adapter.fetch()

    assert result.is_success is False
    assert result.records == []
    assert "all countries degraded" in result.diagnostics


def test_doc_adapter_no_degraded_countries_when_all_succeed() -> None:
    fetcher = SequenceFetcher([_ok_payload(), _ok_payload()])
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine", "POL": "poland"},
        fetch_json=fetcher,
        now_provider=lambda: NOW,
        retry_sleep=lambda _: None,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert "degraded_countries" not in result.diagnostics


# ===========================================================================
# 4. GDELTDocAdapter HTTP 5xx retry behavior
# ===========================================================================

def test_doc_adapter_retries_on_http_5xx() -> None:
    sleep_calls: list[float] = []
    fetcher = SequenceFetcher([
        FakeServerError("HTTP 503", code=503),
        _ok_payload(),
    ])
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine"},
        fetch_json=fetcher,
        now_provider=lambda: NOW,
        retry_sleep=sleep_calls.append,
        max_retries=2,
        retry_backoff_seconds=1.0,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(fetcher.urls) == 2
    assert len(sleep_calls) == 1


def test_doc_adapter_does_not_retry_on_http_404() -> None:
    """404 errors are retried (all exceptions are retried), but when all countries fail it's a failure."""
    sleep_calls: list[float] = []
    fetcher = SequenceFetcher([
        FakeHTTPError("Not found", 404),
        FakeHTTPError("Not found", 404),
        FakeHTTPError("Not found", 404),
        FakeHTTPError("Not found", 404),
    ])
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine"},
        fetch_json=fetcher,
        now_provider=lambda: NOW,
        retry_sleep=sleep_calls.append,
        max_retries=3,
    )

    result = adapter.fetch()

    assert result.is_success is False  # all countries degraded -> failure
    assert len(fetcher.urls) == 4  # 1 initial + 3 retries
    assert "all countries degraded" in result.diagnostics


# ===========================================================================
# 5. GDELTDocAdapter malformed article graceful skip
# ===========================================================================

def test_doc_adapter_skips_malformed_article_without_seendate() -> None:
    payload = {
        "articles": [
            _make_article(title="Good"),
            {"url": "https://example.test/bad", "title": "Missing seendate"},
            _make_article(title="Also good"),
        ]
    }
    fetcher = SequenceFetcher([payload])
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine"},
        fetch_json=fetcher,
        now_provider=lambda: NOW,
        retry_sleep=lambda _: None,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 2
    assert result.records[0]["title"] == "Good"
    assert result.records[1]["title"] == "Also good"


def test_doc_adapter_skips_article_that_is_not_a_dict() -> None:
    payload = {
        "articles": [
            _make_article(title="Good"),
            "not a dict",
            _make_article(title="Also good"),
        ]
    }
    fetcher = SequenceFetcher([payload])
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine"},
        fetch_json=fetcher,
        now_provider=lambda: NOW,
        retry_sleep=lambda _: None,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 2


def test_doc_adapter_skips_article_with_bad_seendate_format() -> None:
    payload = {
        "articles": [
            _make_article(title="Good"),
            {**_make_article(), "seendate": "not-a-date"},
            _make_article(title="Also good"),
        ]
    }
    fetcher = SequenceFetcher([payload])
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine"},
        fetch_json=fetcher,
        now_provider=lambda: NOW,
        retry_sleep=lambda _: None,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(result.records) == 2


# ===========================================================================
# 6. GDELTEventsAdapter HTTP 5xx retry behavior
# ===========================================================================

def test_events_adapter_retries_on_http_5xx() -> None:
    import io
    import zipfile

    def _build_export_zip(rows: list[list[str]]) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            csv_payload = "\n".join("\t".join(row) for row in rows)
            archive.writestr("20260513130000.export.CSV", csv_payload)
        return buffer.getvalue()

    export_url = "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    sleep_calls: list[float] = []

    class StubTextFetcher:
        def __call__(self, url: str) -> str:
            return f"100 abc {export_url}\n"

    fetcher_responses: list[object] = [
        FakeServerError("HTTP 502", code=502),
        _build_export_zip([]),
    ]

    class SequenceBytesFetcher:
        def __init__(self) -> None:
            self.urls: list[str] = []

        def __call__(self, url: str) -> bytes:
            self.urls.append(url)
            response = fetcher_responses.pop(0)
            if isinstance(response, Exception):
                raise response
            assert isinstance(response, bytes)
            return response

    bytes_fetcher = SequenceBytesFetcher()
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
        fetch_text=StubTextFetcher(),
        fetch_bytes=bytes_fetcher,
        retry_sleep=sleep_calls.append,
        now_provider=lambda: NOW,
        max_retries=2,
        retry_backoff_seconds=1.0,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(bytes_fetcher.urls) == 2
    assert len(sleep_calls) == 1


# ===========================================================================
# 7. GDELTEventsAdapter TimeoutError retry behavior
# ===========================================================================

def test_events_adapter_retries_on_timeout_error() -> None:
    import io
    import zipfile

    def _build_export_zip(rows: list[list[str]]) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            csv_payload = "\n".join("\t".join(row) for row in rows)
            archive.writestr("20260513130000.export.CSV", csv_payload)
        return buffer.getvalue()

    export_url = "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    sleep_calls: list[float] = []

    class StubTextFetcher:
        def __call__(self, url: str) -> str:
            return f"100 abc {export_url}\n"

    fetcher_responses: list[object] = [
        TimeoutError("request timed out"),
        _build_export_zip([]),
    ]

    class SequenceBytesFetcher:
        def __init__(self) -> None:
            self.urls: list[str] = []

        def __call__(self, url: str) -> bytes:
            self.urls.append(url)
            response = fetcher_responses.pop(0)
            if isinstance(response, Exception):
                raise response
            assert isinstance(response, bytes)
            return response

    bytes_fetcher = SequenceBytesFetcher()
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
        fetch_text=StubTextFetcher(),
        fetch_bytes=bytes_fetcher,
        retry_sleep=sleep_calls.append,
        now_provider=lambda: NOW,
        max_retries=2,
        retry_backoff_seconds=1.0,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert len(bytes_fetcher.urls) == 2
    assert len(sleep_calls) == 1


# ===========================================================================
# 8. GDELTEventsAdapter configurable timeout
# ===========================================================================

def test_events_adapter_has_configurable_request_timeout() -> None:
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
        request_timeout_seconds=90.0,
    )
    assert adapter.request_timeout_seconds == 90.0


def test_events_adapter_default_request_timeout_is_30() -> None:
    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
    )
    assert adapter.request_timeout_seconds == 30.0


# ===========================================================================
# 9. GDELTDocAdapter 5xx with Retry-After header
# ===========================================================================

def test_doc_adapter_respects_retry_after_on_5xx() -> None:
    sleep_calls: list[float] = []
    fetcher = SequenceFetcher([
        FakeServerError("HTTP 503", code=503, retry_after="12"),
        _ok_payload(),
    ])
    adapter = GDELTDocAdapter(
        country_queries={"UKR": "ukraine"},
        fetch_json=fetcher,
        now_provider=lambda: NOW,
        retry_sleep=sleep_calls.append,
        max_retries=2,
        retry_backoff_seconds=1.0,
    )

    result = adapter.fetch()

    assert result.is_success is True
    assert sleep_calls == [12.0]


# ===========================================================================
# 10. GDELTEventsAdapter does not retry non-retryable errors
# ===========================================================================

def test_events_adapter_retries_value_error_then_fails() -> None:
    import io
    import zipfile

    export_url = "http://data.gdeltproject.org/gdeltv2/20260513130000.export.CSV.zip"
    sleep_calls: list[float] = []

    class StubTextFetcher:
        def __call__(self, url: str) -> str:
            return f"100 abc {export_url}\n"

    call_count = 0

    class FailBytesFetcher:
        def __call__(self, url: str) -> bytes:
            nonlocal call_count
            call_count += 1
            raise ValueError("bad data")

    adapter = GDELTEventsAdapter(
        country_codes={"UKR": "UP"},
        fetch_text=StubTextFetcher(),
        fetch_bytes=FailBytesFetcher(),
        retry_sleep=sleep_calls.append,
        now_provider=lambda: NOW,
        max_retries=3,
    )

    result = adapter.fetch()

    assert result.is_success is False
    assert call_count == 4  # 1 initial + 3 retries (all exceptions are retried)
    assert len(sleep_calls) == 3
