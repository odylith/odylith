Status: Done
Created: 2026-04-28
Updated: 2026-04-28
Backlog: B-053

# Legacy Radar Index Normalization Before Sync Validation

## Goal
Close `B-053` by making migrated Radar source truth self-bridge before strict
sync validation, so old backlog indexes do not block the first governed sync on
mechanically repairable rationale or schema drift.

## Decisions
- Keep the compatibility bridge in
  `legacy_backlog_normalization.py` as a focused Radar-source normalizer.
- Preserve authored rationale lines and only append missing required bullets.
- Strip legacy `impacted_lanes` metadata from idea specs and table headers.
- Repair manual-priority override rationale with a dated review checkpoint.
- Create a missing `## Reorder Rationale Log` section for very old indexes
  instead of raising a formatter exception.
- Keep future Radar schema upgrades explicit; this bridge is not a generic
  Markdown repair engine.

## Related Records
- Backlog: B-053.
- Parent workstream: B-048.
- Casebook: CB-058.
- Blocks cleared for: B-054.
- Target release: 0.1.12.

## Must-Ship
- [x] Normalize legacy active, execution, parked, and finished table schemas.
- [x] Backfill missing rationale bullets while preserving authored prose.
- [x] Repair manual-override ranking basis and review checkpoint text.
- [x] Handle a missing reorder-rationale section safely.
- [x] Prove normalization is idempotent after the first bridge pass.
- [x] Wire sync and dashboard refresh through the same normalizer.

## Non-Goals
- Do not reorder backlog items.
- Do not rewrite complete authored rationale.
- Do not broaden sync preflight into a general governance auto-repair lane.
- Do not grow the oversized sync or backlog-validation modules for this edge
  case.

## Impacted Areas
- [x] [legacy_backlog_normalization.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/legacy_backlog_normalization.py)
- [x] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [x] [test_legacy_backlog_normalization.py](/Users/freedom/code/odylith/tests/unit/runtime/test_legacy_backlog_normalization.py)
- [x] [test_sync_cli_compat.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_cli_compat.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_legacy_backlog_normalization.py tests/unit/runtime/test_sync_cli_compat.py -k 'legacy_backlog or legacy_radar or normalizes_legacy or auto_normalizes or backlog_contract_blockers'` passed with 9 tests and 57 deselected.
- [x] `python3 -m py_compile src/odylith/runtime/governance/legacy_backlog_normalization.py tests/unit/runtime/test_legacy_backlog_normalization.py` passed.

## Closure
- Closed on 2026-04-28 after the legacy Radar bridge covered missing rationale
  bullets, legacy schema fields, missing rationale sections, and idempotent
  second-run behavior before strict sync validation.
