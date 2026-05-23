from __future__ import annotations

from pathlib import Path

from siasa.readmodels.stakeholder_e2e_ui_smoke import build_stakeholder_e2e_ui_smoke_report


EXPECTED_FLOW_IDS = {
    "FLOW-PL-READINESS-GONO-001",
    "FLOW-AN-COUNTRY-DOMAIN-001",
    "FLOW-AN-VALIDATION-REPLAY-001",
    "FLOW-GOV-SOURCE-TRACE-001",
    "FLOW-GOV-REPORT-EVIDENCE-001",
    "FLOW-VIEWER-ROLE-BOUNDARY-001",
}


def test_stakeholder_e2e_ui_smoke_report_closes_all_ap04_flow_checks() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_stakeholder_e2e_ui_smoke_report(repo_root=repo_root)

    assert report["flow_count"] >= 6
    assert report["covered_flow_count"] == report["flow_count"]
    assert report["flow_gap_count"] == 0
    assert EXPECTED_FLOW_IDS.issubset(set(report["flow_results"]))
    assert all(report["stop_criteria"].values())
