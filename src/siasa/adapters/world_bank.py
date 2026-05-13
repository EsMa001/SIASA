from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import urlopen

from .base import FetchResult, SourceAdapter


FetchJson = Callable[[str], object]


def _default_fetch_json(url: str) -> object:
    with urlopen(url, timeout=30) as response:
        return json.load(response)


@dataclass
class WorldBankIndicatorsAdapter(SourceAdapter):
    country_ids: tuple[str, ...]
    source_id: str = "WB-INDICATORS"
    domain: str = "D"
    base_url: str = "https://api.worldbank.org/v2/country"
    per_page: int = 1000
    mrv: int = 1
    annual_freshness_hours: int = 8760
    fetch_json: FetchJson = _default_fetch_json
    indicators: dict[str, str] = field(
        default_factory=lambda: {
            "NY.GDP.MKTP.KD.ZG": "gdp_growth",
            "NE.EXP.GNFS.KD.ZG": "trade_volume_change",
        }
    )

    def fetch(self) -> FetchResult:
        try:
            records: list[dict[str, Any]] = []
            for indicator_id, signal_key in self.indicators.items():
                url = self._build_url(indicator_id)
                payload = self.fetch_json(url)
                records.extend(self._parse_payload(payload, signal_key))
            diagnostics = (
                f"world_bank_fetch_ok countries={len(self.country_ids)} "
                f"indicators={len(self.indicators)} records={len(records)}"
            )
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except (RuntimeError, ValueError, KeyError, TypeError, URLError) as exc:
            return FetchResult(records=[], diagnostics=f"world_bank_fetch_failed: {exc}", is_success=False)

    def _build_url(self, indicator_id: str) -> str:
        countries = ";".join(self.country_ids)
        return (
            f"{self.base_url}/{countries}/indicator/{indicator_id}"
            f"?format=json&per_page={self.per_page}&mrv={self.mrv}"
        )

    def _parse_payload(self, payload: object, signal_key: str) -> list[dict[str, Any]]:
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            raise ValueError("World Bank payload must be a two-element list with a data array")

        records: list[dict[str, Any]] = []
        for row in payload[1]:
            if not isinstance(row, dict):
                raise ValueError("World Bank data rows must be objects")
            value = row.get("value")
            if value is None:
                continue
            country = row.get("country") or {}
            country_id = str(country.get("id") or "").strip()
            period = str(row.get("date") or "").strip()
            if not country_id or not period:
                raise ValueError("World Bank rows require country.id and date")
            records.append(
                {
                    "country_id": country_id,
                    "period": period,
                    "signal_key": signal_key,
                    "value": float(value),
                    "expected_source_count": 1,
                    "freshness_hours": self.annual_freshness_hours,
                    "quality_flag": "world_bank_api",
                }
            )
        return records
