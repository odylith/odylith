Status: Done
Created: 2026-04-28
Updated: 2026-04-28
Backlog: B-055

# Lifecycle Plan Dirty Overlap Summary Defaults

## Goal
Close `B-055` by proving lifecycle plans summarize dirty overlap by default
across install, reinstall, upgrade, and sync, while preserving verbose full
enumeration for debugging.

## Decisions
- Keep `summarize_dirty_overlap` in the shared runtime common layer so CLI and
  sync printers stay aligned.
- Default output shows count, area breakdown, representative paths, and hidden
  count.
- `--verbose` remains the explicit full-listing mode.
- Dirty-overlap classification distinguishes runtime state, generated surfaces,
  repo truth, managed guidance, and other paths.
- Add a small dedicated lifecycle test file instead of growing the oversized
  CLI or sync compatibility modules.

## Related Records
- Backlog: B-055.
- Parent workstream: B-048.
- Depends on: B-030, B-054.
- Casebook: CB-060.
- Target release: 0.1.12.

## Must-Ship
- [x] Prove install lifecycle plans use compact dirty-overlap output by default.
- [x] Prove reinstall lifecycle plans use the same compact output.
- [x] Prove upgrade lifecycle plans use the same compact output.
- [x] Prove verbose mode prints the full overlap list.
- [x] Prove area counts identify runtime state, generated surfaces, repo truth,
      managed guidance, and other paths.
- [x] Preserve sync plan compact/verbose coverage and large-overlap gate tests.

## Non-Goals
- Do not change which paths are considered dirty overlap.
- Do not hide representative path samples.
- Do not remove verbose full-listing mode.

## Impacted Areas
- [x] [dirty_overlap.py](/Users/freedom/code/odylith/src/odylith/runtime/common/dirty_overlap.py)
- [x] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [x] [test_lifecycle_dirty_overlap.py](/Users/freedom/code/odylith/tests/unit/test_lifecycle_dirty_overlap.py)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [x] [test_sync_cli_compat.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_cli_compat.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_lifecycle_dirty_overlap.py tests/unit/test_cli.py -k 'dirty_overlap or lifecycle_plan_condenses or lifecycle_plan_verbose' tests/unit/runtime/test_sync_cli_compat.py -k 'dirty_overlap or large_dirty_overlap'` passed with 9 tests and 187 deselected.
- [x] `python3 -m py_compile tests/unit/test_lifecycle_dirty_overlap.py` passed.

## Closure
- Closed on 2026-04-28 after compact lifecycle dirty-overlap output was proven
  across the install, reinstall, upgrade, and sync operator surfaces.
