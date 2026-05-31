"""SIASA health monitoring.

Provides deterministic health checks for operational SIASA deployments:
- Liveness: is the scheduler/system reachable and responsive?
- Source availability: can each configured source be probed?
- Staleness: are latest artifacts within acceptable freshness?
- Status file: write machine-readable health status to disk.

Usage:
    PYTHONPATH=src python -m siasa.runs.health_monitor \\
        --history-db build/run_history/latest_runs.sqlite \\
        --artifacts-dir build/run_artifacts/latest \\
        --output build/health/health_status.json \\
        --max-staleness-hours 48
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class HealthCheck:
    name: str
    status: str  # "ok" | "warning" | "critical"
    message: str
    checked_at: str


@dataclass
class HealthStatus:
    overall: str  # "healthy" | "degraded" | "unhealthy"
    checked_at: str
    checks: list[HealthCheck] = field(default_factory=list)


def check_liveness() -> HealthCheck:
    """Basic liveness: the Python process can execute and report."""
    return HealthCheck(
        name="liveness",
        status="ok",
        message="Process responsive",
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


def check_artifacts_exist(artifacts_dir: Path) -> HealthCheck:
    """Check that the governed artifacts directory contains expected files."""
    now = datetime.now(timezone.utc).isoformat()
    if not artifacts_dir.exists():
        return HealthCheck(name="artifacts_exist", status="critical",
                           message=f"Artifacts dir missing: {artifacts_dir}", checked_at=now)

    expected = ["snapshot.json", "readmodels/system_status.json", "readmodels/world_map.json"]
    missing = [f for f in expected if not (artifacts_dir / f).exists()]
    if missing:
        return HealthCheck(name="artifacts_exist", status="warning",
                           message=f"Missing artifacts: {', '.join(missing)}", checked_at=now)

    return HealthCheck(name="artifacts_exist", status="ok",
                       message=f"All expected artifacts present in {artifacts_dir}", checked_at=now)


def check_artifacts_staleness(artifacts_dir: Path, *, max_staleness_hours: float = 48.0) -> HealthCheck:
    """Check that latest artifacts are not older than max_staleness_hours."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    snapshot_path = artifacts_dir / "snapshot.json"

    if not snapshot_path.exists():
        return HealthCheck(name="artifacts_staleness", status="critical",
                           message="No snapshot.json to check staleness against", checked_at=now_iso)

    try:
        mtime = datetime.fromtimestamp(snapshot_path.stat().st_mtime, tz=timezone.utc)
        age_hours = (now - mtime).total_seconds() / 3600
        if age_hours > max_staleness_hours:
            return HealthCheck(
                name="artifacts_staleness", status="warning",
                message=f"Artifacts are {age_hours:.1f}h old (threshold: {max_staleness_hours}h)",
                checked_at=now_iso,
            )
        return HealthCheck(
            name="artifacts_staleness", status="ok",
            message=f"Artifacts are {age_hours:.1f}h old (within {max_staleness_hours}h threshold)",
            checked_at=now_iso,
        )
    except Exception as exc:
        return HealthCheck(name="artifacts_staleness", status="critical",
                           message=f"Could not check staleness: {exc}", checked_at=now_iso)


def check_run_history_health(history_db_path: Path) -> HealthCheck:
    """Check that the run-history DB exists and has at least one run."""
    now = datetime.now(timezone.utc).isoformat()
    if not history_db_path.exists():
        return HealthCheck(name="run_history", status="warning",
                           message="Run-history DB does not exist yet", checked_at=now)

    try:
        from siasa.data.storage import load_recent_runs
        runs = load_recent_runs(history_db_path, limit=1)
        if not runs:
            return HealthCheck(name="run_history", status="warning",
                               message="Run-history DB exists but contains no runs", checked_at=now)

        latest = runs[0]
        if latest.run_status != "success":
            return HealthCheck(
                name="run_history", status="warning",
                message=f"Latest run {latest.run_id} status={latest.run_status}",
                checked_at=now,
            )
        return HealthCheck(
            name="run_history", status="ok",
            message=f"Latest run {latest.run_id} status=success at {latest.recorded_at}",
            checked_at=now,
        )
    except Exception as exc:
        return HealthCheck(name="run_history", status="critical",
                           message=f"Could not read run history: {exc}", checked_at=now)


def check_source_availability() -> HealthCheck:
    """Probe basic network reachability of configured sources."""
    now = datetime.now(timezone.utc).isoformat()
    probes = {
        "World Bank": "https://api.worldbank.org/v2/country/UKR/indicator/NY.GDP.MKTP.CD?format=json&per_page=1",
        "GDELT Doc": "https://api.gdeltproject.org/api/v2/doc/doc?query=Ukraine&mode=artlist&maxrecords=1&format=json",
        "GDACS": "https://www.gdacs.org/gdacsapi/api/events/getevents?limit=1",
    }
    results = []
    for name, url in probes.items():
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "SIASA-Health/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status < 400:
                    results.append(f"{name}:ok")
                else:
                    results.append(f"{name}:http{resp.status}")
        except Exception as exc:
            results.append(f"{name}:failed({type(exc).__name__})")

    failed = [r for r in results if ":ok" not in r]
    if failed:
        return HealthCheck(
            name="source_availability", status="warning",
            message=f"Source probes: {', '.join(results)}",
            checked_at=now,
        )
    return HealthCheck(
        name="source_availability", status="ok",
        message=f"All source probes ok: {', '.join(results)}",
        checked_at=now,
    )


def run_health_checks(
    *,
    artifacts_dir: Path,
    history_db_path: Path,
    max_staleness_hours: float = 48.0,
    skip_source_probe: bool = False,
) -> HealthStatus:
    """Run all health checks and return aggregated status."""
    checks = [
        check_liveness(),
        check_artifacts_exist(artifacts_dir),
        check_artifacts_staleness(artifacts_dir, max_staleness_hours=max_staleness_hours),
        check_run_history_health(history_db_path),
    ]
    if not skip_source_probe:
        checks.append(check_source_availability())

    statuses = [c.status for c in checks]
    if "critical" in statuses:
        overall = "unhealthy"
    elif "warning" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return HealthStatus(
        overall=overall,
        checked_at=datetime.now(timezone.utc).isoformat(),
        checks=checks,
    )


def write_health_status(health: HealthStatus, output_path: Path) -> None:
    """Write health status to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(health)
    output_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="SIASA health monitor")
    parser.add_argument("--artifacts-dir", default="build/run_artifacts/latest")
    parser.add_argument("--history-db", default="build/run_history/latest_runs.sqlite")
    parser.add_argument("--output", default="build/health/health_status.json")
    parser.add_argument("--max-staleness-hours", type=float, default=48.0)
    parser.add_argument("--skip-source-probe", action="store_true")
    args = parser.parse_args()

    health = run_health_checks(
        artifacts_dir=Path(args.artifacts_dir),
        history_db_path=Path(args.history_db),
        max_staleness_hours=args.max_staleness_hours,
        skip_source_probe=args.skip_source_probe,
    )
    write_health_status(health, Path(args.output))
    print(json.dumps(asdict(health), indent=2, sort_keys=True))
    return 0 if health.overall == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
