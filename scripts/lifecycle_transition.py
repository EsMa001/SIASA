#!/usr/bin/env python3
"""
G4: Operator lifecycle-transition CLI for the SIASA approval-to-distribution record.

Usage:
  python scripts/lifecycle_transition.py approve   --record-path PATH [--reviewer-id ID] [--rationale TEXT]
  python scripts/lifecycle_transition.py approve_with_conditions --record-path PATH --conditions "Cond A" "Cond B"
  python scripts/lifecycle_transition.py defer     --record-path PATH [--rationale TEXT]
  python scripts/lifecycle_transition.py reject    --record-path PATH [--rationale TEXT]
  python scripts/lifecycle_transition.py distribute --record-path PATH [--recipients "a@b.com" "c@d.com"] [--note TEXT]
  python scripts/lifecycle_transition.py status    --record-path PATH

After a transition the record is saved back in place and a human-readable
summary is printed to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from siasa.readmodels.approval_lifecycle import (
    build_default_approval_lifecycle_record,
    build_approval_lifecycle_view_model,
    derive_lifecycle_status,
    load_approval_lifecycle_record,
    save_approval_lifecycle_record,
    transition_lifecycle_record,
    LifecycleTransitionError,
    ALLOWED_TRANSITIONS,
)


def _print_status(vm: dict) -> None:
    ls = vm.get('lifecycle_status', {})
    print('─' * 60)
    print(f"  Package:        {vm.get('package_id', '—')}")
    print(f"  Run ID:         {vm.get('package_run_id', '—')}")
    print(f"  Lifecycle state: {vm.get('lifecycle_state', '—')}")
    print(f"  Overall:        {ls.get('overall', '—')}")
    print(f"  Approved:       {ls.get('approved', False)}")
    print(f"  Distributed:    {ls.get('distributed', False)}")
    print(f"  Send allowed:   {ls.get('external_send_allowed', False)}")
    print(f"  Reviewer:       {vm.get('reviewer_id', '—') or '—'}")
    print(f"  Decision date:  {vm.get('decision_date_utc', '—') or '—'}")
    print(f"  Disposition:    {vm.get('disposition', '—') or '—'}")
    print(f"  Recipients:     {', '.join(vm.get('distribution_recipients', [])) or '—'}")
    print(f"  Next action:    {ls.get('operator_next_action', '—')}")
    print(f"  Audit entries:  {ls.get('audit_entry_count', 0)}")
    print('─' * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='SIASA G4 lifecycle transition operator CLI',
    )
    parser.add_argument(
        'action',
        choices=['approve', 'approve_with_conditions', 'defer', 'reject', 'distribute', 'status'],
        help='Lifecycle action to apply',
    )
    parser.add_argument(
        '--record-path',
        required=True,
        help='Path to approval_lifecycle_record.json',
    )
    parser.add_argument('--reviewer-id', default='', help='Reviewer name/handle')
    parser.add_argument('--reviewer-role', default='', help='Reviewer role (e.g. project_lead)')
    parser.add_argument('--rationale', default='', help='Decision rationale text')
    parser.add_argument(
        '--conditions',
        nargs='+',
        default=None,
        help='Approval conditions (for approve_with_conditions)',
    )
    parser.add_argument(
        '--recipients',
        nargs='+',
        default=None,
        help='Distribution recipient list (for distribute)',
    )
    parser.add_argument(
        '--bundle-artifacts',
        nargs='+',
        default=None,
        help='Bundle artifact file names included in distribution',
    )
    parser.add_argument('--note', default='', help='Distribution note (for distribute)')
    parser.add_argument('--actor', default='operator', help='Actor identity for audit trail')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--json', action='store_true', dest='json_out', help='Print result as JSON')

    args = parser.parse_args(argv)
    record_path = Path(args.record_path)

    # Load or create
    record = load_approval_lifecycle_record(record_path)
    if record is None:
        if args.action == 'status':
            print(f"[INFO] No record found at '{record_path}'. Creating a default pending view.")
            record = build_default_approval_lifecycle_record()
        else:
            print(f"[INFO] No record found at '{record_path}'. Starting a fresh pending record.")
            record = build_default_approval_lifecycle_record()

    if args.action == 'status':
        vm = build_approval_lifecycle_view_model(record)
        if args.json_out:
            print(json.dumps(vm, indent=2))
        else:
            _print_status(vm)
        return 0

    # Apply transition
    try:
        record = transition_lifecycle_record(
            record=record,
            action=args.action,
            actor=args.actor,
            reviewer_id=args.reviewer_id,
            reviewer_role=args.reviewer_role,
            rationale=args.rationale,
            conditions=args.conditions,
            recipients=args.recipients,
            bundle_artifacts=args.bundle_artifacts,
            distribution_note=args.note,
        )
    except LifecycleTransitionError as exc:
        print(f"[ERROR] {exc}")
        current = record.lifecycle_state
        allowed = ALLOWED_TRANSITIONS.get(current, [])
        print(f"  Current state: {current}")
        print(f"  Allowed actions from here: {allowed or 'none (terminal state)'}")
        return 1

    vm = build_approval_lifecycle_view_model(record)

    if args.dry_run:
        print("[DRY-RUN] Transition would be applied — not saved.")
        if args.json_out:
            print(json.dumps(vm, indent=2))
        else:
            _print_status(vm)
        return 0

    # Persist
    save_approval_lifecycle_record(record, record_path)
    print(f"[OK] Lifecycle record updated: {record_path}")

    if args.json_out:
        print(json.dumps(vm, indent=2))
    else:
        _print_status(vm)

    return 0


if __name__ == '__main__':
    sys.exit(main())
