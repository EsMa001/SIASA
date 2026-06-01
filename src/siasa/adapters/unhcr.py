from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import sleep
from typing import Any, Callable
from urllib.request import Request, urlopen

from .base import FetchResult, SourceAdapter


FetchJSON = Callable[[str], Any]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]


def _default_fetch_json(url: str) -> Any:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _retry_delay_seconds(exc: Exception, default_delay: float, now: datetime) -> float:
    code = getattr(exc, "code", None)
    if code == 429:
        headers = getattr(exc, "headers", None)
        if headers is not None:
            retry_after = headers.get("Retry-After") if hasattr(headers, "get") else None
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


@dataclass
class UNHCRPopulationAdapter(SourceAdapter):
    """Adapter for the UNHCR Population Statistics API.

    Fetches refugee, IDP, asylum seeker, and stateless population data
    per country of origin from the UNHCR public API (no API key required).

    Signals produced per country:
    - refugee_population: total refugees originating from this country
    - asylum_seeker_population: total asylum seekers from this country
    - idp_population: internally displaced persons in this country
    - displacement_total: sum of refugees + asylum seekers + IDPs

    Domain: C (Physical Activity / Social Disruption) — complements GDACS
    disaster data with forced displacement indicators.

    API docs: https://api.unhcr.org/population/v1/
    No API key required. Rate-limited; adapter includes retry/backoff.
    """

    country_ids: set[str] | None = None
    source_id: str = "SRC-UNHCR-POP"
    domain: str = "C"
    api_base_url: str = "https://api.unhcr.org/population/v1/population/"
    year_range: int = 2
    page_size: int = 100
    max_pages: int = 50
    fetch_json: FetchJSON = _default_fetch_json
    now_provider: NowProvider = _utc_now
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    retry_sleep: SleepFn = sleep

    def fetch(self) -> FetchResult:
        try:
            now = self.now_provider()
            year_to = now.year
            year_from = max(year_to - self.year_range + 1, 1951)

            raw_items = self._fetch_all_items(year_from, year_to)
            records = self._aggregate_items(raw_items, now)
            country_count = len({r["country_id"] for r in records})
            diagnostics = (
                f"unhcr_fetch_ok countries={country_count} "
                f"raw_items={len(raw_items)} records={len(records)} "
                f"years={year_from}-{year_to}"
            )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except Exception as exc:
            return FetchResult(
                records=[], diagnostics=f"unhcr_fetch_failed: {exc}", is_success=False
            )

    def _fetch_json_with_retry(self, url: str) -> Any:
        if self.max_retries < 0:
            raise ValueError("UNHCR adapter max_retries must be >= 0")

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_json(url)
            except Exception as exc:  # noqa: BLE001
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

    def _fetch_all_items(self, year_from: int, year_to: int) -> list[dict[str, Any]]:
        """Paginate through UNHCR Population API for target countries."""
        all_items: list[dict[str, Any]] = []

        if self.country_ids:
            # Fetch per country to keep request sizes small
            for country_iso3 in sorted(self.country_ids):
                items = self._fetch_country_items(country_iso3, year_from, year_to)
                all_items.extend(items)
        else:
            # Fetch all countries
            items = self._fetch_country_items(None, year_from, year_to)
            all_items.extend(items)

        return all_items

    def _fetch_country_items(
        self, country_iso3: str | None, year_from: int, year_to: int
    ) -> list[dict[str, Any]]:
        """Fetch paginated items for a single country or all countries."""
        items: list[dict[str, Any]] = []

        for page in range(1, self.max_pages + 1):
            url = (
                f"{self.api_base_url}?limit={self.page_size}&page={page}"
                f"&year_from={year_from}&year_to={year_to}"
            )
            if country_iso3:
                url += f"&coo={country_iso3}"

            response = self._fetch_json_with_retry(url)
            page_items = response.get("items", [])
            if not page_items:
                break

            items.extend(page_items)

            max_pages = response.get("maxPages", 1)
            if page >= max_pages:
                break

        return items

    def _aggregate_items(
        self, items: list[dict[str, Any]], now: datetime
    ) -> list[dict[str, object]]:
        """Aggregate raw UNHCR items into per-country signal records.

        Uses the most recent year's data per country. Sums across all
        destination countries to get total displacement originating from
        each country of origin.
        """
        from collections import defaultdict

        # Group by (country_of_origin_iso3, year) and sum population figures
        country_year: dict[str, dict[int, dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )

        for item in items:
            coo_iso = item.get("coo_iso") or item.get("coo", "")
            if not coo_iso or coo_iso == "-":
                continue
            if self.country_ids is not None and coo_iso not in self.country_ids:
                continue

            year = item.get("year")
            if year is None:
                continue
            year = int(year)

            refugees = _safe_int(item.get("refugees", 0))
            asylum_seekers = _safe_int(item.get("asylum_seekers", 0))
            idps = _safe_int(item.get("idps", 0))

            country_year[coo_iso][year]["refugee_population"] += refugees
            country_year[coo_iso][year]["asylum_seeker_population"] += asylum_seekers
            country_year[coo_iso][year]["idp_population"] += idps

        # For each country, use the most recent year with data
        records: list[dict[str, object]] = []
        for country_id in sorted(country_year):
            years = sorted(country_year[country_id].keys(), reverse=True)
            if not years:
                continue
            latest_year = years[0]
            signals = country_year[country_id][latest_year]

            # Compute total displacement
            displacement_total = (
                signals.get("refugee_population", 0.0)
                + signals.get("asylum_seeker_population", 0.0)
                + signals.get("idp_population", 0.0)
            )
            signals["displacement_total"] = displacement_total

            # Timestamp = end of latest year; freshness = months since then
            data_date = datetime(latest_year, 12, 31, tzinfo=UTC)
            timestamp = data_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            freshness_hours = max(0, int((now - data_date).total_seconds() // 3600))

            for signal_key in (
                "refugee_population",
                "asylum_seeker_population",
                "idp_population",
                "displacement_total",
            ):
                value = signals.get(signal_key, 0.0)
                if value <= 0:
                    continue
                records.append(
                    {
                        "country_id": country_id,
                        "timestamp": timestamp,
                        "signal_key": signal_key,
                        "value": value,
                        "expected_source_count": 1,
                        "freshness_hours": freshness_hours,
                        "quality_flag": "unhcr_population",
                    }
                )
        return records


def _safe_int(value: Any) -> float:
    """Convert UNHCR API values to float, handling string/None/dash."""
    if value is None or value == "-" or value == "":
        return 0.0
    try:
        return float(int(value))
    except (TypeError, ValueError):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
