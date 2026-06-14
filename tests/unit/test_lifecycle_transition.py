"""Unit tests for G4 lifecycle transition logic and CLI."""
import json
import pytest
from pathlib import Path

from siasa.readmodels.approval_lifecycle import (
    ApprovalLifecycleRecord,
    build_default_approval_lifecycle_record,
    transition_lifecycle_record,
    LifecycleTransitionError,
    ALLOWED_TRANSITIONS,
    load_approval_lifecycle_record,
    save_approval_lifecycle_record,
    build_approval_lifecycle_view_model,
)


# ─── transition_lifecycle_record ───────────────────────────────────────────────

def test_approve_from_pending():
    rec = build_default_approval_lifecycle_record()
    result = transition_lifecycle_record(rec, 'approve', actor='max', rationale='All good.')
    assert result.lifecycle_state == 'approved'
    assert result.decision_status == 'approved'
    assert result.disposition == 'approve'
    assert result.approval_rationale == 'All good.'
    assert result.decision_date_utc != ''
    assert len(result.audit_trail) == 2  # created + approve


def test_approve_with_conditions_from_pending():
    rec = build_default_approval_lifecycle_record()
    transition_lifecycle_record(rec, 'approve_with_conditions', conditions=['Fix cond A'])
    assert rec.lifecycle_state == 'approved_with_conditions'
    assert rec.approval_conditions == ['Fix cond A']


def test_defer_from_pending():
    rec = build_default_approval_lifecycle_record()
    transition_lifecycle_record(rec, 'defer', rationale='Not yet ready.')
    assert rec.lifecycle_state == 'deferred'
    assert rec.disposition == 'defer'


def test_reject_from_pending():
    rec = build_default_approval_lifecycle_record()
    transition_lifecycle_record(rec, 'reject', rationale='Blockers unresolved.')
    assert rec.lifecycle_state == 'rejected'
    assert rec.disposition == 'reject'


def test_distribute_from_approved():
    rec = build_default_approval_lifecycle_record()
    transition_lifecycle_record(rec, 'approve')
    transition_lifecycle_record(
        rec, 'distribute',
        recipients=['a@example.com'],
        bundle_artifacts=['release_package.html'],
        distribution_note='Sent via email.',
    )
    assert rec.lifecycle_state == 'distributed'
    assert rec.distributed is True
    assert rec.distribution_recipients == ['a@example.com']
    assert rec.distribution_bundle_artifacts == ['release_package.html']
    assert rec.distribution_record_note == 'Sent via email.'


def test_reviewer_id_and_role_set_on_approve():
    rec = build_default_approval_lifecycle_record()
    transition_lifecycle_record(rec, 'approve', reviewer_id='max', reviewer_role='project_lead')
    assert rec.reviewer_id == 'max'
    assert rec.reviewer_role == 'project_lead'


def test_audit_trail_grows_on_each_transition():
    rec = build_default_approval_lifecycle_record()
    assert len(rec.audit_trail) == 1
    transition_lifecycle_record(rec, 'approve')
    assert len(rec.audit_trail) == 2
    transition_lifecycle_record(rec, 'distribute')
    assert len(rec.audit_trail) == 3


def test_invalid_action_raises():
    rec = build_default_approval_lifecycle_record()
    with pytest.raises(LifecycleTransitionError, match='Unknown action'):
        transition_lifecycle_record(rec, 'publish')


def test_disallowed_transition_raises():
    rec = build_default_approval_lifecycle_record()
    transition_lifecycle_record(rec, 'approve')
    transition_lifecycle_record(rec, 'distribute')
    # distributed is terminal
    with pytest.raises(LifecycleTransitionError, match="not allowed"):
        transition_lifecycle_record(rec, 'approve')


def test_distribute_from_pending_raises():
    rec = build_default_approval_lifecycle_record()
    with pytest.raises(LifecycleTransitionError, match="not allowed"):
        transition_lifecycle_record(rec, 'distribute')


def test_deferred_can_transition_back_to_pending_signoff():
    """deferred -> pending_signoff is the allowed re-entry path."""
    rec = build_default_approval_lifecycle_record()
    transition_lifecycle_record(rec, 'defer')
    assert rec.lifecycle_state == 'deferred'
    allowed = ALLOWED_TRANSITIONS['deferred']
    assert 'pending_signoff' in allowed
    # direct approve from deferred is NOT allowed (must go via pending_signoff first)
    with pytest.raises(LifecycleTransitionError):
        transition_lifecycle_record(rec, 'approve')


def test_rejected_allows_re_initiation():
    rec = build_default_approval_lifecycle_record()
    transition_lifecycle_record(rec, 'reject')
    assert rec.lifecycle_state == 'rejected'
    allowed = ALLOWED_TRANSITIONS['rejected']
    assert 'pending_signoff' in allowed


def test_approve_with_conditions_then_approve():
    rec = build_default_approval_lifecycle_record()
    transition_lifecycle_record(rec, 'approve_with_conditions', conditions=['Cond A'])
    transition_lifecycle_record(rec, 'approve', rationale='Condition resolved.')
    assert rec.lifecycle_state == 'approved'
    assert rec.approval_conditions == ['Cond A']  # conditions preserved
    assert rec.approval_rationale == 'Condition resolved.'


# ─── view model reflects transition ───────────────────────────────────────────

def test_view_model_after_distribute_shows_lifecycle_complete():
    rec = build_default_approval_lifecycle_record()
    transition_lifecycle_record(rec, 'approve')
    transition_lifecycle_record(rec, 'distribute', recipients=['r@example.com'])
    vm = build_approval_lifecycle_view_model(rec)
    assert vm['lifecycle_status']['overall'] == 'lifecycle_complete'
    assert vm['lifecycle_status']['external_send_allowed'] is True
    assert vm['distributed'] is True


# ─── CLI integration tests ─────────────────────────────────────────────────────

def test_cli_status_on_missing_file_prints_pending(tmp_path, capsys):
    from scripts.lifecycle_transition import main
    rc = main(['status', '--record-path', str(tmp_path / 'missing.json')])
    assert rc == 0
    out = capsys.readouterr().out
    assert 'pending_signoff' in out


def test_cli_approve_creates_and_saves_record(tmp_path):
    from scripts.lifecycle_transition import main
    path = tmp_path / 'record.json'
    rc = main(['approve', '--record-path', str(path), '--reviewer-id', 'max', '--rationale', 'OK'])
    assert rc == 0
    assert path.exists()
    loaded = load_approval_lifecycle_record(path)
    assert loaded is not None
    assert loaded.lifecycle_state == 'approved'
    assert loaded.reviewer_id == 'max'


def test_cli_full_lifecycle(tmp_path):
    from scripts.lifecycle_transition import main
    path = tmp_path / 'record.json'
    main(['approve', '--record-path', str(path)])
    main(['distribute', '--record-path', str(path), '--recipients', 's@example.com'])
    loaded = load_approval_lifecycle_record(path)
    assert loaded.lifecycle_state == 'distributed'
    assert loaded.distributed is True


def test_cli_invalid_transition_returns_nonzero(tmp_path, capsys):
    from scripts.lifecycle_transition import main
    path = tmp_path / 'record.json'
    main(['approve', '--record-path', str(path)])
    main(['distribute', '--record-path', str(path)])
    # Now try to approve again from distributed (terminal)
    rc = main(['approve', '--record-path', str(path)])
    assert rc == 1
    out = capsys.readouterr().out
    assert 'ERROR' in out


def test_cli_dry_run_does_not_save(tmp_path):
    from scripts.lifecycle_transition import main
    path = tmp_path / 'record.json'
    main(['approve', '--record-path', str(path), '--dry-run'])
    # File should NOT exist because dry-run skips save
    assert not path.exists()


def test_cli_json_output(tmp_path, capsys):
    from scripts.lifecycle_transition import main
    path = tmp_path / 'record.json'
    main(['status', '--record-path', str(path), '--json'])
    out = capsys.readouterr().out
    # Should contain JSON output (status creates default view without saving)
    data = json.loads(out.split('\n', 1)[1])  # skip the [INFO] line
    assert data['lifecycle_state'] == 'pending_signoff'
