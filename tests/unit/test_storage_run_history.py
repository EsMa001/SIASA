from __future__ import annotations

from pathlib import Path

from siasa.data.storage import (
    load_recent_runs,
    load_source_results_for_run,
    persist_operational_latest_run,
    persist_country_domain_scores,
    load_country_domain_time_series,
    load_latest_country_scores,
)


def test_persist_operational_latest_run_writes_run_and_sources(tmp_path: Path) -> None:
    db_path = tmp_path / "run_history.sqlite"

    persist_operational_latest_run(
        db_path,
        run_id="RUN-LATEST-001",
        run_status="success",
        pilot_set="extended-focus-complete",
        artifacts_dir=tmp_path / "artifacts/latest",
        gui_index=tmp_path / "gui/latest/index.html",
        failed_sources=[],
        source_results=[
            {"source_id": "WB-INDICATORS", "status": "success", "diagnostics": ""},
            {"source_id": "SRC-GDELT-DOC", "status": "failed", "diagnostics": "timeout"},
        ],
        country_set_id="MVP-COUNTRIES-LIVE-extended-focus-complete-v1",
        countries_total=11,
        countries_with_updates=9,
        countries_without_updates_count=2,
        countries_without_updates=["EST", "MMR"],
        combined_ce_ratio=0.8571,
        governance_verdict="amber",
        policy_gate_verdict="pass",
        release_verdict="blocked_by_known_gaps",
        readiness_interpretation="runtime_degraded_and_release_blocked",
        known_gap_count=2,
        allow_partial_success=False,
        allow_failed_sources=False,
        allow_policy_gate_fail=False,
    )

    runs = load_recent_runs(db_path, limit=5)
    assert len(runs) == 1
    assert runs[0].run_id == "RUN-LATEST-001"
    assert runs[0].run_status == "success"
    assert runs[0].pilot_set == "extended-focus-complete"
    assert runs[0].failed_sources == []
    assert runs[0].country_set_id == "MVP-COUNTRIES-LIVE-extended-focus-complete-v1"
    assert runs[0].countries_total == 11
    assert runs[0].countries_with_updates == 9
    assert runs[0].countries_without_updates_count == 2
    assert runs[0].countries_without_updates == ["EST", "MMR"]
    assert runs[0].combined_ce_ratio == 0.8571
    assert runs[0].governance_verdict == "amber"
    assert runs[0].policy_gate_verdict == "pass"
    assert runs[0].release_verdict == "blocked_by_known_gaps"
    assert runs[0].readiness_interpretation == "runtime_degraded_and_release_blocked"
    assert runs[0].known_gap_count == 2
    assert runs[0].allow_partial_success is False
    assert runs[0].allow_failed_sources is False
    assert runs[0].allow_policy_gate_fail is False

    source_results = load_source_results_for_run(db_path, run_id="RUN-LATEST-001")
    assert [entry.source_id for entry in source_results] == ["SRC-GDELT-DOC", "WB-INDICATORS"]
    assert source_results[0].status == "failed"
    assert source_results[0].diagnostics == "timeout"


def test_persist_operational_latest_run_upserts_existing_run(tmp_path: Path) -> None:
    db_path = tmp_path / "run_history.sqlite"

    persist_operational_latest_run(
        db_path,
        run_id="RUN-LATEST-001",
        run_status="partial_success",
        pilot_set="representative",
        artifacts_dir=tmp_path / "artifacts/latest",
        gui_index=tmp_path / "gui/latest/index.html",
        failed_sources=["SRC-GDELT-DOC"],
        source_results=[
            {"source_id": "SRC-GDELT-DOC", "status": "failed", "diagnostics": "timeout"},
        ],
        country_set_id="MVP-COUNTRIES-LIVE-representative-v1",
        countries_total=4,
        countries_with_updates=3,
        countries_without_updates_count=1,
        countries_without_updates=["POL"],
        combined_ce_ratio=0.5,
        governance_verdict="amber",
        policy_gate_verdict="pass",
        release_verdict="blocked_by_known_gaps",
        readiness_interpretation="runtime_degraded_and_release_blocked",
        known_gap_count=1,
        allow_partial_success=True,
        allow_failed_sources=True,
        allow_policy_gate_fail=False,
    )

    persist_operational_latest_run(
        db_path,
        run_id="RUN-LATEST-001",
        run_status="success",
        pilot_set="extended-focus-complete",
        artifacts_dir=tmp_path / "artifacts/latest_v2",
        gui_index=tmp_path / "gui/latest_v2/index.html",
        failed_sources=[],
        source_results=[
            {"source_id": "WB-INDICATORS", "status": "success", "diagnostics": ""},
        ],
        country_set_id="MVP-COUNTRIES-LIVE-extended-focus-complete-v1",
        countries_total=11,
        countries_with_updates=11,
        countries_without_updates_count=0,
        countries_without_updates=[],
        combined_ce_ratio=0.8571,
        governance_verdict="green",
        policy_gate_verdict="pass",
        release_verdict="ready",
        readiness_interpretation="release_ready",
        known_gap_count=0,
        allow_partial_success=False,
        allow_failed_sources=False,
        allow_policy_gate_fail=False,
    )

    runs = load_recent_runs(db_path, limit=5)
    assert len(runs) == 1
    assert runs[0].run_status == "success"
    assert runs[0].pilot_set == "extended-focus-complete"
    assert runs[0].artifacts_dir.endswith("artifacts/latest_v2")
    assert runs[0].gui_index.endswith("gui/latest_v2/index.html")
    assert runs[0].failed_sources == []
    assert runs[0].country_set_id == "MVP-COUNTRIES-LIVE-extended-focus-complete-v1"
    assert runs[0].countries_total == 11
    assert runs[0].countries_with_updates == 11
    assert runs[0].countries_without_updates_count == 0
    assert runs[0].countries_without_updates == []
    assert runs[0].combined_ce_ratio == 0.8571
    assert runs[0].governance_verdict == "green"
    assert runs[0].policy_gate_verdict == "pass"
    assert runs[0].release_verdict == "ready"
    assert runs[0].readiness_interpretation == "release_ready"
    assert runs[0].known_gap_count == 0
    assert runs[0].allow_partial_success is False
    assert runs[0].allow_failed_sources is False
    assert runs[0].allow_policy_gate_fail is False

    source_results = load_source_results_for_run(db_path, run_id="RUN-LATEST-001")
    assert len(source_results) == 1
    assert source_results[0].source_id == "WB-INDICATORS"
    assert source_results[0].status == "success"


def test_persist_and_query_country_domain_scores(tmp_path: Path) -> None:
    db_path = tmp_path / "run_history.sqlite"

    # Create two runs
    for run_id, status in [("RUN-001", "success"), ("RUN-002", "success")]:
        persist_operational_latest_run(
            db_path,
            run_id=run_id,
            run_status=status,
            pilot_set="representative",
            artifacts_dir=tmp_path / "artifacts",
            gui_index=tmp_path / "gui/index.html",
            failed_sources=[],
        )

    persist_country_domain_scores(
        db_path,
        run_id="RUN-001",
        scores=[
            {"country_id": "UKR", "domain": "A", "status": "D2", "score": 0.7, "data_sufficiency": "sufficient"},
            {"country_id": "UKR", "domain": "B", "status": "D1", "score": 0.4, "data_sufficiency": "sufficient"},
            {"country_id": "POL", "domain": "A", "status": "D0", "score": 0.1, "data_sufficiency": "sufficient"},
        ],
    )
    persist_country_domain_scores(
        db_path,
        run_id="RUN-002",
        scores=[
            {"country_id": "UKR", "domain": "A", "status": "D3", "score": 0.9, "data_sufficiency": "sufficient"},
            {"country_id": "UKR", "domain": "B", "status": "D1", "score": 0.45, "data_sufficiency": "marginal"},
        ],
    )

    # Time series for UKR domain A
    ts = load_country_domain_time_series(db_path, country_id="UKR", domain="A")
    assert len(ts) == 2
    assert ts[0].run_id == "RUN-002"  # most recent first
    assert ts[0].score == 0.9
    assert ts[1].run_id == "RUN-001"
    assert ts[1].score == 0.7

    # Latest scores for UKR
    latest = load_latest_country_scores(db_path, country_id="UKR")
    domains = {entry.domain: entry for entry in latest}
    assert "A" in domains
    assert "B" in domains
    assert domains["A"].run_id == "RUN-002"
    assert domains["A"].status == "D3"
    assert domains["B"].data_sufficiency == "marginal"


def test_persist_country_domain_scores_upserts(tmp_path: Path) -> None:
    db_path = tmp_path / "run_history.sqlite"

    persist_operational_latest_run(
        db_path,
        run_id="RUN-001",
        run_status="success",
        pilot_set="representative",
        artifacts_dir=tmp_path / "artifacts",
        gui_index=tmp_path / "gui/index.html",
        failed_sources=[],
    )

    persist_country_domain_scores(
        db_path,
        run_id="RUN-001",
        scores=[
            {"country_id": "UKR", "domain": "A", "status": "D1", "score": 0.3, "data_sufficiency": "sufficient"},
        ],
    )

    # Overwrite with new data
    persist_country_domain_scores(
        db_path,
        run_id="RUN-001",
        scores=[
            {"country_id": "UKR", "domain": "A", "status": "D2", "score": 0.6, "data_sufficiency": "marginal"},
        ],
    )

    ts = load_country_domain_time_series(db_path, country_id="UKR", domain="A")
    assert len(ts) == 1
    assert ts[0].score == 0.6
    assert ts[0].data_sufficiency == "marginal"
