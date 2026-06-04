from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import json

from siasa.readmodels.live_probe_policy_gate import load_live_probe_policy_profile


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_live_probe_evidence_digest(*, artifacts_dir: Path) -> dict[str, Any]:
    readmodels_dir = artifacts_dir / "readmodels"
    system_status = _load_json(readmodels_dir / "system_status.json")
    world_map = _load_json(readmodels_dir / "world_map.json")
    domain_details_dir = readmodels_dir / "domain_details"

    countries = world_map.get("countries") if isinstance(world_map.get("countries"), list) else []
    country_rows: list[dict[str, Any]] = []
    c_active_count = 0
    e_active_count = 0

    for country in countries:
        if not isinstance(country, dict):
            continue
        country_id = str(country.get("country_id", ""))
        active_domains = [str(item) for item in (country.get("active_domains") or [])]
        # Prefer concrete artifact evidence (domain_details files) over active_domains list,
        # because active_domains can remain governance-filtered even when C/E detail artifacts exist.
        has_c = (domain_details_dir / f"{country_id}__C.json").exists() or ("C" in active_domains)
        has_e = (domain_details_dir / f"{country_id}__E.json").exists() or ("E" in active_domains)
        c_active_count += 1 if has_c else 0
        e_active_count += 1 if has_e else 0
        country_rows.append(
            {
                "country_id": country_id,
                "status": str(country.get("status", "unknown")),
                "active_domains": active_domains,
                "has_domain_c": has_c,
                "has_domain_e": has_e,
            }
        )

    total_countries = len(country_rows)
    c_ratio = (c_active_count / total_countries) if total_countries else 0.0
    e_ratio = (e_active_count / total_countries) if total_countries else 0.0
    ce_ratio = ((c_active_count + e_active_count) / (2 * total_countries)) if total_countries else 0.0

    failed_sources = [str(item) for item in (system_status.get("failed_sources") or [])]
    run_status = str(system_status.get("run_status", "unknown"))

    policy_file_raw = os.getenv("LIVE_PROBE_POLICY_FILE")
    policy_profile = os.getenv("LIVE_PROBE_POLICY_PROFILE")
    resolved_policy: dict[str, Any] | None = None
    policy_resolution_error: str | None = None
    if policy_file_raw and policy_profile:
        try:
            policy = load_live_probe_policy_profile(policy_file=Path(policy_file_raw), profile=policy_profile)
            resolved_policy = {
                "min_combined_ce_ratio": policy.min_combined_ce_ratio,
                "allowed_verdicts": list(policy.allowed_verdicts),
                "max_failed_sources": policy.max_failed_sources,
            }
        except Exception as exc:
            policy_resolution_error = str(exc)

    governance_verdict = "green"
    governance_reasons: list[str] = []
    if run_status not in {"success", "partial_success"}:
        governance_verdict = "red"
        governance_reasons.append(f"run_status={run_status}")
    if ce_ratio <= 0.0:
        governance_verdict = "red"
        governance_reasons.append("ce_utilization_zero")
    if run_status == "partial_success" and not failed_sources:
        governance_verdict = "amber"
        governance_reasons.append("partial_success_without_failed_sources")

    if governance_verdict == "green" and failed_sources:
        governance_verdict = "amber"
        governance_reasons.append("failed_sources_present")

    return {
        "schema_version": "v1",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ci_context": {
            "github_run_id": os.getenv("GITHUB_RUN_ID"),
            "github_run_number": os.getenv("GITHUB_RUN_NUMBER"),
            "github_sha": os.getenv("GITHUB_SHA"),
            "github_ref": os.getenv("GITHUB_REF"),
            "github_workflow": os.getenv("GITHUB_WORKFLOW"),
            "github_actor": os.getenv("GITHUB_ACTOR"),
            "live_probe_policy_file": policy_file_raw,
            "live_probe_policy_profile": policy_profile,
            "live_probe_policy_resolved": resolved_policy,
            "live_probe_policy_resolution_error": policy_resolution_error,
        },
        "run_context": {
            "run_id": str(system_status.get("run_id") or system_status.get("last_run") or "unknown"),
            "run_status": run_status,
            "country_set_id": str(system_status.get("country_set_id") or "unknown"),
            "failed_source_count": len(failed_sources),
            "failed_sources": failed_sources,
            "countries_total": total_countries,
            "global_active_domains": [str(item) for item in (world_map.get("active_domains") or [])],
        },
        "ce_utilization": {
            "domain_c_active_country_count": c_active_count,
            "domain_e_active_country_count": e_active_count,
            "countries_total": total_countries,
            "domain_c_ratio": round(c_ratio, 4),
            "domain_e_ratio": round(e_ratio, 4),
            "combined_ce_ratio": round(ce_ratio, 4),
            "country_rows": country_rows,
        },
        "governance_summary": {
            "verdict": governance_verdict,
            "reasons": governance_reasons,
            "operator_next_action": (
                "Investigate failed sources and restore source availability."
                if failed_sources
                else "Increase Domain C/E live coverage in countries where C/E stayed inactive."
                if ce_ratio < 1.0
                else "No immediate action required; live probe governance summary is healthy."
            ),
        },
    }
