from __future__ import annotations

from .country_report import GeneratedReport
from siasa.snapshots.models import Snapshot



def generate_daily_snapshot_report(snapshot: Snapshot) -> GeneratedReport:
    payload = {
        "snapshot_id": snapshot.snapshot_id,
        "run_id": snapshot.run_id,
        "status": snapshot.status,
        "active_domains": snapshot.active_domains,
        "country_status": snapshot.analytical_outputs.get("country_status", {}),
    }
    markdown = "\n".join(
        [
            "# Daily Snapshot",
            f"Snapshot ID: {snapshot.snapshot_id}",
            f"Run ID: {snapshot.run_id}",
            f"Status: {snapshot.status}",
            f"Active domains: {', '.join(snapshot.active_domains)}",
            f"Country status: {payload['country_status']}",
        ]
    )
    return GeneratedReport(
        report_id=f"REP-DAILY-{snapshot.snapshot_id}",
        report_type="daily_snapshot",
        markdown=markdown,
        json_payload=payload,
    )
