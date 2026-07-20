from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from time import sleep
from typing import Any, Callable
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .base import FetchResult, SourceAdapter


FetchJSON = Callable[[str, dict[str, str]], Any]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]

# UCDP GED API hard limit for the pagesize parameter.
_MAX_PAGE_SIZE = 1000

# Annual GED releases follow the YY.1 convention: release YY.1 covers
# 1989-01-01 through 31 Dec of year YY-1 and is published in the following
# spring. The publication lag therefore reaches roughly 16 months. A default
# window shorter than that lag would query a period the annual dataset cannot
# cover yet and return zero events without anything being wrong. 540 days
# (~18 months) clears the maximum lag with margin.
_DEFAULT_LOOKBACK_DAYS = 540

# HTTP statuses that indicate an authentication problem. Retrying these cannot
# succeed and is actively harmful: the UCDP quota counts errors against the
# 5,000 requests/day limit.
_TERMINAL_HTTP_STATUSES = frozenset({401, 403})


class UCDPContractError(RuntimeError):
    """The API response violated an assumption the adapter depends on."""


class UCDPFilterNotAppliedError(UCDPContractError):
    """Raised when the UCDP API returned events outside the requested countries.

    The UCDP API documents that an unknown filter parameter is *silently
    ignored* rather than rejected, which degrades a targeted query into a full
    global fetch that still answers HTTP 200. Detecting foreign countries in
    the response is the only way to notice that the filter did not apply.
    """


class UCDPUnexpectedHostError(UCDPContractError):
    """Raised when a pagination link would send the API token off-host."""


class UCDPNoResolvableCountriesError(UCDPContractError):
    """Raised when no configured country maps to a Gleditsch-Ward id.

    Sending the query without a `Country` filter would silently fetch the
    global dataset, which is precisely the failure this adapter exists to
    prevent, so an unusable country set must fail instead.
    """


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
# UCDP uses Gleditsch-Ward numeric codes both in the `country_id` response
# field and as the accepted value of the `Country` query filter.
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

_UCDP_COUNTRY_ID_TO_ISO3: dict[int, str] = {
    numeric_id: iso3 for iso3, numeric_id in _ISO3_TO_UCDP_COUNTRY_ID.items()
}


@dataclass
class UCDPAdapter(SourceAdapter):
    """Adapter for the UCDP Georeferenced Event Dataset (GED) API.

    Fetches armed conflict events per country from the UCDP GED API.
    Requires an API token (free academic registration at https://ucdp.uu.se/).

    The GED API is a *filtered query* API, not a bulk feed: the adapter sends
    the target countries as the `Country` filter (Gleditsch-Ward numeric ids)
    together with an explicit `StartDate`/`EndDate` window, so the server
    returns only the requested slice. Both date parameters bound the event's
    `date_end` field, meaning a window selects events by when they ended.

    Signals produced per country:
    - armed_conflict_events: count of events
    - battle_deaths_best: sum of best-estimate fatalities
    - state_based_events: count of events involving state actors (type_of_violence=1)

    Domain: B (Security/Conflict) — complements GDELT Events with curated conflict data.
    """

    country_ids: set[str] | None = None
    source_id: str = "SRC-UCDP-GED"
    domain: str = "B"
    api_base_url: str = "https://ucdpapi.pcr.uu.se/api/gedevents"
    api_version: str = "26.1"
    api_token: str = ""
    api_token_env_var: str = "UCDP_API_TOKEN"
    date_window: tuple[datetime, datetime] | None = None
    lookback_days: int = _DEFAULT_LOOKBACK_DAYS
    page_size: int = _MAX_PAGE_SIZE
    # 50 pages x 1000 rows = 50k events per fetch, costing at most 50 of the
    # 5,000 daily requests. High-intensity conflicts (e.g. Ukraine 2022+) can
    # exceed 10k events in an 18-month window, and hitting max_pages is a hard
    # failure now, so the ceiling must sit above realistic windows.
    max_pages: int = 50
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
            # Resolve the window once: with the default trailing lookback it is
            # derived from the clock, so re-deriving it per page would shift the
            # requested range mid-pagination and drop or duplicate events.
            window = self._resolve_window()
            start, end = window
            events, fetched_rows, total_count, truncated = self._fetch_all_events(token, window)
            records = self._aggregate_events(events)
            diagnostics = (
                f"ucdp_fetch_ok version={self.api_version} "
                f"window={start:%Y-%m-%d}..{end:%Y-%m-%d} "
                f"countries={len({r['country_id'] for r in records})} "
                f"fetched_rows={fetched_rows} matched_events={len(events)} "
                f"records={len(records)} total_count={total_count}"
            )
            if truncated:
                # A partial crawl undercounts conflict events, and an
                # undercounted severity signal is more dangerous than a missing
                # one: it looks like calm. Surface it as a failure and drop the
                # partial records rather than feeding a silent understatement
                # into the scoring chain.
                return FetchResult(
                    records=[],
                    diagnostics=(
                        f"ucdp_truncated version={self.api_version} "
                        f"window={start:%Y-%m-%d}..{end:%Y-%m-%d} "
                        f"stopped after max_pages={self.max_pages} while more pages "
                        f"were available (fetched_rows={fetched_rows}, "
                        f"total_count={total_count}); raise max_pages or narrow the "
                        "window — partial records were discarded to avoid "
                        "understating conflict intensity"
                    ),
                    is_success=False,
                )
            if fetched_rows == 0:
                diagnostics = (
                    f"ucdp_empty_window version={self.api_version} "
                    f"window={start:%Y-%m-%d}..{end:%Y-%m-%d} "
                    "the API returned no rows for this window; the annual GED "
                    "release only covers up to 31 Dec of the preceding year"
                )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except UCDPFilterNotAppliedError as exc:
            return FetchResult(
                records=[], diagnostics=f"ucdp_filter_not_applied: {exc}", is_success=False
            )
        except UCDPUnexpectedHostError as exc:
            return FetchResult(
                records=[], diagnostics=f"ucdp_unexpected_host: {exc}", is_success=False
            )
        except UCDPNoResolvableCountriesError as exc:
            return FetchResult(
                records=[], diagnostics=f"ucdp_no_resolvable_countries: {exc}", is_success=False
            )
        except Exception as exc:
            return FetchResult(
                records=[], diagnostics=f"ucdp_fetch_failed: {exc}", is_success=False
            )

    def _resolve_window(self) -> tuple[datetime, datetime]:
        """Resolve the requested date window, defaulting to a trailing lookback."""
        if self.date_window is not None:
            return self.date_window
        end = self.now_provider()
        return end - timedelta(days=self.lookback_days), end

    def _target_country_gw_ids(self) -> list[int]:
        """Gleditsch-Ward ids to request, honouring the configured country set."""
        if self.country_ids is None:
            selected = set(_ISO3_TO_UCDP_COUNTRY_ID.values())
        else:
            selected = {
                _ISO3_TO_UCDP_COUNTRY_ID[iso3]
                for iso3 in self.country_ids
                if iso3 in _ISO3_TO_UCDP_COUNTRY_ID
            }
        return sorted(selected)

    def _build_query_url(self, window: tuple[datetime, datetime]) -> str:
        """Build the first-page URL with server-side country and date filters.

        Parameter names are case-sensitive. `Country`, `StartDate` and
        `EndDate` are the documented spellings; using `country_id` (the
        *response* field name) would be silently ignored by the API and return
        the whole global dataset.
        """
        start, end = window
        params: dict[str, str] = {
            "pagesize": str(min(self.page_size, _MAX_PAGE_SIZE)),
            "StartDate": start.strftime("%Y-%m-%d"),
            "EndDate": end.strftime("%Y-%m-%d"),
        }
        gw_ids = self._target_country_gw_ids()
        if not gw_ids:
            # Omitting Country would fetch the entire global dataset while the
            # verification guard has nothing to compare against — the exact
            # silent-global-fetch this adapter was reworked to eliminate.
            raise UCDPNoResolvableCountriesError(
                f"none of the configured countries {sorted(self.country_ids or [])} "
                "map to a Gleditsch-Ward id; refusing to query UCDP without a "
                "Country filter"
            )
        params["Country"] = ",".join(str(gw_id) for gw_id in gw_ids)
        return f"{self.api_base_url}/{self.api_version}?{urlencode(params)}"

    def _fetch_json_with_retry(self, url: str, headers: dict[str, str]) -> Any:
        if self.max_retries < 0:
            raise ValueError("UCDP adapter max_retries must be >= 0")

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_json(url, headers)
            except Exception as exc:  # noqa: BLE001
                # An authentication failure cannot be fixed by retrying, and
                # every error consumes a slot of the daily request quota.
                if getattr(exc, "code", None) in _TERMINAL_HTTP_STATUSES:
                    raise
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

    def _fetch_all_events(
        self, token: str, window: tuple[datetime, datetime]
    ) -> tuple[list[dict[str, Any]], int, int | None, bool]:
        """Fetch the filtered event slice, following the API's pagination links.

        Returns the matched events, the number of rows the API actually
        returned (pre-filter), the reported total count, and whether the crawl
        stopped early at `max_pages`. Separating those counters keeps "the API
        returned nothing" distinguishable from "the local filter dropped
        everything", and makes truncation visible instead of silent.
        """
        headers = {"x-ucdp-access-token": token}
        requested_gw_ids = set(self._target_country_gw_ids())
        base_url = self._build_query_url(window)
        all_events: list[dict[str, Any]] = []
        fetched_rows = 0
        total_count: int | None = None
        truncated = False

        url = base_url
        for page in range(self.max_pages):
            response = self._fetch_json_with_retry(url, headers)

            # UCDP returns {"TotalCount": N, "TotalPages": P,
            #               "NextPageUrl": "...", "Result": [...]}
            results = response.get("Result", [])
            if total_count is None:
                total_count = response.get("TotalCount")
            if not results:
                break

            fetched_rows += len(results)
            self._assert_filter_applied(results, requested_gw_ids)

            for event in results:
                country_iso3 = self._resolve_country_from_event(event)
                if country_iso3 is None:
                    continue
                if self.country_ids is not None and country_iso3 not in self.country_ids:
                    continue
                event["_resolved_iso3"] = country_iso3
                all_events.append(event)

            # NextPageUrl is the documented pagination mechanism, and an EMPTY
            # NextPageUrl is the documented end-of-data signal — it must not be
            # confused with the key being absent. TotalPages is honoured
            # whenever present, but never assumed (a missing value must not
            # collapse to 0 and stop the crawl after one page).
            total_pages = response.get("TotalPages")
            pages_exhausted = total_pages is not None and page + 1 >= total_pages
            if "NextPageUrl" in response:
                next_url = (response["NextPageUrl"] or "").strip()
                more_available = bool(next_url) and not pages_exhausted
                if more_available:
                    self._assert_same_host(next_url)
            elif total_pages is not None:
                more_available = not pages_exhausted
                next_url = f"{base_url}&page={page + 1}"
            else:
                # No pagination metadata at all: keep going until a page comes
                # back empty rather than risk silently under-fetching.
                more_available = True
                next_url = f"{base_url}&page={page + 1}"

            if not more_available:
                break
            if page + 1 >= self.max_pages:
                truncated = True
                break
            url = next_url

        return all_events, fetched_rows, total_count, truncated

    def _assert_same_host(self, next_url: str) -> None:
        """Refuse to send the API token to a host the API did not originate from."""
        expected = urlparse(self.api_base_url).netloc
        actual = urlparse(next_url).netloc
        if actual != expected:
            raise UCDPUnexpectedHostError(
                f"UCDP NextPageUrl points at an unexpected host {actual!r} "
                f"(expected {expected!r}); refusing to forward the API token"
            )

    def _assert_filter_applied(
        self, results: list[dict[str, Any]], requested_gw_ids: set[int]
    ) -> None:
        """Fail loudly when the response contains countries we did not request."""
        # An empty request set must be impossible here: _build_query_url refuses
        # to build an unfiltered query, so the guard can never silently disarm.
        assert requested_gw_ids, "filter guard invoked without a requested country set"
        returned: set[int] = set()
        for event in results:
            raw_id = event.get("country_id")
            if raw_id is None:
                continue
            try:
                returned.add(int(raw_id))
            except (TypeError, ValueError):
                continue
        unexpected = returned - requested_gw_ids
        if unexpected:
            raise UCDPFilterNotAppliedError(
                "UCDP returned events for countries that were not requested "
                f"(unexpected Gleditsch-Ward ids: {sorted(unexpected)[:10]}). "
                "The Country filter was probably ignored — verify the query "
                "parameter spelling against https://ucdp.uu.se/apidocs/"
            )

    def _resolve_country_from_event(self, event: dict[str, Any]) -> str | None:
        """Extract ISO-3 country code from a UCDP event.

        UCDP events contain 'country_id' (numeric) and 'country' (name).
        We reverse-map from numeric ID to ISO-3.
        """
        ucdp_country_id = event.get("country_id")
        if ucdp_country_id is None:
            return None
        return _UCDP_COUNTRY_ID_TO_ISO3.get(int(ucdp_country_id))

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
