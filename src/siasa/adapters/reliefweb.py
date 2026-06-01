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


# ReliefWeb country name to ISO-3 mapping for pilot set.
# ReliefWeb uses country names in its API; extend as needed.
_RELIEFWEB_COUNTRY_NAMES: dict[str, str] = {
    "UKR": "Ukraine",
    "RUS": "Russian Federation",
    "CHN": "China",
    "TWN": "China - Taiwan Province",
    "ISR": "Israel",
    "IND": "India",
    "IRN": "Iran (Islamic Republic of)",
    "TUR": "Türkiye",
    "PAK": "Pakistan",
    "GEO": "Georgia",
    "POL": "Poland",
    "USA": "United States of America",
    "DEU": "Germany",
    "EST": "Estonia",
    "FIN": "Finland",
    "SAU": "Saudi Arabia",
    "QAT": "Qatar",
    "EGY": "Egypt",
    "NGA": "Nigeria",
    "SDN": "Sudan",
    "MMR": "Myanmar",
}


@dataclass
class ReliefWebAdapter(SourceAdapter):
    """Adapter for the ReliefWeb Reports API (v2).

    Fetches recent humanitarian situation reports per country from the
    ReliefWeb API. Requires a pre-approved appname (register at
    https://apidoc.reliefweb.int/).

    Signals produced per country:
    - humanitarian_report_count: number of recent reports
    - humanitarian_report_sources: number of distinct reporting organizations
    - humanitarian_report_recency: hours since most recent report

    Domain: C (Physical Activity / Social Disruption) — complements GDACS
    disaster data and UNHCR displacement data with humanitarian reporting
    intensity as an indicator of crisis severity.

    API: Requires pre-approved appname. From Nov 2025, generic appnames
    receive HTTP 403. Set RELIEFWEB_APPNAME env var or appname parameter.
    """

    country_ids: set[str] | None = None
    source_id: str = "SRC-RELIEFWEB"
    domain: str = "C"
    api_base_url: str = "https://api.reliefweb.int/v2/reports"
    appname: str = ""
    appname_env_var: str = "RELIEFWEB_APPNAME"
    recent_days: int = 30
    results_per_country: int = 50
    fetch_json: FetchJSON = _default_fetch_json
    now_provider: NowProvider = _utc_now
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    retry_sleep: SleepFn = sleep

    def _resolve_appname(self) -> str:
        if self.appname:
            return self.appname
        return os.environ.get(self.appname_env_var, "").strip()

    def fetch(self) -> FetchResult:
        resolved_appname = self._resolve_appname()
        if not resolved_appname:
            return FetchResult(
                records=[],
                diagnostics=(
                    f"reliefweb_no_appname: set {self.appname_env_var} environment "
                    "variable or provide appname parameter. "
                    "Register at https://apidoc.reliefweb.int/ (required since Nov 2025)."
                ),
                is_success=False,
            )
        try:
            records = self._fetch_all_countries(resolved_appname)
            country_count = len({r["country_id"] for r in records})
            diagnostics = (
                f"reliefweb_fetch_ok countries={country_count} records={len(records)}"
            )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except Exception as exc:
            return FetchResult(
                records=[], diagnostics=f"reliefweb_fetch_failed: {exc}", is_success=False
            )

    def _fetch_json_with_retry(self, url: str, headers: dict[str, str]) -> Any:
        if self.max_retries < 0:
            raise ValueError("ReliefWeb adapter max_retries must be >= 0")

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

    def _fetch_all_countries(self, appname: str) -> list[dict[str, object]]:
        now = self.now_provider()
        cutoff = datetime(
            now.year, now.month, now.day, tzinfo=UTC
        )
        from datetime import timedelta

        date_from = (cutoff - timedelta(days=self.recent_days)).strftime("%Y-%m-%dT00:00:00+00:00")

        target_countries = sorted(self.country_ids) if self.country_ids else sorted(_RELIEFWEB_COUNTRY_NAMES.keys())
        all_records: list[dict[str, object]] = []

        for iso3 in target_countries:
            country_name = _RELIEFWEB_COUNTRY_NAMES.get(iso3)
            if not country_name:
                continue

            # ReliefWeb v2 API query params
            url = (
                f"{self.api_base_url}?appname={appname}"
                f"&filter[field]=country.name"
                f"&filter[value]={_url_encode(country_name)}"
                f"&filter[operator]=AND"
                f"&limit={self.results_per_country}"
                f"&sort[]=date:desc"
                f"&fields[include][]=source"
                f"&fields[include][]=date"
            )

            try:
                headers = {"Accept": "application/json"}
                response = self._fetch_json_with_retry(url, headers)
                reports = response.get("data", [])

                if not reports:
                    continue

                # Aggregate signals
                report_count = len(reports)
                sources: set[str] = set()
                latest_date: datetime | None = None

                for report in reports:
                    fields = report.get("fields", {})

                    # Extract sources
                    for source in fields.get("source", []):
                        source_name = source.get("name", "")
                        if source_name:
                            sources.add(source_name)

                    # Track latest date
                    date_str = fields.get("date", {}).get("created", "")
                    if date_str:
                        try:
                            report_date = datetime.fromisoformat(
                                date_str.replace("Z", "+00:00")
                            )
                            if report_date.tzinfo is None:
                                report_date = report_date.replace(tzinfo=UTC)
                            if latest_date is None or report_date > latest_date:
                                latest_date = report_date
                        except (ValueError, TypeError):
                            pass

                timestamp = (
                    latest_date.strftime("%Y-%m-%dT%H:%M:%SZ") if latest_date else now.strftime("%Y-%m-%dT%H:%M:%SZ")
                )
                freshness_hours = (
                    max(0, int((now - latest_date).total_seconds() // 3600))
                    if latest_date
                    else 0
                )

                all_records.append(
                    {
                        "country_id": iso3,
                        "timestamp": timestamp,
                        "signal_key": "humanitarian_report_count",
                        "value": float(report_count),
                        "expected_source_count": 1,
                        "freshness_hours": freshness_hours,
                        "quality_flag": "reliefweb_reports",
                    }
                )
                if sources:
                    all_records.append(
                        {
                            "country_id": iso3,
                            "timestamp": timestamp,
                            "signal_key": "humanitarian_report_sources",
                            "value": float(len(sources)),
                            "expected_source_count": 1,
                            "freshness_hours": freshness_hours,
                            "quality_flag": "reliefweb_reports",
                        }
                    )
            except Exception:  # noqa: BLE001 - per-country failures should not abort other countries
                continue

        return all_records


def _url_encode(text: str) -> str:
    """Minimal URL encoding for query parameter values."""
    from urllib.parse import quote

    return quote(text, safe="")
