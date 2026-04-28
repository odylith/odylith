Status: Done
Created: 2026-04-27
Updated: 2026-04-27
Backlog: B-050

# Repair And Reinstall Partial Runtime Convergence

## Goal
Make supported recovery commands converge after a partial runtime staging or
replacement failure. Repeated `doctor --repair` and `reinstall --latest` should
move a repo toward one valid pinned runtime state without requiring manual
deletion of leftover `.backup-*`, stage directories, or wrapper-shaped runtime
outputs.

## Decisions
- Keep cleanup target-version scoped under `.odylith/runtime/versions/`.
- Match residue names literally instead of feeding a release version into glob
  expansion.
- Remove only hidden target-version backup and staging residue:
  `.<version>.backup-*`, `.<version>.stage-*`, and legacy
  `.<version>.staging-*`.
- Let managed runtime restaging replace stale visible target-version wrapper
  outputs through the existing atomic backup/replace path.
- Preserve unrelated runtime versions, unrelated hidden residue, rollback
  history, and operator-owned runtime roots.

## Related Records
- Backlog: B-050.
- Casebook: CB-055.
- Parent workstream: B-048.
- Related diagrams: D-018, D-019.
- Target release: 0.1.12.

## Must-Ship
- [x] Centralize runtime tree residue policy in
      [runtime_tree_policy.py](/Users/freedom/code/odylith/src/odylith/install/runtime_tree_policy.py).
- [x] Invoke target-version residue cleanup before wrapped runtime creation,
      runtime repair selection, and managed release restaging.
- [x] Restage untrusted or wrapper-shaped target roots through the atomic
      runtime replacement path.
- [x] Prove cleanup is literal, narrow, and target-version scoped.
- [x] Prove repeated repair and reinstall converge after stale backup and
      staging residue.
- [x] Prove stale wrapper outputs are replaced by a managed runtime without
      deleting unrelated runtime roots.

## Non-Goals
- Do not delete arbitrary runtime versions.
- Do not clean unrelated residue from other versions.
- Do not change rollback scope or generated dashboard reviewability.
- Do not introduce a new operator flag for repair cleanup.

## Impacted Areas
- [x] [runtime_tree_policy.py](/Users/freedom/code/odylith/src/odylith/install/runtime_tree_policy.py)
- [x] [runtime.py](/Users/freedom/code/odylith/src/odylith/install/runtime.py)
- [x] [test_runtime.py](/Users/freedom/code/odylith/tests/unit/install/test_runtime.py)
- [x] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_runtime.py -k 'cleanup_runtime_versions_residue or install_release_runtime_cleans_stale_backup or install_release_runtime_replaces_stale_wrapper or doctor_runtime_repair_converges'` passed with 5 tests.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/install/test_manager.py -k 'reinstall_install_converges_repeatedly_with_stale_target_residue or reinstall_install_repairs_same_version_runtime_when_upgrade_requires_doctor'` passed with 2 tests.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_runtime.py tests/integration/install/test_manager.py` passed with 124 tests.
- [x] `PYTHONPATH=src python3 -m py_compile src/odylith/install/runtime_tree_policy.py src/odylith/install/runtime.py src/odylith/install/manager.py tests/unit/install/test_runtime.py tests/integration/install/test_manager.py` passed.
- [x] `./.odylith/bin/odylith casebook validate --repo-root .` passed with
      134 records checked.
- [x] `./.odylith/bin/odylith validate backlog-contract --repo-root .` passed
      with 127 ideas checked.
- [x] `./.odylith/bin/odylith validate plan-workstream-binding --repo-root .`,
      `./.odylith/bin/odylith validate plan-traceability --repo-root .`, and
      `./.odylith/bin/odylith validate plan-risk-mitigation --repo-root .`
      passed.
- [x] `./.odylith/bin/odylith validate component-registry --repo-root .`
      passed with 27 components and 386 events.
- [x] `git diff --check` passed.

## Closure
- Closed on 2026-04-27 after residue cleanup was made literal and
  target-version scoped, stale wrapper replacement was covered, repeated repair
  and reinstall convergence was proven, and CB-055 was closed.

## Open Questions
- [x] Whether residue cleanup should emit install-ledger telemetry. It remains
      deferred; CB-134 and upgrade reporting own broader reviewability and
      operator audit reports.
