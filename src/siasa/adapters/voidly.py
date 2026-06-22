"""Voidly Atlas API adapter — Internet censorship scores for Domain E.

Source: https://api.voidly.ai (Censorship detection via OONI/IODA/CensoredPlanet).
Free demo key (hydra_demo_key) — 100 req/min. Provides country-level censorship
scores with confidence and sample counts.

Traceability: SwR-ADAPTER-VOIDLY, AP-11.3
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import sleep
from typing import Any, Callable
import json
from urllib.request import Request, urlopen

from .base import FetchResult, SourceAdapter


FetchJson = Callable[[str, dict[str, str]], object]
NowProvider = Callable[[], datetime]
SleepFn = Callable[[float], None]


def _default_fetch_json(url: str, headers: dict[str, str] | None = None) -> object:
    req = Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def _utc_now() -> datetime:
    return datetime.now(UTC)


# ISO-2 → ISO-3 mapping for the 50 countries Voidly covers
_ISO2_TO_ISO3: dict[str, str] = {
    "CN": "CHN", "RU": "RUS", "IR": "IRN", "MM": "MMR", "VE": "VEN",
    "YE": "YEM", "BY": "BLR", "SA": "SAU", "AE": "ARE", "SE": "SWE",
    "EG": "EGY", "UZ": "UZB", "KZ": "KAZ", "SD": "SDN", "PK": "PAK",
    "IQ": "IRQ", "UA": "UKR", "TZ": "TZA", "HN": "HND", "QA": "QAT",
    "KG": "KGZ", "NP": "NPL", "MU": "MUS", "GA": "GAB", "SS": "SSD",
    "BD": "BGD", "TH": "THA", "VN": "VNM", "CU": "CUB", "ET": "ETH",
    "TR": "TUR", "IN": "IND", "NG": "NGA", "ID": "IDN", "BR": "BRA",
    "MX": "MEX", "ZA": "ZAF", "KE": "KEN", "PH": "PHL", "CO": "COL",
    "AR": "ARG", "DE": "DEU", "JP": "JPN", "GB": "GBR", "FR": "FRA",
    "US": "USA", "CA": "CAN", "AU": "AUS", "KR": "KOR", "IT": "ITA",
}


@dataclass
class VoidlyAdapter(SourceAdapter):
    """Fetch internet censorship scores from Voidly Atlas API.

    Returns country-level censorship scores (0-1, higher = more censorship),
    confidence levels, and sample counts. Data refreshed near real-time.
    """
    country_ids: tuple[str, ...]
    source_id: str = "SRC-VOIDLY"
    domain: str = "E"
    base_url: str = "https://api.voidly.ai/hydra/v1"
    api_key: str = "hydra_demo_key"
    fetch_json: FetchJson = _default_fetch_json
    now_provider: NowProvider = _utc_now
    retry_sleep: SleepFn = sleep
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    max_retry_delay_seconds: float = 60.0
    # Freshness: scores update near real-time
    realtime_freshness_hours: int = 24

    def fetch(self) -> FetchResult:
        """Fetch censorship scores for all requested countries."""
        try:
            url = f"{self.base_url}/scores"
            headers = {"X-API-Key": self.api_key}
            payload = self._fetch_with_retry(url, headers)
            records = self._parse_payload(payload)

            diagnostics = (
                f"voidly_fetch_ok requested={len(self.country_ids)} "
                f"matched={len(records)}"
            )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except Exception as exc:  # noqa: BLE001
            return FetchResult(
                records=[],
                diagnostics=f"voidly_fetch_failed: {exc}",
                is_success=False,
            )

    def _parse_payload(self, payload: object) -> list[dict[str, Any]]:
        """Parse Voidly scores response into SIASA records."""
        if not isinstance(payload, dict):
            raise ValueError("Voidly payload must be a JSON object")

        scores = payload.get("scores")
        if not isinstance(scores, list):
            raise ValueError("Voidly payload must contain 'scores' array")

        # Build lookup: ISO-3 target set
        target_iso3 = set(self.country_ids)

        now = self.now_provider()
        records: list[dict[str, Any]] = []

        for entry in scores:
            if not isinstance(entry, dict):
                continue
            iso2 = entry.get("country", "")
            iso3 = _ISO2_TO_ISO3.get(iso2)
            if iso3 is None or iso3 not in target_iso3:
                continue

            score = entry.get("score")
            if score is None:
                continue

            confidence = entry.get("confidence", 0.0)
            samples = entry.get("samples", 0)
            last_updated = entry.get("lastUpdated", "")

            records.append({
                "country_id": iso3,
                "period": last_updated[:10] if last_updated else now.strftime("%Y-%m-%d"),
                "signal_key": "censorship_score",
                "value": float(score),
                "confidence": float(confidence),
                "samples": int(samples),
                "expected_source_count": 1,
                "freshness_hours": self.realtime_freshness_hours,
                "freshness_horizon_hours": self.realtime_freshness_hours,
                "quality_flag": "voidly_atlas_api",
            })

        # Sort by country for determinism
        records.sort(key=lambda r: r["country_id"])
        return records

    def _fetch_with_retry(self, url: str, headers: dict[str, str]) -> object:
        if self.max_retries < 0:
            raise ValueError("Voidly adapter max_retries must be >= 0")

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self.fetch_json(url, headers)
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
