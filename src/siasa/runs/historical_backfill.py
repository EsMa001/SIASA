"""Historical backfill orchestrator (AP-30.2, ALGO-BACKFILL-01).

Pulls historical data for validation event pairs using adapter date_window,
normalizes records, writes to Parquet archive, and produces a manifest.

Requirement trace: SwR-100, StR-693..696
Algorithm: ALGO-BACKFILL-01
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from siasa.data.normalization_service import normalize_records
from siasa.data.normalization_mappings import NormalizationMappingVersion

logger = logging.getLogger(__name__)


@dataclass
class BackfillConfig:
    """Configuration for a historical backfill run."""
    archive_root: Path = Path("data/archive/backfill")
    days_before_onset: int = 90
    days_after_onset: int = 30
    adapter_source_ids: list[str] = field(default_factory=lambda: [
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "SRC-GDACS",
        "WB-INDICATORS",
    ])


@dataclass
class BackfillResult:
    """Result of a single-case historical backfill run."""
    case_id: str
    country_id: str
    total_raw_records: int = 0
    total_normalized_records: int = 0
    sources_succeeded: list[str] = field(default_factory=list)
    sources_failed: list[str] = field(default_factory=list)
    manifest_path: Path | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)


def build_backfill_window(
    *,
    onset_date: str | None = None,
    time_start: str | None = None,
    time_end: str | None = None,
    days_before: int = 90,
    days_after: int = 30,
) -> tuple[date, date]:
    """Derive a (start, end) date window for historical backfill.

    If onset_date is given, window = [onset - days_before, onset + days_after].
    Otherwise, use explicit time_start/time_end.

    Raises:
        ValueError: if neither onset_date nor time_start/time_end provided.
    """
    if onset_date is not None:
        onset = date.fromisoformat(onset_date)
        return (onset - timedelta(days=days_before), onset + timedelta(days=days_after))

    if time_start is not None and time_end is not None:
        return (date.fromisoformat(time_start), date.fromisoformat(time_end))

    raise ValueError(
        "Must provide either onset_date or time_start/time_end for backfill window derivation."
    )


def _build_default_mappings() -> list[NormalizationMappingVersion]:
    """Build minimal normalization mappings for the 4 backfill adapters."""
    return [
        NormalizationMappingVersion(
            mapping_id=f"MAP-{sid}-v1",
            source_id=sid,
            version="1",
            is_active=True,
        )
        for sid in ["SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "SRC-GDACS", "WB-INDICATORS"]
    ]


def run_historical_backfill(
    *,
    case_id: str,
    country_id: str,
    onset_date: str | None = None,
    time_start: str | None = None,
    time_end: str | None = None,
    adapters: list[Any],
    config: BackfillConfig | None = None,
    mappings: list[NormalizationMappingVersion] | None = None,
) -> BackfillResult:
    """Run a historical backfill for one validation case.

    ALGO-BACKFILL-01: adapter.fetch() → normalize_records → manifest.
    Archive writing (Parquet) is left to the caller or a follow-up step
    to keep this orchestrator testable without pyarrow in unit tests.

    Args:
        case_id: Validation case identifier (e.g. VAL-UKR-2022-001).
        country_id: ISO-3 country code.
        onset_date: Event onset date (ISO format) — for escalation cases.
        time_start: Explicit window start — for control cases.
        time_end: Explicit window end — for control cases.
        adapters: List of adapter instances (must have .source_id, .domain, .fetch()).
        config: Backfill configuration.
        mappings: Normalization mappings; if None, uses defaults.

    Returns:
        BackfillResult with record counts, source outcomes, and manifest path.
    """
    if config is None:
        config = BackfillConfig()
    if mappings is None:
        mappings = _build_default_mappings()

    # Derive window
    window_start, window_end = build_backfill_window(
        onset_date=onset_date,
        time_start=time_start,
        time_end=time_end,
        days_before=config.days_before_onset,
        days_after=config.days_after_onset,
    )
    date_window = (
        datetime(window_start.year, window_start.month, window_start.day),
        datetime(window_end.year, window_end.month, window_end.day),
    )

    result = BackfillResult(case_id=case_id, country_id=country_id)
    all_normalized = []
    source_details: list[dict[str, Any]] = []

    for adapter in adapters:
        source_id = adapter.source_id
        domain = adapter.domain
        logger.info("Backfill %s: fetching %s for %s [%s..%s]",
                     case_id, source_id, country_id, window_start, window_end)
        try:
            # Set date_window on adapter if supported
            if hasattr(adapter, 'date_window'):
                adapter.date_window = date_window

            fetch_result = adapter.fetch()

            if not fetch_result.is_success:
                result.sources_failed.append(source_id)
                source_details.append({
                    "source_id": source_id,
                    "status": "failed",
                    "diagnostics": getattr(fetch_result, 'diagnostics', {}),
                })
                continue

            raw_records = fetch_result.records
            result.total_raw_records += len(raw_records)

            # Normalize
            normalized = normalize_records(
                source_id=source_id,
                domain=domain,
                raw_records=raw_records,
                mappings=mappings,
            )
            result.total_normalized_records += len(normalized)
            all_normalized.extend(normalized)
            result.sources_succeeded.append(source_id)
            source_details.append({
                "source_id": source_id,
                "status": "success",
                "raw_count": len(raw_records),
                "normalized_count": len(normalized),
            })
        except Exception as exc:
            logger.exception("Backfill %s: %s failed", case_id, source_id)
            result.sources_failed.append(source_id)
            source_details.append({
                "source_id": source_id,
                "status": "error",
                "error": str(exc),
            })

    # Write manifest
    manifest_dir = config.archive_root / case_id
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "backfill_manifest.json"
    manifest = {
        "case_id": case_id,
        "country_id": country_id,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "onset_date": onset_date,
        "total_raw_records": result.total_raw_records,
        "total_normalized_records": result.total_normalized_records,
        "sources": source_details,
        "algo": "ALGO-BACKFILL-01",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    result.manifest_path = manifest_path

    return result
