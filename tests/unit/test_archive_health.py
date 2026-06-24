"""Tests for Archive Health Monitor (AP-13.14 / SwR-070).

Verifies:
- Record counts per source, domain, and year
- Data gap detection
- Storage size tracking
- Structured health report generation
"""
from __future__ import annotations

from typing import Any

import pytest

from siasa.data.archive_health import ArchiveHealthMonitor, ArchiveHealthReport


def _make_mock_archive_stats() -> dict[str, Any]:
    """Create mock archive statistics."""
    return {
        "sources": {
            "SRC-GDELT-EVENTS": {"record_count": 50000, "years": [2025, 2026]},
            "SRC-WB-INDICATORS": {"record_count": 5000, "years": [2024, 2025]},
        },
        "domains": {
            "A": {"record_count": 30000},
            "B": {"record_count": 15000},
            "C": {"record_count": 10000},
        },
        "years": {
            2024: {"record_count": 5000},
            2025: {"record_count": 40000},
            2026: {"record_count": 10000},
        },
        "total_records": 55000,
        "total_size_bytes": 150_000_000,
        "last_archive_utc": "2026-06-24T04:00:00Z",
    }


# --- TC-SwR-070-001 ---

def test_health_report_from_stats() -> None:
    stats = _make_mock_archive_stats()
    monitor = ArchiveHealthMonitor(archive_stats=stats)
    report = monitor.build_report()

    assert isinstance(report, ArchiveHealthReport)
    assert report.total_records == 55000
    assert report.total_size_bytes == 150_000_000


def test_health_report_source_counts() -> None:
    stats = _make_mock_archive_stats()
    monitor = ArchiveHealthMonitor(archive_stats=stats)
    report = monitor.build_report()

    assert "SRC-GDELT-EVENTS" in report.source_counts
    assert report.source_counts["SRC-GDELT-EVENTS"] == 50000
    assert report.source_counts["SRC-WB-INDICATORS"] == 5000


def test_health_report_domain_counts() -> None:
    stats = _make_mock_archive_stats()
    monitor = ArchiveHealthMonitor(archive_stats=stats)
    report = monitor.build_report()

    assert report.domain_counts == {"A": 30000, "B": 15000, "C": 10000}


def test_health_report_year_counts() -> None:
    stats = _make_mock_archive_stats()
    monitor = ArchiveHealthMonitor(archive_stats=stats)
    report = monitor.build_report()

    assert report.year_counts[2025] == 40000
    assert report.year_counts[2026] == 10000


def test_gap_detection_finds_missing_source_years() -> None:
    stats = _make_mock_archive_stats()
    monitor = ArchiveHealthMonitor(
        archive_stats=stats,
        expected_sources=["SRC-GDELT-EVENTS", "SRC-WB-INDICATORS", "SRC-CISA-KEV"],
    )
    report = monitor.build_report()

    assert "SRC-CISA-KEV" in report.missing_sources


def test_gap_detection_empty_archive() -> None:
    stats = {
        "sources": {},
        "domains": {},
        "years": {},
        "total_records": 0,
        "total_size_bytes": 0,
        "last_archive_utc": None,
    }
    monitor = ArchiveHealthMonitor(archive_stats=stats)
    report = monitor.build_report()

    assert report.total_records == 0
    assert report.is_healthy is False


def test_health_report_to_dict() -> None:
    stats = _make_mock_archive_stats()
    monitor = ArchiveHealthMonitor(archive_stats=stats)
    report = monitor.build_report()
    d = report.to_dict()

    assert "total_records" in d
    assert "source_counts" in d
    assert "domain_counts" in d
    assert "is_healthy" in d


def test_healthy_archive() -> None:
    stats = _make_mock_archive_stats()
    monitor = ArchiveHealthMonitor(archive_stats=stats)
    report = monitor.build_report()

    assert report.is_healthy is True
    assert report.last_archive_utc == "2026-06-24T04:00:00Z"
