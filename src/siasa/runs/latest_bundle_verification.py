from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_LATEST_ARTIFACTS = (
    "snapshot.json",
    "readmodels/system_status.json",
    "readmodels/world_map.json",
    "readmodels/live_probe_evidence_digest.json",
    "readmodels/live_probe_policy_gate.json",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_latest_bundle(
    artifacts_dir: Path,
    *,
    required_domains: tuple[str, ...] = ("A", "B", "D", "E"),
    allow_partial_success: bool = False,
    allow_failed_sources: bool = False,
) -> dict[str, Any]:
    missing_paths = [relative for relative in REQUIRED_LATEST_ARTIFACTS if not (artifacts_dir / relative).exists()]
    if missing_paths:
        raise ValueError(f"latest bundle missing required artifacts: {', '.join(missing_paths)}")

    system_status = _read_json(artifacts_dir / "readmodels/system_status.json")
    allowed_statuses = {"success", "partial_success"} if allow_partial_success else {"success"}
    run_status = str(system_status.get("run_status"))
    if run_status not in allowed_statuses:
        raise ValueError(
            f"latest bundle run_status '{run_status}' not in allowed statuses: {sorted(allowed_statuses)}"
        )
    failed_sources = list(system_status.get("failed_sources", []))
    if failed_sources and not allow_failed_sources:
        raise ValueError(f"latest bundle has failed_sources: {failed_sources}")

    world_map = _read_json(artifacts_dir / "readmodels/world_map.json")
    active_domains = tuple(str(domain) for domain in world_map.get("active_domains", []))

    digest = _read_json(artifacts_dir / "readmodels/live_probe_evidence_digest.json")
    run_context = digest.get("run_context") if isinstance(digest.get("run_context"), dict) else {}
    if str(run_context.get("run_id", "unknown")) != str(system_status.get("run_id", "unknown")):
        raise ValueError("latest bundle digest run_id does not match system_status run_id")
    if str(run_context.get("run_status", "unknown")) != run_status:
        raise ValueError("latest bundle digest run_status does not match system_status run_status")
    country_set_id = str(run_context.get("country_set_id", "unknown"))
    if country_set_id == "unknown":
        raise ValueError("latest bundle digest missing explicit country_set_id")

    gate = _read_json(artifacts_dir / "readmodels/live_probe_policy_gate.json")
    observed = gate.get("observed") if isinstance(gate.get("observed"), dict) else {}
    if str(observed.get("run_id", "unknown")) != str(system_status.get("run_id", "unknown")):
        raise ValueError("latest bundle policy gate run_id does not match system_status run_id")
    gate_verdict = str(gate.get("gate_verdict", "unknown"))
    if gate_verdict not in {"pass", "fail"}:
        raise ValueError("latest bundle policy gate has invalid gate_verdict")

    missing_required_domains = [domain for domain in required_domains if domain not in active_domains]
    if missing_required_domains:
        raise ValueError(
            "latest bundle missing required active domains: " + ", ".join(missing_required_domains)
        )

    country_profile_dir = artifacts_dir / "readmodels/country_profiles"
    profile_paths = sorted(country_profile_dir.glob("*.json")) if country_profile_dir.exists() else []
    if not profile_paths:
        raise ValueError("latest bundle has no country profiles")

    countries_with_domain_e: list[str] = []
    for profile_path in profile_paths:
        profile = _read_json(profile_path)
        domain_states = profile.get("domain_states", {})
        if isinstance(domain_states, dict) and "E" in domain_states:
            countries_with_domain_e.append(str(profile.get("country_id", profile_path.stem)))

    if not countries_with_domain_e:
        raise ValueError("latest bundle contains no country profile with Domain E state")

    return {
        "artifacts_dir": str(artifacts_dir),
        "run_id": system_status.get("run_id"),
        "run_status": run_status,
        "country_set_id": country_set_id,
        "failed_sources": failed_sources,
        "policy_gate_verdict": gate_verdict,
        "country_profile_count": len(profile_paths),
        "active_domains": list(active_domains),
        "required_domains": list(required_domains),
        "countries_with_domain_e": countries_with_domain_e,
        "status": "ok",
    }
