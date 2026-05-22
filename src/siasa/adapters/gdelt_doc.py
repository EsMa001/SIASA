from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import json
from time import sleep
from typing import Any, Callable
from urllib.parse import quote_plus
from urllib.request import urlopen

from .base import FetchResult, SourceAdapter


FetchJson = Callable[[str], object]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]


def _default_fetch_json(url: str) -> object:
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def _utc_now() -> datetime:
    return datetime.now(UTC)



def _retry_delay_seconds(exc: Exception, default_delay: float, now: datetime) -> float:
    code = getattr(exc, 'code', None)
    if code == 429:
        headers = getattr(exc, 'headers', None)
        if headers is not None:
            retry_after = headers.get('Retry-After') if hasattr(headers, 'get') else None
            if retry_after is not None:
                try:
                    return max(default_delay, float(retry_after))
                except (TypeError, ValueError):
                    try:
                        retry_at = parsedate_to_datetime(str(retry_after))
                    except (TypeError, ValueError, IndexError, OverflowError):
                        return default_delay
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=UTC)
                    seconds_until_retry = max(0.0, (retry_at - now).total_seconds())
                    return max(default_delay, seconds_until_retry)
    return default_delay



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
    inter_request_delay_seconds: float = 0.0
    max_full_fetch_retries: int = 0
    full_fetch_retry_cooldown_seconds: float = 0.0
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep

    def fetch(self) -> FetchResult:
        try:
            for full_fetch_attempt in range(self.max_full_fetch_retries + 1):
                try:
                    records = self._fetch_country_batch()
                    diagnostics = (
                        f"gdelt_doc_fetch_ok countries={len(self.country_queries)} records={len(records)}"
                    )
                    return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
                except Exception as exc:
                    if full_fetch_attempt == self.max_full_fetch_retries or not _is_rate_limit_error(exc):
                        raise
                    self.retry_sleep(self.full_fetch_retry_cooldown_seconds)
        except Exception as exc:
            return FetchResult(records=[], diagnostics=f"gdelt_doc_fetch_failed: {exc}", is_success=False)

    def _fetch_country_batch(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        country_items = list(self.country_queries.items())
        for index, (country_id, query) in enumerate(country_items):
            url = self._build_url(query)
            payload = self._fetch_with_retry(url)
            records.extend(self._parse_payload(country_id, payload))
            if index < len(country_items) - 1 and self.inter_request_delay_seconds > 0:
                self.retry_sleep(self.inter_request_delay_seconds)
        return records

    def _build_url(self, query: str) -> str:
        encoded_query = quote_plus(query)
        return (
            f"{self.base_url}?query={encoded_query}&mode={self.mode}"
            f"&maxrecords={self.max_records}&format={self.output_format}"
        )

    def _fetch_with_retry(self, url: str) -> object:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_json(url)
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
        return records
