"""SIASA Archive Health Monitor (AP-13.14).

Implements:
- SwR-070: Archive health monitoring with per-source/domain/year record counts,
  gap detection, storage tracking, and structured health reports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence


@dataclass
class ArchiveHealthReport:
    """Structured health report for the Parquet archive."""
    total_records: int = 0
    total_size_bytes: int = 0
    last_archive_utc: Optional[str] = None
    source_counts: dict[str, int] = field(default_factory=dict)
    domain_counts: dict[str, int] = field(default_factory=dict)
    year_counts: dict[int, int] = field(default_factory=dict)
    missing_sources: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        """Archive is healthy if it has records and no missing sources."""
        return self.total_records > 0 and len(self.missing_sources) == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to plain dict for serialization."""
        return {
            "total_records": self.total_records,
            "total_size_bytes": self.total_size_bytes,
            "last_archive_utc": self.last_archive_utc,
            "source_counts": self.source_counts,
            "domain_counts": self.domain_counts,
            "year_counts": self.year_counts,
            "missing_sources": self.missing_sources,
            "gaps": self.gaps,
            "is_healthy": self.is_healthy,
        }


class ArchiveHealthMonitor:
    """Monitor for Parquet archive health.

    Analyzes archive statistics to produce a structured health report
    with per-source/domain/year counts, gap detection, and storage info.
    """

    def __init__(
        self,
        archive_stats: dict[str, Any],
        expected_sources: Optional[Sequence[str]] = None,
    ) -> None:
        self._stats = archive_stats
        self._expected_sources = list(expected_sources) if expected_sources else []

    def build_report(self) -> ArchiveHealthReport:
        """Build a comprehensive health report from archive statistics.

        Returns:
            ArchiveHealthReport with counts, gaps, and health status.
        """
        report = ArchiveHealthReport(
            total_records=self._stats.get("total_records", 0),
            total_size_bytes=self._stats.get("total_size_bytes", 0),
            last_archive_utc=self._stats.get("last_archive_utc"),
        )

        # Source counts
        sources = self._stats.get("sources", {})
        for source_id, info in sources.items():
            report.source_counts[source_id] = info.get("record_count", 0)

        # Domain counts
        domains = self._stats.get("domains", {})
        for domain, info in domains.items():
            report.domain_counts[domain] = info.get("record_count", 0)

        # Year counts
        years = self._stats.get("years", {})
        for year, info in years.items():
            report.year_counts[int(year)] = info.get("record_count", 0)

        # Gap detection: missing expected sources
        actual_sources = set(sources.keys())
        for expected in self._expected_sources:
            if expected not in actual_sources:
                report.missing_sources.append(expected)

        return report
