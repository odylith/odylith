Status: Done
Created: 2026-04-28
Updated: 2026-04-28
Backlog: B-054

# Sync Failure Summary Dedup And Next-Action Routing

## Goal
Close `B-054` by proving sync failure output stays compact, keeps useful file
anchors, and routes operators to a next different action instead of telling
them to repeat the same failed sync.

## Decisions
- Keep the implementation in the existing sync failure helpers; this closeout
  adds focused proof instead of another rewrite.
- Count exact duplicate backlog-contract messages and suppress the long tail
  with a clear hidden-count line.
- Route backlog-contract next actions by failure class: metadata/status/plan
  binding, rationale completion, index table repair, or fallback strict check.
- Preserve execution-step-specific `next_command_on_failure` for repair-class
  failures so runtime repair can point to `odylith doctor --repair`.
- Avoid adding more tests to the oversized `test_sync_cli_compat.py`; use a new
  small failure-summary test file for the hard contract.

## Related Records
- Backlog: B-054.
- Parent workstream: B-048.
- Depends on: B-053.
- Casebook: CB-059.
- Target release: 0.1.12.

## Must-Ship
- [x] Prove duplicate sync blockers collapse with counts.
- [x] Prove long-tail suppression is explicit.
- [x] Prove next actions differ by backlog failure class.
- [x] Prove repair-class step failures use their own repair command.
- [x] Reconcile B-054 and CB-059 governance state.

## Non-Goals
- Do not change validation semantics.
- Do not write a full sync failure report file in this slice.
- Do not inflate oversized sync compatibility tests for helper-level behavior.

## Impacted Areas
- [x] [legacy_backlog_normalization.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/legacy_backlog_normalization.py)
- [x] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [x] [test_sync_failure_summary.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_failure_summary.py)
- [x] [test_sync_cli_compat.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_cli_compat.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_sync_failure_summary.py tests/unit/runtime/test_legacy_backlog_normalization.py tests/unit/runtime/test_sync_cli_compat.py -k 'sync_failure or backlog_summary or backlog_next_action or sync_preflight_summarizes'` passed with 5 tests and 64 deselected.
- [x] `python3 -m py_compile tests/unit/runtime/test_sync_failure_summary.py` passed.

## Closure
- Closed on 2026-04-28 after the sync failure summary behavior was proven for
  duplicate collapse, representative anchors, class-aware next actions, and
  repair-command routing.
