from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from time import sleep
from typing import Any, Callable
from urllib.parse import quote_plus
from urllib.request import urlopen

from .base import FetchResult, SourceAdapter
from .retry_utils import _retry_delay_seconds, is_retryable_error


FetchJson = Callable[[str], object]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]


def _default_fetch_json(url: str, timeout_seconds: float) -> object:
    with urlopen(url, timeout=timeout_seconds) as response:
        return json.load(response)


def _utc_now() -> datetime:
    return datetime.now(UTC)



def _is_rate_limit_error(exc: Exception) -> bool:
    return getattr(exc, 'code', None) == 429


@dataclass
class GDELTDocAdapter(SourceAdapter):
    country_queries: dict[str, str]
    source_id: str = "SRC-GDELT-DOC"
    domain: str = "A"
    base_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    mode: str = "ArtList"
    max_records: int = 50
    output_format: str = "json"
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    request_timeout_seconds: float = 30.0
    inter_request_delay_seconds: float = 0.0
    max_full_fetch_retries: int = 0
    full_fetch_retry_cooldown_seconds: float = 0.0
    fetch_json: FetchJson | None = None
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    # AP-30.1 (SwR-095): optional historical window; None -> live path unchanged.
    date_window: tuple[datetime, datetime] | None = None

    def fetch(self) -> FetchResult:
        try:
            for full_fetch_attempt in range(self.max_full_fetch_retries + 1):
                try:
                    records, degraded_countries = self._fetch_country_batch()
                    # If ALL countries degraded and no records, treat as failure
                    if degraded_countries and len(degraded_countries) == len(self.country_queries) and not records:
                        raise RuntimeError(
                            f"all countries degraded: {' | '.join(degraded_countries)}"
                        )
                    diagnostics = (
                        f"gdelt_doc_fetch_ok countries={len(self.country_queries)} records={len(records)}"
                    )
                    if degraded_countries:
                        diagnostics = (
                            f"{diagnostics} degraded_countries={len(degraded_countries)}"
                            f" degraded_reasons={' | '.join(degraded_countries)}"
                        )
                    return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
                except Exception as exc:
                    if full_fetch_attempt == self.max_full_fetch_retries or not _is_rate_limit_error(exc):
                        raise
                    self.retry_sleep(self.full_fetch_retry_cooldown_seconds)
        except Exception as exc:
            return FetchResult(records=[], diagnostics=f"gdelt_doc_fetch_failed: {exc}", is_success=False)

    def _fetch_country_batch(self) -> tuple[list[dict[str, Any]], list[str]]:
        records: list[dict[str, Any]] = []
        degraded_countries: list[str] = []
        country_items = list(self.country_queries.items())
        for index, (country_id, query) in enumerate(country_items):
            try:
                url = self._build_url(query)
                payload = self._fetch_with_retry(url)
                records.extend(self._parse_payload(country_id, payload))
            except Exception as exc:  # noqa: BLE001 - per-country fault isolation
                if _is_rate_limit_error(exc):
                    raise  # rate limit errors bubble up for full-batch retry
                degraded_countries.append(f"{country_id}: {exc}")
                continue
            if index < len(country_items) - 1 and self.inter_request_delay_seconds > 0:
                self.retry_sleep(self.inter_request_delay_seconds)
        return records, degraded_countries

    def _build_url(self, query: str) -> str:
        encoded_query = quote_plus(query)
        url = (
            f"{self.base_url}?query={encoded_query}&mode={self.mode}"
            f"&maxrecords={self.max_records}&format={self.output_format}"
        )
        if self.date_window is not None:
            start, end = self.date_window
            url += (
                f"&startdatetime={start.strftime('%Y%m%d%H%M%S')}"
                f"&enddatetime={end.strftime('%Y%m%d%H%M%S')}"
            )
        return url

    def _fetch_json_with_runtime_timeout(self, url: str) -> object:
        if self.fetch_json is not None:
            return self.fetch_json(url)
        return _default_fetch_json(url, self.request_timeout_seconds)

    def _fetch_with_retry(self, url: str) -> object:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._fetch_json_with_runtime_timeout(url)
            except Exception as exc:  # noqa: BLE001 - adapter should return failed FetchResult, not crash caller
                last_error = exc
                if attempt == self.max_retries:
                    break
                retry_delay = _retry_delay_seconds(
                    exc,
                    self.retry_backoff_seconds * (2**attempt),
                    self.now_provider(),
                )
                retry_delay = min(retry_delay, self.max_retry_delay_seconds)
                self.retry_sleep(retry_delay)
        assert last_error is not None
        raise last_error

    def _parse_payload(self, country_id: str, payload: object) -> list[dict[str, Any]]:
        if not isinstance(payload, dict) or not isinstance(payload.get("articles"), list):
            raise ValueError("GDELT DOC payload must contain an 'articles' list")

        now = self.now_provider()
        records: list[dict[str, Any]] = []
        for article in payload["articles"]:
            try:
                if not isinstance(article, dict):
                    raise ValueError("GDELT DOC article entries must be objects")
                seendate = str(article.get("seendate") or "").strip()
                if not seendate:
                    raise ValueError("GDELT DOC articles require seendate")
                seen_at = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
                freshness_hours = max(0, int((now - seen_at).total_seconds() // 3600))
                records.append(
                    {
                        "country_id": country_id,
                        "timestamp": seen_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "signal_key": "article_count",
                        "value": 1.0,
                        "expected_source_count": 1,
                        "freshness_hours": freshness_hours,
                        "quality_flag": "gdelt_doc_api",
                        "url": str(article.get("url") or ""),
                        "title": str(article.get("title") or ""),
                        "domain": str(article.get("domain") or ""),
                        "language": str(article.get("language") or ""),
                        "sourcecountry": str(article.get("sourcecountry") or ""),
                    }
                )
            except Exception:  # noqa: BLE001 - skip malformed articles gracefully
                continue
        return records
