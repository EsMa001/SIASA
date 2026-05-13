from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
from typing import Callable
from urllib.request import urlopen

from .base import FetchResult, SourceAdapter


FetchText = Callable[[str], str]
NowProvider = Callable[[], datetime]

_GDACS_NS = {"gdacs": "http://www.gdacs.org"}
_ALERT_LEVELS = {
    "green": 1.0,
    "orange": 2.0,
    "red": 3.0,
}


def _default_fetch_text(url: str) -> str:
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class GDACSAdapter(SourceAdapter):
    country_ids: set[str] | None = None
    source_id: str = "SRC-GDACS"
    domain: str = "B"
    rss_url: str = "https://www.gdacs.org/xml/rss.xml"
    fetch_text: FetchText = _default_fetch_text
    now_provider: NowProvider = _utc_now

    def fetch(self) -> FetchResult:
        try:
            payload = self.fetch_text(self.rss_url)
            records = self._parse_payload(payload)
            diagnostics = f"gdacs_fetch_ok countries={len(records)} records={len(records)}"
            return FetchResult(records=records, diagnostics=diagnostics, is_success=True)
        except Exception as exc:
            return FetchResult(records=[], diagnostics=f"gdacs_fetch_failed: {exc}", is_success=False)

    def _parse_payload(self, payload: str) -> list[dict[str, object]]:
        root = ET.fromstring(payload)
        channel = root.find("channel")
        if channel is None:
            raise ValueError("GDACS RSS payload must contain channel")

        selected: dict[str, tuple[float, datetime]] = {}
        now = self.now_provider()
        for item in channel.findall("item"):
            country_id = (item.findtext("gdacs:iso3", default="", namespaces=_GDACS_NS) or "").strip().upper()
            if not country_id:
                continue
            if self.country_ids is not None and country_id not in self.country_ids:
                continue
            is_current = (item.findtext("gdacs:iscurrent", default="true", namespaces=_GDACS_NS) or "true").strip().lower()
            if is_current != "true":
                continue
            alert_level_name = (item.findtext("gdacs:alertlevel", default="", namespaces=_GDACS_NS) or "").strip().lower()
            alert_level = _ALERT_LEVELS.get(alert_level_name)
            if alert_level is None:
                continue
            added_text = (item.findtext("gdacs:dateadded", default="", namespaces=_GDACS_NS) or item.findtext("pubDate", default="") or "").strip()
            if not added_text:
                raise ValueError("GDACS RSS items require gdacs:dateadded or pubDate")
            added_at = parsedate_to_datetime(added_text)
            if added_at.tzinfo is None:
                added_at = added_at.replace(tzinfo=UTC)
            else:
                added_at = added_at.astimezone(UTC)

            previous = selected.get(country_id)
            if previous is None or alert_level > previous[0] or (alert_level == previous[0] and added_at > previous[1]):
                selected[country_id] = (alert_level, added_at)

        records: list[dict[str, object]] = []
        for country_id in sorted(selected):
            value, added_at = selected[country_id]
            freshness_hours = max(0, int((now - added_at).total_seconds() // 3600))
            records.append(
                {
                    "country_id": country_id,
                    "timestamp": added_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "signal_key": "disaster_alert_level",
                    "value": value,
                    "expected_source_count": 1,
                    "freshness_hours": freshness_hours,
                    "quality_flag": "gdacs_rss",
                }
            )
        return records
