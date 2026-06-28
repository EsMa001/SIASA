"""Tests for historical backfill orchestrator (AP-30.2, ALGO-BACKFILL-01).

The orchestrator pulls historical data for validation event pairs using
adapter date_window, normalizes, archives to Parquet, and aligns daily.
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from siasa.runs.historical_backfill import (
    BackfillConfig,
    BackfillResult,
    build_backfill_window,
    run_historical_backfill,
)


# --- AP-30.2: Window derivation ---

def test_build_backfill_window_from_onset_date():
    """Derive a (start, end) date window from onset_date with margins."""
    start, end = build_backfill_window(
        onset_date="2022-02-24",
        days_before=90,
        days_after=30,
    )
    assert start == date(2021, 11, 26)  # 90 days before 2022-02-24
    assert end == date(2022, 3, 26)     # 30 days after 2022-02-24


def test_build_backfill_window_control_case_no_onset():
    """Control cases have no onset; use time_start/time_end directly."""
    start, end = build_backfill_window(
        onset_date=None,
        time_start="2024-01-01",
        time_end="2024-03-31",
    )
    assert start == date(2024, 1, 1)
    assert end == date(2024, 3, 31)


def test_build_backfill_window_raises_without_dates():
    """Must have either onset_date or time_start/time_end."""
    with pytest.raises(ValueError, match="onset_date or time_start/time_end"):
        build_backfill_window(onset_date=None)


# --- AP-30.2: Orchestrator ---

def test_backfill_config_defaults():
    """Config has sensible defaults for margins and adapter list."""
    cfg = BackfillConfig()
    assert cfg.days_before_onset == 90
    assert cfg.days_after_onset == 30
    assert cfg.adapter_source_ids == [
        "SRC-GDELT-DOC",
        "SRC-GDELT-EVENTS",
        "SRC-GDACS",
        "WB-INDICATORS",
    ]


def _make_stub_adapter(source_id: str, records: list[dict]) -> Any:
    """Create a stub adapter that returns canned records."""
    adapter = MagicMock()
    adapter.source_id = source_id
    adapter.domain = "A"
    fetch_result = MagicMock()
    fetch_result.is_success = True
    fetch_result.records = records
    adapter.fetch.return_value = fetch_result
    return adapter


def test_run_historical_backfill_produces_result():
    """The orchestrator returns a BackfillResult with record counts."""
    records = [
        {
            "country_id": "UKR",
            "signal_key": "gdelt_doc_tone",
            "value": -2.5,
            "timestamp": "2022-02-20",
        },
        {
            "country_id": "UKR",
            "signal_key": "gdelt_doc_tone",
            "value": -4.1,
            "timestamp": "2022-02-24",
        },
    ]
    stub = _make_stub_adapter("SRC-GDELT-DOC", records)

    with tempfile.TemporaryDirectory() as tmpdir:
        archive_dir = Path(tmpdir) / "archive"
        cfg = BackfillConfig(
            archive_root=archive_dir,
            adapter_source_ids=["SRC-GDELT-DOC"],
        )
        result = run_historical_backfill(
            case_id="VAL-UKR-2022-001",
            country_id="UKR",
            onset_date="2022-02-24",
            time_start="2021-11-26",
            time_end="2022-03-26",
            adapters=[stub],
            config=cfg,
        )
    assert isinstance(result, BackfillResult)
    assert result.case_id == "VAL-UKR-2022-001"
    assert result.total_raw_records >= 2
    assert result.total_normalized_records >= 2
    assert result.sources_succeeded == ["SRC-GDELT-DOC"]
    assert result.sources_failed == []


def test_run_historical_backfill_handles_adapter_failure():
    """Failed adapters are recorded but don't abort the run."""
    failing_adapter = MagicMock()
    failing_adapter.source_id = "SRC-GDACS"
    failing_adapter.domain = "C"
    fetch_result = MagicMock()
    fetch_result.is_success = False
    fetch_result.records = []
    fetch_result.diagnostics = {"error": "timeout"}
    failing_adapter.fetch.return_value = fetch_result

    ok_records = [{"country_id": "UKR", "signal_key": "gdelt_doc_tone", "value": -1.0, "timestamp": "2022-02-20"}]
    ok_adapter = _make_stub_adapter("SRC-GDELT-DOC", ok_records)

    with tempfile.TemporaryDirectory() as tmpdir:
        archive_dir = Path(tmpdir) / "archive"
        cfg = BackfillConfig(
            archive_root=archive_dir,
            adapter_source_ids=["SRC-GDELT-DOC", "SRC-GDACS"],
        )
        result = run_historical_backfill(
            case_id="VAL-UKR-2022-001",
            country_id="UKR",
            onset_date="2022-02-24",
            time_start="2021-11-26",
            time_end="2022-03-26",
            adapters=[ok_adapter, failing_adapter],
            config=cfg,
        )
    assert "SRC-GDELT-DOC" in result.sources_succeeded
    assert "SRC-GDACS" in result.sources_failed
    assert result.total_raw_records >= 1


def test_run_historical_backfill_writes_manifest():
    """A backfill manifest JSON is written alongside the archive."""
    records = [{"country_id": "UKR", "signal_key": "gdelt_doc_tone", "value": -2.5, "timestamp": "2022-02-20"}]
    stub = _make_stub_adapter("SRC-GDELT-DOC", records)

    with tempfile.TemporaryDirectory() as tmpdir:
        archive_dir = Path(tmpdir) / "archive"
        cfg = BackfillConfig(
            archive_root=archive_dir,
            adapter_source_ids=["SRC-GDELT-DOC"],
        )
        result = run_historical_backfill(
            case_id="VAL-UKR-2022-001",
            country_id="UKR",
            onset_date="2022-02-24",
            time_start="2021-11-26",
            time_end="2022-03-26",
            adapters=[stub],
            config=cfg,
        )
        assert result.manifest_path is not None
        assert result.manifest_path.exists()
        manifest = json.loads(result.manifest_path.read_text())
        assert manifest["case_id"] == "VAL-UKR-2022-001"
        assert manifest["country_id"] == "UKR"
        assert "sources" in manifest
