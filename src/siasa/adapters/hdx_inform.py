"""HDX INFORM Risk Index adapter — humanitarian risk indicators for Domain C.

Source: OCHA Humanitarian Data Exchange (data.humdata.org) → INFORM Risk Index.
Free, no auth. CSV-based dataset with 190+ countries, ISO-3 codes.
Provides INFORM Risk Index composite score and sub-indicators.

Traceability: SwR-ADAPTER-HDX-INFORM, AP-11.6
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import sleep
from typing import Any, Callable
from urllib.request import urlopen

from .base import FetchResult, SourceAdapter


FetchText = Callable[[str], str]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]


def _default_fetch_text(url: str) -> str:
    with urlopen(url, timeout=60) as response:
        return response.read().decode("utf-8")


def _utc_now() -> datetime:
    return datetime.now(UTC)


# Key INFORM indicators to extract (from the full ~80+ indicator set)
_TARGET_INDICATORS: dict[str, str] = {
    "INFORM Risk": "inform_risk",
    "Hazard & Exposure": "hazard_exposure",
    "Vulnerability": "vulnerability",
    "Lack of Coping Capacity": "lack_coping_capacity",
    "Natural": "hazard_natural",
    "Human": "hazard_human",
    "Socio-Economic Vulnerability": "vulnerability_socioeconomic",
    "Vulnerable Groups": "vulnerability_groups",
    "Institutional": "coping_institutional",
    "Infrastructure": "coping_infrastructure",
}


@dataclass
class HDXInformRiskAdapter(SourceAdapter):
    """Fetch INFORM Risk Index data from HDX CSV download.

    Downloads the INFORM Risk Index CSV, filters to target countries and
    key indicators, and returns country-level humanitarian risk records.
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-HDX-INFORM"
    domain: str = "C"
    csv_url: str = (
        "https://data.humdata.org/dataset/f5ec2ee7-8a1b-49b4-864b-70bdb582a022/"
        "resource/7467184f-ac86-4b4a-895c-27c8ad7179ee/download/inform_risk_index.csv"
    )
    fetch_text: FetchText = _default_fetch_text
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    max_retry_delay_seconds: float = 60.0
    target_indicators: dict[str, str] = field(default_factory=lambda: dict(_TARGET_INDICATORS))
    # Freshness: INFORM updates annually
    annual_freshness_hours: int = 8760

    def fetch(self) -> FetchResult:
        """Fetch INFORM Risk Index CSV and parse target indicators."""
        try:
            csv_text = self._fetch_with_retry(self.csv_url)
            records = self._parse_csv(csv_text)

            diagnostics = (
                f"hdx_inform_fetch_ok requested={len(self.country_ids)} "
                f"indicators={len(self.target_indicators)} records={len(records)}"
            )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except Exception as exc:  # noqa: BLE001
            return FetchResult(
                records=[],
                diagnostics=f"hdx_inform_fetch_failed: {exc}",
                is_success=False,
            )

    def _parse_csv(self, csv_text: str) -> list[dict[str, Any]]:
        """Parse INFORM Risk CSV into SIASA records.

        CSV columns: CountryName, Iso3, ValidityYear, IndicatorName, IndicatorScore, Unit
        """
        target_iso3 = set(self.country_ids)
        target_indicators_lower = {k.lower(): v for k, v in self.target_indicators.items()}

        reader = csv.DictReader(io.StringIO(csv_text))
        records: list[dict[str, Any]] = []

        for row in reader:
            iso3 = (row.get("Iso3") or "").strip().upper()
            if iso3 not in target_iso3:
                continue

            indicator_name = (row.get("IndicatorName") or "").strip()
            signal_key = target_indicators_lower.get(indicator_name.lower())
            if signal_key is None:
                continue

            score_str = (row.get("IndicatorScore") or "").strip()
            if not score_str:
                continue

            try:
                score = float(score_str)
            except (ValueError, TypeError):
                continue

            year = (row.get("ValidityYear") or "").strip()

            records.append({
                "country_id": iso3,
                "period": year,
                "signal_key": signal_key,
                "value": score,
                "indicator_name": indicator_name,
                "expected_source_count": 1,
                "freshness_hours": self.annual_freshness_hours,
                "freshness_horizon_hours": self.annual_freshness_hours,
                "quality_flag": "hdx_inform_risk_index",
            })

        records.sort(key=lambda r: (r["country_id"], r["signal_key"]))
        return records

    def _fetch_with_retry(self, url: str) -> str:
        if self.max_retries < 0:
            raise ValueError("HDX INFORM adapter max_retries must be >= 0")

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_text(url)
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
