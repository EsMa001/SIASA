from __future__ import annotations


def _source_status_by_source_id(sources: list[dict[str, object]]) -> dict[str, str]:
    return {
        str(source.get("source_id", "unknown")): str(source.get("status", "unknown"))
        for source in sources
    }


def _enrich_source_activation_readiness(
    source_activation_readiness: list[dict[str, object]],
    source_status_by_source_id: dict[str, str],
) -> list[dict[str, object]]:
    enriched_rows: list[dict[str, object]] = []
    for item in source_activation_readiness:
        enriched = dict(item)
        source_id = str(item.get("source_id", "unknown"))
        activation_status = str(item.get("activation_status", "unknown"))
        runtime_source_status = source_status_by_source_id.get(source_id, "not_in_run")
        applicable_country_count = int(item.get("applicable_country_count", len(item.get("applicable_country_ids", []))))
        if applicable_country_count <= 0:
            closure_status = "not_applicable_in_requested_scope"
            activation_evidence = "not_applicable"
            closure_next_step = "No governed countries in the requested slice use this source."
        elif activation_status == "blocked_missing_credentials":
            closure_status = "external_blocker_present"
            activation_evidence = "not_attempted_missing_credentials"
            closure_next_step = str(item.get("activation_next_step", "Resolve missing credentials/registration."))
        elif runtime_source_status == "success":
            closure_status = "activated_with_live_evidence"
            activation_evidence = "live_source_success"
            closure_next_step = "Activation evidence collected in the latest governed run."
        elif runtime_source_status == "failed":
            closure_status = "credentialed_but_live_fetch_failed"
            activation_evidence = "live_source_failed"
            closure_next_step = "Investigate latest source diagnostics and rerun after remediation."
        else:
            closure_status = "configured_but_not_evidenced"
            activation_evidence = (
                "prepared_adapter_only" if runtime_source_status == "prepared_adapter" else "no_runtime_source_row"
            )
            closure_next_step = "Run governed live pipeline to collect first credential-backed source evidence."
        enriched["runtime_source_status"] = runtime_source_status
        enriched["activation_evidence"] = activation_evidence
        enriched["closure_status"] = closure_status
        enriched["closure_next_step"] = closure_next_step
        enriched_rows.append(enriched)
    return enriched_rows


def _build_source_activation_readiness_summary(
    source_activation_readiness: list[dict[str, object]],
) -> dict[str, object]:
    status_counts: dict[str, int] = {}
    source_ids_by_status: dict[str, list[str]] = {}
    country_scope_by_status: dict[str, set[str]] = {}
    closure_counts: dict[str, int] = {}
    source_ids_by_closure: dict[str, list[str]] = {}
    for item in source_activation_readiness:
        status = str(item.get("activation_status", "unknown"))
        closure_status = str(item.get("closure_status", "unknown"))
        source_id = str(item.get("source_id", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        closure_counts[closure_status] = closure_counts.get(closure_status, 0) + 1
        source_ids_by_status.setdefault(status, []).append(source_id)
        source_ids_by_closure.setdefault(closure_status, []).append(source_id)
        country_scope_by_status.setdefault(status, set()).update(
            str(country_id)
            for country_id in item.get("applicable_country_ids", [])
            if str(country_id).strip()
        )
    blocked_sources = list(source_ids_by_status.get("blocked_missing_credentials", []))
    ready_sources = list(source_ids_by_status.get("configured_ready", []))
    blocked_countries = sorted(country_scope_by_status.get("blocked_missing_credentials", set()))
    ready_countries = sorted(country_scope_by_status.get("configured_ready", set()))
    activated_sources = list(source_ids_by_closure.get("activated_with_live_evidence", []))
    external_blocked_sources = list(source_ids_by_closure.get("external_blocker_present", []))
    failed_activation_sources = list(source_ids_by_closure.get("credentialed_but_live_fetch_failed", []))
    pending_evidence_sources = list(source_ids_by_closure.get("configured_but_not_evidenced", []))
    scoped_out_sources = list(source_ids_by_closure.get("not_applicable_in_requested_scope", []))
    if external_blocked_sources:
        overall_closure_status = "external_blockers_present"
        operator_next_step = (
            "Resolve credential/registration blockers for: " + ", ".join(external_blocked_sources)
        )
    elif failed_activation_sources:
        overall_closure_status = "activation_attempt_failures_present"
        operator_next_step = (
            "Investigate failed live activation attempts for: " + ", ".join(failed_activation_sources)
        )
    elif pending_evidence_sources:
        overall_closure_status = "pending_live_activation_evidence"
        operator_next_step = (
            "Run governed live pipeline to collect first activation evidence for: "
            + ", ".join(pending_evidence_sources)
        )
    elif activated_sources:
        overall_closure_status = "operationally_activated_for_scope"
        operator_next_step = "Credential-gated sources are operationally evidenced for this governed slice."
    else:
        overall_closure_status = "no_credential_gated_sources_in_scope"
        operator_next_step = "No credential-gated source activation is relevant for this governed slice."
    return {
        "total_sources": len(source_activation_readiness),
        "blocked_source_count": len(blocked_sources),
        "configured_ready_count": len(ready_sources),
        "status_counts": status_counts,
        "blocked_sources": blocked_sources,
        "configured_ready_sources": ready_sources,
        "blocked_applicable_country_count": len(blocked_countries),
        "blocked_applicable_countries": blocked_countries,
        "configured_ready_applicable_country_count": len(ready_countries),
        "configured_ready_applicable_countries": ready_countries,
        "closure_status_counts": closure_counts,
        "activated_with_live_evidence_count": len(activated_sources),
        "activated_with_live_evidence_sources": activated_sources,
        "external_blocker_count": len(external_blocked_sources),
        "external_blocker_sources": external_blocked_sources,
        "live_fetch_failed_count": len(failed_activation_sources),
        "live_fetch_failed_sources": failed_activation_sources,
        "pending_evidence_count": len(pending_evidence_sources),
        "pending_evidence_sources": pending_evidence_sources,
        "out_of_scope_count": len(scoped_out_sources),
        "out_of_scope_sources": scoped_out_sources,
        "overall_closure_status": overall_closure_status,
        "operator_next_step": operator_next_step,
    }


def build_source_coverage_read_model(
    sources: list[dict[str, object]],
    *,
    missing_sources: list[str] | None = None,
    source_activation_readiness: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    failed_sources = [str(source["source_id"]) for source in sources if source.get("status") == "failed"]
    degraded_sources = [str(source["source_id"]) for source in sources if source.get("status") != "success"]
    source_status_summary: dict[str, int] = {}
    for source in sources:
        status = str(source.get("status", "unknown"))
        source_status_summary[status] = source_status_summary.get(status, 0) + 1
    readiness_rows = _enrich_source_activation_readiness(
        list(source_activation_readiness or []),
        _source_status_by_source_id(sources),
    )
    return {
        "sources": sources,
        "failed_sources": failed_sources,
        "missing_sources": missing_sources or [],
        "degraded_sources": degraded_sources,
        "source_status_summary": source_status_summary,
        "source_activation_readiness": readiness_rows,
        "source_activation_readiness_summary": _build_source_activation_readiness_summary(readiness_rows),
    }
