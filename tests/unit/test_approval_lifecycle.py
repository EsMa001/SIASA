"""Unit tests for G4 approval lifecycle record module."""
import json
import pytest
from pathlib import Path

from siasa.readmodels.approval_lifecycle import (
    ApprovalLifecycleRecord,
    build_default_approval_lifecycle_record,
    derive_lifecycle_status,
    load_approval_lifecycle_record,
    save_approval_lifecycle_record,
    build_approval_lifecycle_view_model,
    LIFECYCLE_STATES,
    DISPOSITION_OPTIONS,
)


# --- build_default_approval_lifecycle_record ---

def test_default_record_has_pending_signoff_state():
    rec = build_default_approval_lifecycle_record()
    assert rec.lifecycle_state == 'pending_signoff'
    assert rec.decision_status == 'pending_signoff'


def test_default_record_populates_created_at():
    rec = build_default_approval_lifecycle_record()
    assert rec.created_at_utc != ''
    assert 'T' in rec.created_at_utc  # ISO timestamp


def test_default_record_has_audit_trail_entry():
    rec = build_default_approval_lifecycle_record()
    assert len(rec.audit_trail) == 1
    assert rec.audit_trail[0]['action'] == 'record_created'


def test_default_record_package_id_generated_when_empty():
    rec = build_default_approval_lifecycle_record()
    assert rec.package_id.startswith('release-')


def test_default_record_custom_package_id():
    rec = build_default_approval_lifecycle_record(package_id='release-2026-06-14')
    assert rec.package_id == 'release-2026-06-14'


def test_default_record_reviewer_role_default():
    rec = build_default_approval_lifecycle_record()
    assert rec.reviewer_role == 'project_lead'


def test_default_record_not_distributed():
    rec = build_default_approval_lifecycle_record()
    assert rec.distributed is False
    assert rec.distribution_recipients == []


# --- derive_lifecycle_status ---

def test_status_pending_signoff():
    rec = build_default_approval_lifecycle_record()
    status = derive_lifecycle_status(rec)
    assert status['overall'] == 'awaiting_reviewer_decision'
    assert status['external_send_allowed'] is False
    assert status['approved'] is False
    assert status['distributed'] is False


def test_status_approved():
    rec = build_default_approval_lifecycle_record()
    rec.lifecycle_state = 'approved'
    rec.decision_status = 'approved'
    status = derive_lifecycle_status(rec)
    assert status['overall'] == 'approved_pending_distribution'
    assert status['external_send_allowed'] is True
    assert status['approved'] is True
    assert status['distributed'] is False


def test_status_approved_with_conditions():
    rec = build_default_approval_lifecycle_record()
    rec.lifecycle_state = 'approved_with_conditions'
    rec.approval_conditions = ['Condition A']
    status = derive_lifecycle_status(rec)
    assert status['overall'] == 'approved_pending_distribution'
    assert status['external_send_allowed'] is False  # conditions block direct send
    assert status['has_conditions'] is True


def test_status_distributed():
    rec = build_default_approval_lifecycle_record()
    rec.lifecycle_state = 'distributed'
    rec.distributed = True
    rec.distribution_recipients = ['stakeholder@example.com']
    status = derive_lifecycle_status(rec)
    assert status['overall'] == 'lifecycle_complete'
    assert status['external_send_allowed'] is True
    assert status['distributed'] is True
    assert status['has_distribution_recipients'] is True


def test_status_deferred():
    rec = build_default_approval_lifecycle_record()
    rec.lifecycle_state = 'deferred'
    status = derive_lifecycle_status(rec)
    assert status['overall'] == 'distribution_deferred'
    assert status['external_send_allowed'] is False


def test_status_rejected():
    rec = build_default_approval_lifecycle_record()
    rec.lifecycle_state = 'rejected'
    status = derive_lifecycle_status(rec)
    assert status['overall'] == 'distribution_rejected'
    assert status['external_send_allowed'] is False


# --- persist / load ---

def test_save_and_load_roundtrip(tmp_path):
    rec = build_default_approval_lifecycle_record(
        package_id='release-2026-06-14',
        package_run_id='RUN-LIVE-TEST-001',
    )
    path = tmp_path / 'approval_lifecycle_record.json'
    save_approval_lifecycle_record(rec, path)
    assert path.exists()
    loaded = load_approval_lifecycle_record(path)
    assert loaded is not None
    assert loaded.package_id == 'release-2026-06-14'
    assert loaded.package_run_id == 'RUN-LIVE-TEST-001'
    assert loaded.lifecycle_state == 'pending_signoff'
    assert len(loaded.audit_trail) == 1


def test_load_missing_file_returns_none(tmp_path):
    path = tmp_path / 'does_not_exist.json'
    result = load_approval_lifecycle_record(path)
    assert result is None


def test_load_malformed_json_returns_none(tmp_path):
    path = tmp_path / 'bad.json'
    path.write_text('{not valid json', encoding='utf-8')
    result = load_approval_lifecycle_record(path)
    assert result is None


def test_save_creates_parent_dirs(tmp_path):
    rec = build_default_approval_lifecycle_record()
    path = tmp_path / 'subdir' / 'nested' / 'record.json'
    save_approval_lifecycle_record(rec, path)
    assert path.exists()


def test_saved_json_is_valid(tmp_path):
    rec = build_default_approval_lifecycle_record()
    path = tmp_path / 'record.json'
    save_approval_lifecycle_record(rec, path)
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['lifecycle_state'] == 'pending_signoff'
    assert 'audit_trail' in data


# --- build_approval_lifecycle_view_model ---

def test_view_model_from_none_returns_pending_defaults():
    vm = build_approval_lifecycle_view_model(None, package_run_id='RUN-001')
    assert vm['lifecycle_state'] == 'pending_signoff'
    assert vm['lifecycle_status']['overall'] == 'awaiting_reviewer_decision'
    assert vm['package_run_id'] == 'RUN-001'


def test_view_model_from_approved_record():
    rec = build_default_approval_lifecycle_record()
    rec.lifecycle_state = 'approved'
    rec.decision_status = 'approved'
    rec.disposition = 'approve'
    rec.reviewer_id = 'max'
    vm = build_approval_lifecycle_view_model(rec)
    assert vm['lifecycle_state'] == 'approved'
    assert vm['lifecycle_status']['approved'] is True
    assert vm['reviewer_id'] == 'max'


def test_view_model_includes_audit_trail():
    rec = build_default_approval_lifecycle_record()
    vm = build_approval_lifecycle_view_model(rec)
    assert isinstance(vm['audit_trail'], list)
    assert len(vm['audit_trail']) == 1


# --- constants ---

def test_lifecycle_states_coverage():
    assert 'pending_signoff' in LIFECYCLE_STATES
    assert 'approved' in LIFECYCLE_STATES
    assert 'distributed' in LIFECYCLE_STATES
    assert 'rejected' in LIFECYCLE_STATES


def test_disposition_options_coverage():
    assert 'approve' in DISPOSITION_OPTIONS
    assert 'reject' in DISPOSITION_OPTIONS
    assert 'defer' in DISPOSITION_OPTIONS
