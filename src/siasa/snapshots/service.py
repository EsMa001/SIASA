from __future__ import annotations

from siasa.runs.run_state import RunState

from .models import Snapshot



def create_snapshot(
    run_state: RunState,
    country_set_id: str,
    active_domains: list[str],
    rule_versions: dict[str, str],
    analytical_outputs: dict[str, object],
    algorithm_version: str,
    data_version: str,
    version: int = 1,
) -> Snapshot:
    if run_state.status not in {"success", "partial_success"}:
        raise ValueError("Snapshots require a success or partial_success run")

    source_state = {result.source_id: result.status for result in run_state.source_results}
    snapshot_id = f"SNAP-{run_state.run_id}-v{version}"
    return Snapshot(
        snapshot_id=snapshot_id,
        run_id=run_state.run_id,
        country_set_id=country_set_id,
        active_domains=active_domains,
        rule_versions=rule_versions,
        source_state=source_state,
        analytical_outputs=analytical_outputs,
        status=run_state.status,
        algorithm_version=algorithm_version,
        data_version=data_version,
    )
