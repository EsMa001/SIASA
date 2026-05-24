from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


_HREF_RE = re.compile(r"href=['\"]([^'\"]+)['\"]", re.IGNORECASE)


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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _has_link_to(html_text: str, target_suffix: str) -> bool:
    for href in _HREF_RE.findall(html_text):
        if href.lower() in {"none", "null"}:
            continue
        clean = href.split("#", 1)[0].split("?", 1)[0]
        if clean.endswith(target_suffix):
            return True
    return False


def build_stakeholder_browser_interaction_depth_report(*, repo_root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="siasa-browser-depth-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        default_artifacts_dir = repo_root / "build" / "run_artifacts" / "latest"
        artifacts_dir = default_artifacts_dir if default_artifacts_dir.exists() else None

        role_dirs = {
            "analyst": tmp_root / "analyst",
            "viewer": tmp_root / "viewer",
            "admin": tmp_root / "admin",
        }
        for role, out_dir in role_dirs.items():
            _build_gui_bundle(repo_root, out_dir, ui_role=role, artifacts_dir=artifacts_dir)

        analyst_dir = role_dirs["analyst"]
        viewer_dir = role_dirs["viewer"]
        admin_dir = role_dirs["admin"]

        analyst_index = _read(analyst_dir / "index.html")
        analyst_readiness = _read(analyst_dir / "readiness.html")
        analyst_validation = _read(analyst_dir / "validation.html")
        analyst_reports = _read(analyst_dir / "reports.html")

        country_pages = sorted((analyst_dir / "countries").glob("*.html"))
        domain_pages = sorted((analyst_dir / "domains").glob("*.html"))
        sample_country = _read(country_pages[0]) if country_pages else ""
        sample_domain = _read(domain_pages[0]) if domain_pages else ""

        viewer_index = _read(viewer_dir / "index.html")
        admin_index = _read(admin_dir / "index.html")

        transitions = {
            "analyst_index_to_readiness": _has_link_to(analyst_index, "readiness.html"),
            "analyst_readiness_to_coverage": _has_link_to(analyst_readiness, "coverage.html"),
            "analyst_index_has_country_drilldown": "countries/" in analyst_index,
            "analyst_country_to_domain": "../domains/" in sample_country,
            "analyst_domain_to_validation": _has_link_to(sample_domain, "validation.html"),
            "analyst_validation_to_reports": _has_link_to(analyst_validation, "reports.html"),
            "analyst_reports_has_download_actions": "download" in analyst_reports.lower(),
            "viewer_index_hides_reports_navigation": not _has_link_to(viewer_index, "reports.html"),
            "admin_index_exposes_reports_navigation": _has_link_to(admin_index, "reports.html"),
        }

        stop_criteria = {
            "interaction_depth_transitions_closed": all(transitions.values()),
            "minimum_country_domain_pages_present": len(country_pages) > 0 and len(domain_pages) > 0,
            "role_navigation_boundary_consistent": transitions["viewer_index_hides_reports_navigation"] and transitions["admin_index_exposes_reports_navigation"],
        }

        return {
            "metadata": {
                "work_package": "AP-12",
                "roles": ["viewer", "analyst", "admin"],
            },
            "summary": {
                "transition_count": len(transitions),
                "passed_transition_count": sum(1 for value in transitions.values() if value),
                "country_page_count": len(country_pages),
                "domain_page_count": len(domain_pages),
            },
            "transitions": transitions,
            "stop_criteria": stop_criteria,
        }
