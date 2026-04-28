Status: Done
Created: 2026-04-28
Updated: 2026-04-28
Backlog: B-052

# Legacy Migration Stale Reference Audit

## Goal
Close `B-052` by making legacy Odyssey migration honest about stale references
that remain in repo-owned source truth after managed roots move to Odylith.

## Decisions
- Keep the audit non-destructive: it reports stale references and never rewrites
  user docs or governed prose.
- Scan tracked text files when Git metadata exists; use a conservative fallback
  text scan when it does not.
- Exclude managed runtime, cache, lock, log, migration-report, and migration-ledger
  trees.
- Exclude generated dashboard surfaces, root temp clones, vendor trees, build
  outputs, and common local tool caches so the report leads with source truth.
- Keep source truth in scope, including user docs, Radar source, Casebook bugs,
  Registry source, and guidance Markdown.

## Related Records
- Backlog: B-052.
- Parent workstream: B-048.
- Casebook: CB-057.
- Related diagrams: D-018, D-019.
- Target release: 0.1.12.

## Must-Ship
- [x] Persist a stale-reference report under `.odylith/state/migration/`.
- [x] Print a compact migration CLI summary with hit/file counts and sample
      paths.
- [x] Prove user docs are reported but not rewritten.
- [x] Exclude generated surfaces and non-source sludge from the report.
- [x] Preserve source-truth references so operators know what still needs
      manual cleanup.

## Non-Goals
- Do not rewrite tracked user documents automatically.
- Do not treat intentionally historical references as errors.
- Do not scan generated dashboard payloads as primary migration evidence.

## Impacted Areas
- [x] [migration_audit.py](/Users/freedom/code/odylith/src/odylith/install/migration_audit.py)
- [x] [legacy_install_migration.py](/Users/freedom/code/odylith/src/odylith/install/legacy_install_migration.py)
- [x] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [test_migration_audit.py](/Users/freedom/code/odylith/tests/unit/install/test_migration_audit.py)
- [x] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_migration_audit.py tests/integration/install/test_manager.py -k 'legacy_install or migration_audit or stale_reference'` passed with 6 tests and 79 deselected.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_migration_audit.py tests/integration/install/test_manager.py tests/unit/test_cli.py -k 'migrate_legacy_install or stale_reference or migration_audit'` passed with 7 tests and 211 deselected.
- [x] `python3 -m py_compile src/odylith/install/migration_audit.py tests/unit/install/test_migration_audit.py` passed.

## Closure
- Closed on 2026-04-28 after the migration audit was proven across direct
  audit, install migration, and CLI summary paths, then hardened to suppress
  generated-surface and repository-sludge noise without hiding source-truth
  references.
