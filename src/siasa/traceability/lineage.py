from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineageRecord:
    source_id: str
    raw_record_id: str
    normalized_id: str
    feature_id: str
    domain_status_id: str
    multi_domain_status_id: str
    snapshot_id: str
    report_id: str | None = None



def build_lineage_record(
    source_id: str,
    raw_record_id: str,
    normalized_id: str,
    feature_id: str,
    domain_status_id: str,
    multi_domain_status_id: str,
    snapshot_id: str,
    report_id: str | None = None,
) -> LineageRecord:
    return LineageRecord(
        source_id=source_id,
        raw_record_id=raw_record_id,
        normalized_id=normalized_id,
        feature_id=feature_id,
        domain_status_id=domain_status_id,
        multi_domain_status_id=multi_domain_status_id,
        snapshot_id=snapshot_id,
        report_id=report_id,
    )
