from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


_FLOW_IDS = (
    "FLOW-PL-READINESS-GONO-001",
    "FLOW-AN-COUNTRY-DOMAIN-001",
    "FLOW-AN-VALIDATION-REPLAY-001",
    "FLOW-GOV-SOURCE-TRACE-001",
    "FLOW-GOV-REPORT-EVIDENCE-001",
    "FLOW-VIEWER-ROLE-BOUNDARY-001",
)


def _build_gui_bundle(repo_root: Path, output_dir: Path, *, ui_role: str, artifacts_dir: Path | None) -> None:
    command = [
        sys.executable,
        "-m",
        "siasa.gui.local_app",
        "--output-dir",
        str(output_dir),
        "--ui-role",
        ui_role,
        "--skip-stakeholder-e2e-ui-smoke-report",
    ]
    if artifacts_dir is not None:
        command.extend(["--artifacts-dir", str(artifacts_dir)])
    env = dict(os.environ)
    src_path = str((repo_root / "src").resolve())
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_path if not existing_pythonpath else f"{src_path}:{existing_pythonpath}"
    result = subprocess.run(command, cwd=repo_root, env=env, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "local_app build failed"
            f"\ncommand: {' '.join(command)}"
            f"\nstdout:\n{result.stdout}"
            f"\nstderr:\n{result.stderr}"
        )


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_stakeholder_e2e_ui_smoke_report(*, repo_root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="siasa-e2e-ui-smoke-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        analyst_dir = tmp_root / "analyst"
        viewer_dir = tmp_root / "viewer"
        default_artifacts_dir = repo_root / "build" / "run_artifacts" / "latest"
        artifacts_dir = default_artifacts_dir if default_artifacts_dir.exists() else None

        _build_gui_bundle(repo_root, analyst_dir, ui_role="analyst", artifacts_dir=artifacts_dir)
        _build_gui_bundle(repo_root, viewer_dir, ui_role="viewer", artifacts_dir=artifacts_dir)

        readiness_html = _read_text(analyst_dir / "readiness.html")
        index_html = _read_text(analyst_dir / "index.html")
        validation_html = _read_text(analyst_dir / "validation.html")
        coverage_html = _read_text(analyst_dir / "coverage.html")
        traceability_path = analyst_dir / "traceability.html"
        traceability_html = _read_text(traceability_path) if traceability_path.exists() else ""
        reports_html = _read_text(analyst_dir / "reports.html")

        country_pages = list((analyst_dir / "countries").glob("*.html"))
        domain_pages = list((analyst_dir / "domains").glob("*.html"))
        one_country_html = _read_text(country_pages[0]) if country_pages else ""

        flow_results = {
            "FLOW-PL-READINESS-GONO-001": all(
                marker in readiness_html
                for marker in (
                    "Release Readiness Index",
                    "Stakeholder E2E Flow Coverage (AP-04/AP-05)",
                    "Gate Verdict",
                )
            ),
            "FLOW-AN-COUNTRY-DOMAIN-001": (
                "countries/" in index_html
                and "domains/" in one_country_html
                and len(country_pages) > 0
                and len(domain_pages) > 0
            ),
            "FLOW-AN-VALIDATION-REPLAY-001": all(
                marker in validation_html
                for marker in (
                    "Replay Attention Watchlist",
                    "replay-attention-text-filter",
                    "replay-attention-copy-link",
                )
            ),
            "FLOW-GOV-SOURCE-TRACE-001": (
                "Stale Coverage Priority Queue" in coverage_html
                and "Origin Inference Status" in traceability_html
                and "Observed Lag (min)" in traceability_html
            ),
            "FLOW-GOV-REPORT-EVIDENCE-001": (
                "Report / Export View" in reports_html
                and "Reports available" in reports_html
                and "download" in reports_html.lower()
            ),
            "FLOW-VIEWER-ROLE-BOUNDARY-001": (
                (viewer_dir / "index.html").exists()
                and (viewer_dir / "readiness.html").exists()
                and not (viewer_dir / "reports.html").exists()
                and not (viewer_dir / "runs.html").exists()
                and not (viewer_dir / "annotations.html").exists()
            ),
        }

        flow_count = len(_FLOW_IDS)
        covered_flow_count = sum(1 for flow_id in _FLOW_IDS if flow_results.get(flow_id))
        flow_gap_count = flow_count - covered_flow_count

        stop_criteria = {
            "minimum_flow_count_reached": flow_count >= 6,
            "all_flows_covered": flow_gap_count == 0,
            "project_lead_readiness_flow_passed": flow_results["FLOW-PL-READINESS-GONO-001"],
            "analyst_country_domain_flow_passed": flow_results["FLOW-AN-COUNTRY-DOMAIN-001"],
            "analyst_validation_flow_passed": flow_results["FLOW-AN-VALIDATION-REPLAY-001"],
            "governance_source_trace_flow_passed": flow_results["FLOW-GOV-SOURCE-TRACE-001"],
            "governance_report_evidence_flow_passed": flow_results["FLOW-GOV-REPORT-EVIDENCE-001"],
            "viewer_role_boundary_flow_passed": flow_results["FLOW-VIEWER-ROLE-BOUNDARY-001"],
        }

        return {
            "flow_count": flow_count,
            "covered_flow_count": covered_flow_count,
            "flow_gap_count": flow_gap_count,
            "flow_results": flow_results,
            "stop_criteria": stop_criteria,
        }
