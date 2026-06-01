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


_CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def _default_fetch_json(url: str) -> Any:
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "SIASA/1.0"})
    with urlopen(req, timeout=60) as response:
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
class CISAKEVAdapter(SourceAdapter):
    """Adapter for the CISA Known Exploited Vulnerabilities (KEV) catalog.

    Fetches the public CISA KEV JSON feed and computes global cyber-threat
    indicators: recent KEV additions, ransomware-linked KEVs, and overdue
    remediation counts. These are global signals (not country-specific) and
    are broadcast to all target countries as Domain E context.

    Signals produced per country:
    - cyber_kev_recent_count: KEVs added in the last `recent_days` days
    - cyber_kev_ransomware_recent: recent KEVs with known ransomware use
    - cyber_kev_overdue_count: KEVs past their remediation due date
    - cyber_kev_total: total catalog size (slow-moving baseline)

    Domain: E (Cyber/InfoOps) — complements GDELT Doc cyber-mention data
    with structured exploit-threat intelligence.

    API: Fully public, no API key required.
    """

    country_ids: set[str] | None = None
    source_id: str = "SRC-CISA-KEV"
    domain: str = "E"
    catalog_url: str = _CISA_KEV_URL
    recent_days: int = 30
    fetch_json: FetchJSON = _default_fetch_json
    now_provider: NowProvider = _utc_now
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    retry_sleep: SleepFn = sleep

    def fetch(self) -> FetchResult:
        try:
            catalog = self._fetch_catalog()
            vulnerabilities = catalog.get("vulnerabilities", [])
            signals = self._compute_signals(vulnerabilities)
            records = self._broadcast_to_countries(signals)
            diagnostics = (
                f"cisa_kev_fetch_ok total_vulns={len(vulnerabilities)} "
                f"countries={len(self._target_countries())} records={len(records)}"
            )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except Exception as exc:
            return FetchResult(
                records=[], diagnostics=f"cisa_kev_fetch_failed: {exc}", is_success=False
            )

    def _fetch_catalog(self) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_json(self.catalog_url)
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

    def _compute_signals(self, vulnerabilities: list[dict[str, Any]]) -> dict[str, float]:
        now = self.now_provider()
        cutoff = datetime(now.year, now.month, now.day, tzinfo=UTC)

        recent_count = 0
        ransomware_recent = 0
        overdue_count = 0
        total = len(vulnerabilities)

        for vuln in vulnerabilities:
            date_added_str = vuln.get("dateAdded", "")
            due_date_str = vuln.get("dueDate", "")
            ransomware_use = vuln.get("knownRansomwareCampaignUse", "Unknown")

            # Parse dateAdded
            added_date: datetime | None = None
            if date_added_str:
                try:
                    added_date = datetime.strptime(date_added_str, "%Y-%m-%d").replace(tzinfo=UTC)
                except (ValueError, TypeError):
                    pass

            # Recent additions (within last N days)
            if added_date is not None:
                days_since = (cutoff - added_date).days
                if 0 <= days_since <= self.recent_days:
                    recent_count += 1
                    if ransomware_use == "Known":
                        ransomware_recent += 1

            # Overdue (past due date)
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                    if due_date < cutoff:
                        overdue_count += 1
                except (ValueError, TypeError):
                    pass

        return {
            "cyber_kev_recent_count": float(recent_count),
            "cyber_kev_ransomware_recent": float(ransomware_recent),
            "cyber_kev_overdue_count": float(overdue_count),
            "cyber_kev_total": float(total),
        }

    def _target_countries(self) -> set[str]:
        if self.country_ids:
            return self.country_ids
        # Default pilot set if no country filter
        return {
            "UKR", "RUS", "CHN", "TWN", "ISR", "IND", "IRN", "TUR",
            "PAK", "GEO", "POL", "USA", "DEU", "EST", "FIN",
        }

    def _broadcast_to_countries(self, signals: dict[str, float]) -> list[dict[str, object]]:
        """Broadcast global KEV signals to all target countries.

        Since KEV data is not country-specific, each country gets the same
        global cyber-threat context. The quality_flag 'cisa_kev_global'
        makes the non-country-specific nature explicit.
        """
        now = self.now_provider()
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        records: list[dict[str, object]] = []

        for country_id in sorted(self._target_countries()):
            for signal_key, value in sorted(signals.items()):
                if value <= 0:
                    continue
                records.append(
                    {
                        "country_id": country_id,
                        "timestamp": timestamp,
                        "signal_key": signal_key,
                        "value": value,
                        "expected_source_count": 1,
                        "freshness_hours": 0,  # Catalog is fetched now
                        "quality_flag": "cisa_kev_global",
                    }
                )
        return records
