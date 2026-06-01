from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import sleep
from typing import Any, Callable
from urllib.request import Request, urlopen

from .base import FetchResult, SourceAdapter


FetchJSON = Callable[[str, dict[str, str]], Any]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]


def _default_fetch_json(url: str, headers: dict[str, str]) -> Any:
    req = Request(url, headers=headers)
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


# ISO-3166-1 alpha-3 to UCDP numeric country IDs for pilot set.
# UCDP uses numeric codes internally; this mapping enables country_id filtering.
# Extend as needed for broader pilot sets.
_ISO3_TO_UCDP_COUNTRY_ID: dict[str, int] = {
    "UKR": 369,
    "RUS": 365,
    "ISR": 666,
    "TUR": 352,
    "IND": 750,
    "PAK": 770,
    "GEO": 372,
    "IRN": 630,
    "CHN": 710,
    "TWN": 713,
    "POL": 290,
    "MMR": 775,
    "NGA": 475,
    "SDN": 625,
    "EGY": 651,
    "USA": 2,
    "DEU": 255,
    "EST": 366,
    "FIN": 375,
    "SAU": 670,
    "QAT": 694,
}


@dataclass
class UCDPAdapter(SourceAdapter):
    """Adapter for the UCDP Georeferenced Event Dataset (GED) API.

    Fetches recent armed conflict events per country from the UCDP GED API.
    Requires an API token (free academic registration at https://ucdp.uu.se/).

    Signals produced per country:
    - armed_conflict_events: count of events
    - battle_deaths_best: sum of best-estimate fatalities
    - state_based_events: count of events involving state actors (type_of_violence=1)

    Domain: B (Security/Conflict) — complements GDELT Events with curated conflict data.
    """

    country_ids: set[str] | None = None
    source_id: str = "SRC-UCDP-GED"
    domain: str = "B"
    api_base_url: str = "https://ucdpapi.pcr.uu.se/api/gedevents/24.1"
    api_token: str = ""
    api_token_env_var: str = "UCDP_API_TOKEN"
    page_size: int = 100
    max_pages: int = 10
    fetch_json: FetchJSON = _default_fetch_json
    now_provider: NowProvider = _utc_now
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    retry_sleep: SleepFn = sleep

    def _resolve_token(self) -> str:
        """Resolve API token from explicit value or environment variable."""
        if self.api_token:
            return self.api_token
        env_token = os.environ.get(self.api_token_env_var, "").strip()
        return env_token

    def fetch(self) -> FetchResult:
        token = self._resolve_token()
        if not token:
            return FetchResult(
                records=[],
                diagnostics=(
                    f"ucdp_no_api_token: set {self.api_token_env_var} environment "
                    "variable or provide api_token parameter. "
                    "Register free at https://ucdp.uu.se/"
                ),
                is_success=False,
            )
        try:
            events = self._fetch_all_events(token)
            records = self._aggregate_events(events)
            diagnostics = (
                f"ucdp_fetch_ok countries={len({r['country_id'] for r in records})} "
                f"raw_events={len(events)} records={len(records)}"
            )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except Exception as exc:
            return FetchResult(
                records=[], diagnostics=f"ucdp_fetch_failed: {exc}", is_success=False
            )

    def _fetch_json_with_retry(self, url: str, headers: dict[str, str]) -> Any:
        if self.max_retries < 0:
            raise ValueError("UCDP adapter max_retries must be >= 0")

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_json(url, headers)
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

    def _fetch_all_events(self, token: str) -> list[dict[str, Any]]:
        """Paginate through UCDP GED API, collecting events for target countries."""
        headers = {"x-ucdp-access-token": token}
        all_events: list[dict[str, Any]] = []

        for page in range(self.max_pages):
            url = f"{self.api_base_url}?pagesize={self.page_size}&page={page}"
            response = self._fetch_json_with_retry(url, headers)

            # UCDP API returns {"TotalCount": N, "TotalPages": P, "Result": [...]}
            results = response.get("Result", [])
            if not results:
                break

            for event in results:
                country_iso3 = self._resolve_country_from_event(event)
                if country_iso3 is None:
                    continue
                if self.country_ids is not None and country_iso3 not in self.country_ids:
                    continue
                event["_resolved_iso3"] = country_iso3
                all_events.append(event)

            total_pages = response.get("TotalPages", 0)
            if page + 1 >= total_pages:
                break

        return all_events

    def _resolve_country_from_event(self, event: dict[str, Any]) -> str | None:
        """Extract ISO-3 country code from a UCDP event.

        UCDP events contain 'country_id' (numeric) and 'country' (name).
        We reverse-map from numeric ID to ISO-3.
        """
        ucdp_country_id = event.get("country_id")
        if ucdp_country_id is None:
            return None
        ucdp_id = int(ucdp_country_id)
        for iso3, numeric_id in _ISO3_TO_UCDP_COUNTRY_ID.items():
            if numeric_id == ucdp_id:
                return iso3
        return None

    def _aggregate_events(self, events: list[dict[str, Any]]) -> list[dict[str, object]]:
        """Aggregate raw events into per-country signal records."""
        from collections import defaultdict

        aggregated: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        latest_date: dict[str, datetime] = {}

        for event in events:
            country_id = event["_resolved_iso3"]

            # Count events
            aggregated[country_id]["armed_conflict_events"] += 1.0

            # Accumulate fatalities (best estimate)
            best_deaths = event.get("best", 0) or 0
            aggregated[country_id]["battle_deaths_best"] += float(best_deaths)

            # State-based violence (type_of_violence == 1)
            type_of_violence = event.get("type_of_violence", 0)
            if type_of_violence == 1:
                aggregated[country_id]["state_based_events"] += 1.0

            # Track latest date
            date_start = event.get("date_start", "")
            if date_start:
                try:
                    event_date = datetime.strptime(str(date_start)[:10], "%Y-%m-%d").replace(
                        tzinfo=UTC
                    )
                    prev = latest_date.get(country_id)
                    if prev is None or event_date > prev:
                        latest_date[country_id] = event_date
                except (ValueError, TypeError):
                    pass

        now = self.now_provider()
        records: list[dict[str, object]] = []
        for country_id in sorted(aggregated):
            ts = latest_date.get(country_id, now)
            timestamp = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
            freshness_hours = max(0, int((now - ts).total_seconds() // 3600))

            for signal_key in ("armed_conflict_events", "battle_deaths_best", "state_based_events"):
                value = aggregated[country_id].get(signal_key, 0.0)
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
                        "quality_flag": "ucdp_ged",
                    }
                )
        return records
