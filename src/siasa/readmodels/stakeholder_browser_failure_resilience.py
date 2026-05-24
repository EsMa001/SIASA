from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

_HREF_RE = re.compile(r'href=[\'\"]([^\'\"]+)[\'\"]', re.IGNORECASE)


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


def _links(html_text: str) -> list[str]:
    return [href for href in _HREF_RE.findall(html_text) if href and href.lower() not in {"none", "null"}]


def _link_exists(html_text: str, target_suffix: str) -> bool:
    for href in _links(html_text):
        clean = href.split("#", 1)[0].split("?", 1)[0]
        if clean.endswith(target_suffix):
            return True
    return False


def _resolve_internal(base_page: Path, href: str) -> Path | None:
    clean = href.split("#", 1)[0].split("?", 1)[0].strip()
    if not clean or clean.startswith(("http://", "https://", "mailto:", "tel:", "javascript:")):
        return None
    if clean.startswith("/"):
        clean = clean[1:]
    return (base_page.parent / clean).resolve()


def build_stakeholder_browser_failure_resilience_report(*, repo_root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="siasa-browser-resilience-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        default_artifacts_dir = repo_root / "build" / "run_artifacts" / "latest"
        artifacts_dir = default_artifacts_dir if default_artifacts_dir.exists() else None

        role_dirs = {"analyst": tmp_root / "analyst", "viewer": tmp_root / "viewer", "admin": tmp_root / "admin"}
        for role, out_dir in role_dirs.items():
            _build_gui_bundle(repo_root, out_dir, ui_role=role, artifacts_dir=artifacts_dir)

        analyst_dir = role_dirs["analyst"]
        viewer_dir = role_dirs["viewer"]
        admin_dir = role_dirs["admin"]

        analyst_index_path = analyst_dir / "index.html"
        analyst_readiness_path = analyst_dir / "readiness.html"
        analyst_country_pages = sorted((analyst_dir / "countries").glob("*.html"))
        analyst_domain_pages = sorted((analyst_dir / "domains").glob("*.html"))

        viewer_index = _read(viewer_dir / "index.html")
        analyst_index = _read(analyst_index_path)
        admin_index = _read(admin_dir / "index.html")
        analyst_readiness = _read(analyst_readiness_path)

        role_misrouting_checks = {
            "viewer_hides_reports": not _link_exists(viewer_index, "reports.html"),
            "viewer_hides_annotations": not _link_exists(viewer_index, "annotations.html"),
            "viewer_hides_runs": not _link_exists(viewer_index, "runs.html"),
            "analyst_exposes_reports": _link_exists(analyst_index, "reports.html"),
            "admin_exposes_reports": _link_exists(admin_index, "reports.html"),
        }

        nav_required = [
            (analyst_index_path, "readiness.html"),
            (analyst_index_path, "coverage.html"),
            (analyst_readiness_path, "coverage.html"),
        ]

        if analyst_country_pages:
            nav_required.append((analyst_country_pages[0], "../index.html"))
            nav_required.append((analyst_country_pages[0], "../domains/"))
        if analyst_domain_pages:
            nav_required.append((analyst_domain_pages[0], "../index.html"))

        missing_required_targets = []
        for page, target in nav_required:
            text = _read(page)
            if target.endswith("/"):
                if target not in text:
                    missing_required_targets.append({"page": str(page.relative_to(analyst_dir)), "target": target})
            elif not _link_exists(text, target):
                missing_required_targets.append({"page": str(page.relative_to(analyst_dir)), "target": target})

        broken_internal_links = []
        pages_to_check = [analyst_index_path, analyst_readiness_path]
        pages_to_check.extend(analyst_country_pages[:3])
        pages_to_check.extend(analyst_domain_pages[:3])
        for page in pages_to_check:
            for href in _links(_read(page)):
                resolved = _resolve_internal(page, href)
                if resolved is None:
                    continue
                if not resolved.exists():
                    broken_internal_links.append({"page": str(page.relative_to(analyst_dir)), "href": href})

        checks = {
            "role_misrouting_resilient": all(role_misrouting_checks.values()),
            "required_navigation_targets_present": len(missing_required_targets) == 0,
            "no_broken_internal_links_on_core_paths": len(broken_internal_links) == 0,
            "country_domain_pages_present": len(analyst_country_pages) > 0 and len(analyst_domain_pages) > 0,
        }

        return {
            "metadata": {"work_package": "AP-13", "roles": ["viewer", "analyst", "admin"]},
            "summary": {
                "role_check_count": len(role_misrouting_checks),
                "role_check_passed_count": sum(1 for v in role_misrouting_checks.values() if v),
                "required_target_count": len(nav_required),
                "missing_required_target_count": len(missing_required_targets),
                "broken_internal_link_count": len(broken_internal_links),
            },
            "role_misrouting_checks": role_misrouting_checks,
            "missing_required_targets": missing_required_targets,
            "broken_internal_links": broken_internal_links,
            "stop_criteria": checks,
        }
