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


def _extract_local_links(html_text: str) -> list[str]:
    links: list[str] = []
    for href in _HREF_RE.findall(html_text):
        candidate = (href or "").strip()
        if not candidate or candidate.lower() in {"none", "null"}:
            continue
        if candidate.startswith(("http://", "https://", "mailto:", "tel:", "javascript:")):
            continue
        if candidate.startswith("#"):
            continue
        links.append(candidate)
    return links


def _crawl_bundle_links(bundle_dir: Path) -> dict[str, Any]:
    html_files = sorted(bundle_dir.rglob("*.html"))
    broken_links: list[dict[str, str]] = []
    checked_links = 0

    for html_file in html_files:
        text = html_file.read_text(encoding="utf-8")
        for href in _extract_local_links(text):
            clean_href = href.split("#", 1)[0].split("?", 1)[0]
            if not clean_href:
                continue
            target = (html_file.parent / clean_href).resolve()
            checked_links += 1
            if not target.exists():
                broken_links.append(
                    {
                        "from": str(html_file.relative_to(bundle_dir)),
                        "href": href,
                        "resolved_target": str(target.relative_to(bundle_dir.resolve())),
                    }
                )

    return {
        "html_file_count": len(html_files),
        "checked_link_count": checked_links,
        "broken_link_count": len(broken_links),
        "broken_links": broken_links,
    }


def build_stakeholder_browser_e2e_acceptance_report(*, repo_root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="siasa-browser-e2e-") as tmp_dir:
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

        analyst_core_pages = [
            "index.html",
            "readiness.html",
            "coverage.html",
            "validation.html",
            "traceability.html",
            "reports.html",
        ]
        analyst_core_pages_present = all((analyst_dir / page).exists() for page in analyst_core_pages)

        viewer_restricted_pages_absent = all(
            not (viewer_dir / page).exists()
            for page in ("reports.html", "runs.html", "annotations.html")
        )
        analyst_operational_pages_present = all(
            (analyst_dir / page).exists()
            for page in ("reports.html", "runs.html", "annotations.html")
        )
        admin_operational_pages_present = all(
            (admin_dir / page).exists()
            for page in ("reports.html", "runs.html", "annotations.html")
        )

        crawl_results = {role: _crawl_bundle_links(path) for role, path in role_dirs.items()}
        broken_link_count = sum(int(payload["broken_link_count"]) for payload in crawl_results.values())
        checked_link_count = sum(int(payload["checked_link_count"]) for payload in crawl_results.values())

        stop_criteria = {
            "all_role_bundles_build": True,
            "analyst_core_pages_present": analyst_core_pages_present,
            "viewer_role_boundaries_enforced": viewer_restricted_pages_absent,
            "analyst_operational_pages_present": analyst_operational_pages_present,
            "admin_operational_pages_present": admin_operational_pages_present,
            "no_broken_internal_links": broken_link_count == 0,
        }

        return {
            "metadata": {
                "work_package": "AP-11",
                "roles": ["viewer", "analyst", "admin"],
            },
            "summary": {
                "bundle_count": len(role_dirs),
                "checked_link_count": checked_link_count,
                "broken_link_count": broken_link_count,
            },
            "stop_criteria": stop_criteria,
            "role_link_crawl": crawl_results,
        }
