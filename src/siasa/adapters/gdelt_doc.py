from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
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
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep

    def fetch(self) -> FetchResult:
        try:
            records: list[dict[str, Any]] = []
            for country_id, query in self.country_queries.items():
                url = self._build_url(query)
                payload = self._fetch_with_retry(url)
                records.extend(self._parse_payload(country_id, payload))
            diagnostics = (
                f"gdelt_doc_fetch_ok countries={len(self.country_queries)} records={len(records)}"
            )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except Exception as exc:
            return FetchResult(records=[], diagnostics=f"gdelt_doc_fetch_failed: {exc}", is_success=False)

    def _build_url(self, query: str) -> str:
        encoded_query = quote_plus(query)
        return (
            f"{self.base_url}?query={encoded_query}&mode={self.mode}"
            f"&maxrecords={self.max_records}&format={self.output_format}"
        )

    def _fetch_with_retry(self, url: str) -> object:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return self.fetch_json(url)
            except Exception as exc:  # noqa: BLE001 - adapter should return failed FetchResult, not crash caller
                last_error = exc
                if attempt == self.max_retries - 1:
                    break
                self.retry_sleep(self.retry_backoff_seconds * (2**attempt))
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
