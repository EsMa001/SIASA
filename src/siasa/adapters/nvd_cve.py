"""NVD CVE 2.0 adapter — cyber vulnerability signals for Domain E.

Source: https://services.nvd.nist.gov/rest/json/cves/2.0
Free, no auth required (optional API key for higher rate limits).
Rate limit: 5 requests per 30 seconds without key.

Fetches daily CVE publications, extracts CVSS scores, and aggregates
into daily counts and severity metrics.

Traceability: SwR-075, AP-14.4
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import sleep
from typing import Any, Callable
import json
from urllib.request import Request, urlopen

from .base import FetchResult, SourceAdapter


FetchJson = Callable[[str], object]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]

_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _extract_cvss_score(metrics: dict[str, Any]) -> float | None:
    """Extract the best available CVSS base score from NVD metrics.

    Prefers v3.1, falls back to v3.0, then v2.0.
    """
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        metric_list = metrics.get(key)
        if isinstance(metric_list, list) and metric_list:
            cvss_data = metric_list[0].get("cvssData", {})
            score = cvss_data.get("baseScore")
            if score is not None:
                return float(score)
    return None


def _extract_severity(metrics: dict[str, Any]) -> str:
    """Extract CVSS severity label (CRITICAL, HIGH, MEDIUM, LOW)."""
    for key in ("cvssMetricV31", "cvssMetricV30"):
        metric_list = metrics.get(key)
        if isinstance(metric_list, list) and metric_list:
            cvss_data = metric_list[0].get("cvssData", {})
            sev = cvss_data.get("baseSeverity", "")
            if sev:
                return sev.upper()
    return "UNKNOWN"


def _default_fetch_json(url: str) -> object:
    req = Request(url, headers={"User-Agent": "SIASA/1.0"})
    with urlopen(req, timeout=60) as response:
        return json.load(response)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class NVDCVEAdapter(SourceAdapter):
    """Fetch daily CVE publications and aggregate CVSS metrics.

    Produces three signal types:
    - nvd_cve_count_daily: Total CVEs published per day
    - nvd_avg_cvss_base: Average CVSS base score per day
    - nvd_critical_cve_count: Count of CRITICAL severity CVEs per day
    """
    source_id: str = "SRC-NVD-CVE"
    domain: str = "E"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    max_retry_delay_seconds: float = 60.0
    lookback_days: int = 1
    freshness_hours: int = 48

    def fetch(self) -> FetchResult:
        """Fetch CVEs published in the lookback window and aggregate."""
        now = self.now_provider()
        start = now - timedelta(days=self.lookback_days)

        # NVD API date format: ISO 8601 with T and timezone
        start_str = start.strftime("%Y-%m-%dT00:00:00.000")
        end_str = now.strftime("%Y-%m-%dT23:59:59.999")

        url = (
            f"{_BASE_URL}?"
            f"pubStartDate={start_str}&pubEndDate={end_str}"
        )

        try:
            payload = self._fetch_with_retry(url)
        except Exception as exc:  # noqa: BLE001
            return FetchResult(
                records=[],
                diagnostics=f"nvd_fetch_failed: {exc}",
                is_success=False,
            )

        try:
            records = self._aggregate(payload, now)
        except Exception as exc:  # noqa: BLE001
            return FetchResult(
                records=[],
                diagnostics=f"nvd_parse_failed: {exc}",
                is_success=False,
            )

        diagnostics = f"nvd_fetch_ok records={len(records)}"
        return FetchResult(
            records=records,
            diagnostics=diagnostics,
            is_success=True,
        )

    def _aggregate(
        self, payload: object, now: datetime
    ) -> list[dict[str, Any]]:
        """Aggregate CVE data into daily signal records."""
        if not isinstance(payload, dict):
            return []

        vulnerabilities = payload.get("vulnerabilities", [])
        if not isinstance(vulnerabilities, list):
            return []

        period = now.strftime("%Y-%m-%d")

        total_count = len(vulnerabilities)
        cvss_scores: list[float] = []
        critical_count = 0

        for vuln in vulnerabilities:
            if not isinstance(vuln, dict):
                continue
            cve = vuln.get("cve", {})
            if not isinstance(cve, dict):
                continue

            metrics = cve.get("metrics", {})
            if not isinstance(metrics, dict):
                continue

            score = _extract_cvss_score(metrics)
            if score is not None:
                cvss_scores.append(score)

            severity = _extract_severity(metrics)
            if severity == "CRITICAL":
                critical_count += 1

        records: list[dict[str, Any]] = []

        # Signal 1: Daily CVE count
        records.append(self._make_record(
            signal_key="nvd_cve_count_daily",
            value=total_count,
            period=period,
        ))

        # Signal 2: Average CVSS base score
        if cvss_scores:
            avg_cvss = round(sum(cvss_scores) / len(cvss_scores), 2)
            records.append(self._make_record(
                signal_key="nvd_avg_cvss_base",
                value=avg_cvss,
                period=period,
            ))

        # Signal 3: Critical CVE count
        records.append(self._make_record(
            signal_key="nvd_critical_cve_count",
            value=critical_count,
            period=period,
        ))

        return records

    def _make_record(
        self,
        signal_key: str,
        value: float | int,
        period: str,
    ) -> dict[str, Any]:
        return {
            "country_id": "GLOBAL",  # CVEs are not country-specific
            "period": period,
            "signal_key": signal_key,
            "value": value,
            "quality_flag": "nvd_cve_api",
            "freshness_hours": self.freshness_hours,
            "freshness_horizon_hours": self.freshness_hours,
            "expected_source_count": 1,
        }

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
