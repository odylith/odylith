Status: Done

Created: 2026-04-12

Updated: 2026-04-12

Backlog: B-077

Goal: Normalize external wait state, emit semantic receipts, and default
follow-up execution to resume instead of restarting from scratch.

Assumptions:
- The first adapter set is intentionally bounded to proven product surfaces.
- Sparse proof snapshots still need to preserve resumable handles.

Constraints:
- Receipt and wait posture must survive packet compaction and shared runtime
  export.
- New wait-state fields cannot reopen sync churn or stale summary fallback.

Related Bugs:
- No related bug found.

## Learnings
- [x] External work only becomes trustworthy when wait state is semantic, not
      just `running`.
- [x] Resume handles are most useful when sparse or partial snapshots still
      keep them alive.

## Must-Ship
- [x] Add semantic receipts and resume-handle helpers.
- [x] Normalize the first supported external wait states through the shared
      execution-governance adapter.
- [x] Preserve wait detail and resume tokens through packet, shell, Compass,
      router, and remediator consumers.

## Success Criteria
- [x] Execution-governance summaries show semantic wait state and resumability
      from one shared snapshot.
- [x] Rerun posture prefers resumption when a live receipt already exists.

## Impacted Areas
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/receipts.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/receipts.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_surface_governance.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_surface_governance.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/reasoning/remediator.py](/Users/freedom/code/odylith/src/odylith/runtime/reasoning/remediator.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_governance.py tests/unit/runtime/test_remediator.py tests/unit/runtime/test_odylith_runtime_surface_summary.py`
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --force --impact-mode full`

## Current Outcome
- [x] The engine now exposes semantic wait state, receipt posture, and resume
      handles across the shared execution-governance path.
