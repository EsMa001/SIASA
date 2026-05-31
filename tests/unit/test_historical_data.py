from __future__ import annotations

import json
import time
from pathlib import Path

from siasa.data.historical import (
    HistoricalRecord,
    get_retention_horizon,
    load_historical_records,
    persist_historical_records,
    prune_expired_records,
    set_retention_horizon,
)
from siasa.data.storage import persist_operational_latest_run


def _seed_run(db_path: Path, run_id: str = "RUN-001") -> None:
    persist_operational_latest_run(
        db_path,
        run_id=run_id,
        run_status="success",
        pilot_set="representative",
        artifacts_dir=Path("/tmp/artifacts"),
        gui_index=Path("/tmp/gui/index.html"),
        failed_sources=[],
    )


def test_persist_and_load_historical_records(tmp_path: Path) -> None:
    db = tmp_path / "history.sqlite"
    _seed_run(db, "RUN-001")

    count = persist_historical_records(
        db,
        run_id="RUN-001",
        records=[
            {"source_id": "WB-INDICATORS", "country_id": "UKR", "domain": "D",
             "record_type": "raw", "payload": {"gdp": 123.4}},
            {"source_id": "SRC-GDELT-DOC", "country_id": "UKR", "domain": "B",
             "record_type": "normalized", "payload": {"tone": -2.1}},
        ],
    )
    assert count == 2

    results = load_historical_records(db, source_id="WB-INDICATORS")
    assert len(results) == 1
    assert results[0].country_id == "UKR"
    assert results[0].payload["gdp"] == 123.4


def test_load_historical_records_with_filters(tmp_path: Path) -> None:
    db = tmp_path / "history.sqlite"
    _seed_run(db, "RUN-001")

    persist_historical_records(
        db,
        run_id="RUN-001",
        records=[
            {"source_id": "WB-INDICATORS", "country_id": "UKR", "domain": "D",
             "payload": {"gdp": 100}},
            {"source_id": "WB-INDICATORS", "country_id": "POL", "domain": "D",
             "payload": {"gdp": 200}},
            {"source_id": "SRC-GDELT-DOC", "country_id": "UKR", "domain": "B",
             "payload": {"tone": -1}},
        ],
    )

    # Filter by country
    ukr = load_historical_records(db, country_id="UKR")
    assert len(ukr) == 2

    # Filter by country + domain
    ukr_d = load_historical_records(db, country_id="UKR", domain="D")
    assert len(ukr_d) == 1
    assert ukr_d[0].source_id == "WB-INDICATORS"

    # Filter by source
    wb = load_historical_records(db, source_id="WB-INDICATORS")
    assert len(wb) == 2


def test_retention_horizon_default_and_custom(tmp_path: Path) -> None:
    db = tmp_path / "history.sqlite"

    # Default
    h = get_retention_horizon(db, key="A")
    assert h == 168.0  # 7 days

    # Set custom
    set_retention_horizon(db, key="A", hours=336.0)
    h = get_retention_horizon(db, key="A")
    assert h == 336.0

    # Update
    set_retention_horizon(db, key="A", hours=72.0)
    h = get_retention_horizon(db, key="A")
    assert h == 72.0

    # Other keys still default
    h = get_retention_horizon(db, key="B")
    assert h == 168.0


def test_prune_expired_records(tmp_path: Path) -> None:
    db = tmp_path / "history.sqlite"
    _seed_run(db, "RUN-001")

    import os
    from datetime import datetime, timezone, timedelta

    old_time = (datetime.now(timezone.utc) - timedelta(hours=200)).isoformat()
    recent_time = datetime.now(timezone.utc).isoformat()

    persist_historical_records(
        db,
        run_id="RUN-001",
        records=[
            {"source_id": "WB-INDICATORS", "country_id": "UKR", "domain": "D",
             "recorded_at": old_time, "payload": {"old": True}},
            {"source_id": "WB-INDICATORS", "country_id": "UKR", "domain": "D",
             "recorded_at": recent_time, "payload": {"recent": True}},
        ],
    )

    # Default retention is 168h; the old record (200h) should be pruned
    deleted = prune_expired_records(db)
    assert deleted >= 1

    remaining = load_historical_records(db, source_id="WB-INDICATORS")
    assert len(remaining) == 1
    assert remaining[0].payload["recent"] is True


def test_prune_respects_custom_retention(tmp_path: Path) -> None:
    db = tmp_path / "history.sqlite"
    _seed_run(db, "RUN-001")

    from datetime import datetime, timezone, timedelta

    # Record 100 hours old
    time_100h = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
    recent = datetime.now(timezone.utc).isoformat()

    persist_historical_records(
        db,
        run_id="RUN-001",
        records=[
            {"source_id": "WB-INDICATORS", "country_id": "UKR", "domain": "D",
             "recorded_at": time_100h, "payload": {"age": "100h"}},
            {"source_id": "SRC-GDELT-DOC", "country_id": "UKR", "domain": "B",
             "recorded_at": time_100h, "payload": {"age": "100h"}},
        ],
    )

    # Set domain D retention to 48h (record should be pruned)
    # Leave domain B at default 168h (record should survive)
    set_retention_horizon(db, key="D", hours=48.0)

    deleted = prune_expired_records(db)
    assert deleted >= 1

    remaining_d = load_historical_records(db, domain="D")
    assert len(remaining_d) == 0

    remaining_b = load_historical_records(db, domain="B")
    assert len(remaining_b) == 1
