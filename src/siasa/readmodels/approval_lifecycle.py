"""
G4: Approval-to-distribution release lifecycle record.

Governs the explicit lifecycle transition from:
  pending_signoff -> approved -> distributed (or: deferred / rejected)

This module provides:
- ApprovalLifecycleRecord dataclass and serialisation helpers
- build_default_approval_lifecycle_record(): creates a fresh pending record
- load_approval_lifecycle_record(): loads from JSON artifact if present
- derive_lifecycle_status(): derives machine-readable lifecycle_status from record state
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

UTC = timezone.utc

# Valid lifecycle states (ordered)
LIFECYCLE_STATES = [
    'pending_signoff',
    'approved',
    'approved_with_conditions',
    'distributed',
    'deferred',
    'rejected',
]

# Valid disposition values
DISPOSITION_OPTIONS = ['approve', 'approve_with_conditions', 'defer', 'reject']


@dataclass
class ApprovalLifecycleRecord:
    """Persistent governed approval-to-distribution lifecycle record for one release packet."""

    # Identity
    package_id: str = ''               # e.g. 'release-2026-06-14'
    package_run_id: str = ''           # run_id that generated the governing bundle

    # Approval state
    lifecycle_state: str = 'pending_signoff'  # one of LIFECYCLE_STATES
    decision_status: str = 'pending_signoff'  # alias for GUI/checklist compat
    reviewer_role: str = ''
    reviewer_id: str = ''              # optional: reviewer name or handle
    decision_date_utc: str = ''        # ISO timestamp when decision was recorded
    disposition: str = ''              # one of DISPOSITION_OPTIONS or ''
    approval_conditions: list = field(default_factory=list)   # non-empty for approve_with_conditions
    approval_rationale: str = ''

    # Distribution state
    distributed: bool = False
    distribution_date_utc: str = ''
    distribution_recipients: list = field(default_factory=list)
    distribution_bundle_artifacts: list = field(default_factory=list)
    distribution_record_note: str = ''

    # Lifecycle timestamps
    created_at_utc: str = ''
    last_updated_utc: str = ''

    # Audit trail (list of dicts with timestamp/action/actor/note)
    audit_trail: list = field(default_factory=list)


def build_default_approval_lifecycle_record(
    package_id: str = '',
    package_run_id: str = '',
    reviewer_role: str = 'project_lead',
) -> ApprovalLifecycleRecord:
    """Create a fresh pending-signoff lifecycle record."""
    now = datetime.now(UTC).isoformat()
    return ApprovalLifecycleRecord(
        package_id=package_id or f'release-{datetime.now(UTC).strftime("%Y-%m-%d")}',
        package_run_id=package_run_id,
        lifecycle_state='pending_signoff',
        decision_status='pending_signoff',
        reviewer_role=reviewer_role,
        created_at_utc=now,
        last_updated_utc=now,
        audit_trail=[
            {
                'timestamp_utc': now,
                'action': 'record_created',
                'actor': 'system',
                'note': 'Approval lifecycle record initialized.',
            }
        ],
    )


def derive_lifecycle_status(record: ApprovalLifecycleRecord) -> dict:
    """Derive a machine-readable lifecycle status summary from the record."""
    state = record.lifecycle_state

    # Compute overall readiness signal
    if state == 'distributed':
        overall = 'lifecycle_complete'
        external_send_allowed = True
        operator_next_action = 'Lifecycle is complete. Archive this record.'
    elif state in ('approved', 'approved_with_conditions') and not record.distributed:
        overall = 'approved_pending_distribution'
        external_send_allowed = (state == 'approved')
        operator_next_action = (
            'Distribute canonical release package and record recipients.'
            if state == 'approved'
            else 'Resolve approval conditions, then distribute.'
        )
    elif state == 'pending_signoff':
        overall = 'awaiting_reviewer_decision'
        external_send_allowed = False
        operator_next_action = 'Obtain explicit reviewer sign-off before distribution.'
    elif state == 'deferred':
        overall = 'distribution_deferred'
        external_send_allowed = False
        operator_next_action = 'Re-trigger review when conditions are resolved.'
    elif state == 'rejected':
        overall = 'distribution_rejected'
        external_send_allowed = False
        operator_next_action = 'Address rejection rationale and re-initiate review cycle.'
    else:
        overall = 'lifecycle_status_unknown'
        external_send_allowed = False
        operator_next_action = 'Check lifecycle_state value.'

    return {
        'lifecycle_state': state,
        'overall': overall,
        'external_send_allowed': external_send_allowed,
        'operator_next_action': operator_next_action,
        'approved': state in ('approved', 'approved_with_conditions', 'distributed'),
        'distributed': record.distributed,
        'has_conditions': bool(record.approval_conditions),
        'has_distribution_recipients': bool(record.distribution_recipients),
        'audit_entry_count': len(record.audit_trail),
    }


def load_approval_lifecycle_record(artifact_path: Path) -> Optional[ApprovalLifecycleRecord]:
    """Load a persisted approval lifecycle record from JSON. Returns None if missing/invalid."""
    if not artifact_path.exists():
        return None
    try:
        data = json.loads(artifact_path.read_text(encoding='utf-8'))
        rec = ApprovalLifecycleRecord(**{
            k: v for k, v in data.items()
            if k in ApprovalLifecycleRecord.__dataclass_fields__
        })
        return rec
    except Exception:
        return None


def save_approval_lifecycle_record(record: ApprovalLifecycleRecord, artifact_path: Path) -> None:
    """Persist a lifecycle record as JSON."""
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(asdict(record), indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


def build_approval_lifecycle_view_model(
    record: Optional[ApprovalLifecycleRecord],
    package_run_id: str = '',
) -> dict:
    """Build a GUI/readmodel view-model dict from the current lifecycle record."""
    if record is None:
        record = build_default_approval_lifecycle_record(package_run_id=package_run_id)
    status = derive_lifecycle_status(record)
    return {
        'package_id': record.package_id,
        'package_run_id': record.package_run_id,
        'lifecycle_state': record.lifecycle_state,
        'decision_status': record.decision_status,
        'reviewer_role': record.reviewer_role,
        'reviewer_id': record.reviewer_id,
        'decision_date_utc': record.decision_date_utc,
        'disposition': record.disposition,
        'approval_conditions': record.approval_conditions,
        'approval_rationale': record.approval_rationale,
        'distributed': record.distributed,
        'distribution_date_utc': record.distribution_date_utc,
        'distribution_recipients': record.distribution_recipients,
        'distribution_bundle_artifacts': record.distribution_bundle_artifacts,
        'distribution_record_note': record.distribution_record_note,
        'created_at_utc': record.created_at_utc,
        'last_updated_utc': record.last_updated_utc,
        'audit_trail': record.audit_trail,
        'lifecycle_status': status,
    }
