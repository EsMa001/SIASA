from __future__ import annotations

from datetime import UTC, datetime

from siasa.adapters.base import FetchResult
from siasa.adapters.gdacs import GDACSAdapter
from siasa.data.normalization_mappings import NormalizationMappingVersion
from siasa.data.normalization_service import normalize_records
from siasa.features.domain_b import DomainBFeatureService


class StubTextFetcher:
    def __init__(self, text: str, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.urls: list[str] = []

    def __call__(self, url: str) -> str:
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        return self.text


def _rss_item(*, iso3: str, alertlevel: str, dateadded: str, eventtype: str, eventid: str, iscurrent: str = "true") -> str:
    return f"""
    <item>
      <title>{alertlevel} {eventtype} in {iso3}</title>
      <link>https://www.gdacs.org/report.aspx?eventtype={eventtype}&amp;eventid={eventid}</link>
      <pubDate>{dateadded}</pubDate>
      <gdacs:dateadded>{dateadded}</gdacs:dateadded>
      <gdacs:iscurrent>{iscurrent}</gdacs:iscurrent>
      <gdacs:eventtype>{eventtype}</gdacs:eventtype>
      <gdacs:alertlevel>{alertlevel}</gdacs:alertlevel>
      <gdacs:eventid>{eventid}</gdacs:eventid>
      <gdacs:iso3>{iso3}</gdacs:iso3>
      <gdacs:country>{iso3}</gdacs:country>
    </item>
    """.strip()


def _rss_feed(items: list[str]) -> str:
    joined = "\n".join(items)
    return f"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0' xmlns:gdacs='http://www.gdacs.org'>
  <channel>
    {joined}
  </channel>
</rss>
"""


def test_gdacs_adapter_fetch_aggregates_highest_current_country_alert_level() -> None:
    adapter = GDACSAdapter(
        country_ids={"UKR", "POL"},
        fetch_text=StubTextFetcher(
            _rss_feed(
                [
                    _rss_item(
                        iso3="UKR",
                        alertlevel="Green",
                        dateadded="Wed, 13 May 2026 08:00:00 GMT",
                        eventtype="FL",
                        eventid="1001",
                    ),
                    _rss_item(
                        iso3="UKR",
                        alertlevel="Red",
                        dateadded="Wed, 13 May 2026 09:30:00 GMT",
                        eventtype="EQ",
                        eventid="1002",
                    ),
                    _rss_item(
                        iso3="POL",
                        alertlevel="Orange",
                        dateadded="Wed, 13 May 2026 07:00:00 GMT",
                        eventtype="TC",
                        eventid="1003",
                    ),
                    _rss_item(
                        iso3="DEU",
                        alertlevel="Red",
                        dateadded="Wed, 13 May 2026 10:00:00 GMT",
                        eventtype="WF",
                        eventid="1004",
                    ),
                    _rss_item(
                        iso3="POL",
                        alertlevel="Red",
                        dateadded="Wed, 13 May 2026 11:00:00 GMT",
                        eventtype="WF",
                        eventid="1005",
                        iscurrent="false",
                    ),
                ]
            )
        ),
        now_provider=lambda: datetime(2026, 5, 13, 11, 30, tzinfo=UTC),
    )

    result = adapter.fetch()

    assert isinstance(result, FetchResult)
    assert result.is_success is True
    assert result.records == [
        {
            "country_id": "POL",
            "timestamp": "2026-05-13T07:00:00Z",
            "signal_key": "disaster_alert_level",
            "value": 2.0,
            "expected_source_count": 1,
            "freshness_hours": 4,
            "quality_flag": "gdacs_rss",
        },
        {
            "country_id": "UKR",
            "timestamp": "2026-05-13T09:30:00Z",
            "signal_key": "disaster_alert_level",
            "value": 3.0,
            "expected_source_count": 1,
            "freshness_hours": 2,
            "quality_flag": "gdacs_rss",
        },
    ]


def test_gdacs_adapter_supports_domain_b_disaster_alert_feature_computation() -> None:
    adapter = GDACSAdapter(
        country_ids={"UKR"},
        fetch_text=StubTextFetcher(
            _rss_feed(
                [
                    _rss_item(
                        iso3="UKR",
                        alertlevel="Red",
                        dateadded="Wed, 13 May 2026 09:30:00 GMT",
                        eventtype="EQ",
                        eventid="1002",
                    )
                ]
            )
        ),
        now_provider=lambda: datetime(2026, 5, 13, 11, 30, tzinfo=UTC),
    )

    result = adapter.fetch()
    normalized = normalize_records(
        source_id=adapter.source_id,
        domain=adapter.domain,
        raw_records=result.records,
        mappings=[
            NormalizationMappingVersion(
                mapping_id="MAP-GDACS-v1",
                source_id=adapter.source_id,
                version="v1",
                is_active=True,
            )
        ],
    )
    features = {feature.feature_id: feature for feature in DomainBFeatureService().compute(normalized)}

    assert features["B_disaster_alert_level"].value == 3.0
    assert features["B_event_count"].value == 0.0


def test_gdacs_adapter_returns_failed_fetch_result_when_rss_fetch_fails() -> None:
    adapter = GDACSAdapter(
        country_ids={"UKR"},
        fetch_text=StubTextFetcher("", error=RuntimeError("gdacs unavailable")),
    )

    result = adapter.fetch()

    assert result.records == []
    assert result.is_success is False
    assert "gdacs unavailable" in result.diagnostics
