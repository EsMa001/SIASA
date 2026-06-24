"""Wikipedia Pageviews adapter — narrative attention signals for Domain A.

Source: https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/
Free, no auth, 100 req/s. Fetches daily pageview counts for configurable
country-topic Wikipedia articles as a proxy for public attention/salience.

Traceability: SwR-072, AP-14.1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from time import sleep
from typing import Any, Callable
from urllib.parse import quote
import json
from urllib.request import Request, urlopen


from .base import FetchResult, SourceAdapter


FetchJson = Callable[[str], object]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]


_BASE_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"


def _build_url(article: str, start: str, end: str, project: str = "en.wikipedia.org") -> str:
    """Build Wikimedia Pageviews API URL.

    Args:
        article: Wikipedia article title (e.g. 'Ukraine', 'South Sudan').
        start: Start date as YYYYMMDD.
        end: End date as YYYYMMDD.
        project: Wikimedia project (default: en.wikipedia.org).

    Returns:
        Full API URL.
    """
    encoded_article = quote(article.replace(" ", "_"), safe="")
    return (
        f"{_BASE_URL}/{project}/all-access/all-agents/"
        f"{encoded_article}/daily/{start}/{end}"
    )


def _default_fetch_json(url: str) -> object:
    req = Request(url, headers={"User-Agent": "SIASA/1.0 (conflict early-warning research)"})
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class WikipediaPageviewsAdapter(SourceAdapter):
    """Fetch daily Wikipedia pageview counts for country-topic articles.

    Each country is mapped to a Wikipedia article title. The adapter fetches
    daily pageview counts for a configurable lookback window and produces
    one record per day per country.
    """
    country_topics: dict[str, str]  # ISO-3 → article title, e.g. {"UKR": "Ukraine"}
    source_id: str = "SRC-WIKIPEDIA-PAGEVIEWS"
    domain: str = "A"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    lookback_days: int = 3
    freshness_hours: int = 48

    def fetch(self) -> FetchResult:
        """Fetch pageview data for all configured country-topics."""
        if not self.country_topics:
            return FetchResult(
                records=[],
                diagnostics="wikipedia_no_topics_configured",
                is_success=True,
            )

        now = self.now_provider()
        start_date = now - timedelta(days=self.lookback_days)
        start_str = start_date.strftime("%Y%m%d")
        end_str = now.strftime("%Y%m%d")

        all_records: list[dict[str, Any]] = []
        errors: list[str] = []

        for iso3 in sorted(self.country_topics):
            article = self.country_topics[iso3]
            try:
                url = _build_url(article, start_str, end_str)
                payload = self._fetch_with_retry(url)
                records = self._parse_payload(payload, iso3)
                all_records.extend(records)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{iso3}:{exc}")

        if errors and not all_records:
            return FetchResult(
                records=[],
                diagnostics=f"wikipedia_fetch_failed: {'; '.join(errors)}",
                is_success=False,
            )

        diagnostics = (
            f"wikipedia_fetch_ok countries={len(self.country_topics)} "
            f"records={len(all_records)}"
        )
        if errors:
            diagnostics += f" partial_errors={len(errors)}"

        return FetchResult(
            records=all_records,
            diagnostics=diagnostics,
            is_success=True,
        )

    def _parse_payload(
        self, payload: object, country_id: str
    ) -> list[dict[str, Any]]:
        """Parse Wikimedia pageviews response into SIASA records."""
        if not isinstance(payload, dict):
            return []

        items = payload.get("items")
        if not isinstance(items, list):
            return []

        records: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            views = item.get("views")
            timestamp = item.get("timestamp", "")
            if views is None or not timestamp:
                continue

            # Parse timestamp: YYYYMMDD00 → YYYY-MM-DD
            date_str = timestamp[:8]
            try:
                period = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                # Validate date
                datetime.strptime(period, "%Y-%m-%d")
            except (ValueError, IndexError):
                continue

            records.append({
                "country_id": country_id,
                "period": period,
                "signal_key": "wiki_pageview_count",
                "value": int(views),
                "quality_flag": "wikipedia_pageviews_api",
                "freshness_hours": self.freshness_hours,
                "freshness_horizon_hours": self.freshness_hours,
                "expected_source_count": 1,
            })

        return records

    def _fetch_with_retry(self, url: str) -> object:
        """Fetch URL with exponential backoff retry."""
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_json(url)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == self.max_retries:
                    break
                delay = min(
                    self.retry_backoff_seconds * (2 ** attempt),
                    self.max_retry_delay_seconds,
                )
                self.retry_sleep(delay)
        assert last_error is not None
        raise last_error
