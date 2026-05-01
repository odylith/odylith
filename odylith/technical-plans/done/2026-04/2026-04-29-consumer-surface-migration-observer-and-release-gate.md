Status: Done
Created: 2026-04-29
Updated: 2026-04-29
Backlog: B-140

# Consumer Surface Migration Observer And Release Gate

## Goal
Make consumer-lane migration assessment automatic for changed Odylith surfaces.
Before a release can close, changed guidance, skills, browser governance
surfaces, public docs, install-managed assets, and operator CLI contracts must
either have no consumer-visible impact or carry a completed Radar assessment
record for the target release.

## Decisions
- Implement the observer under `src/odylith/install/` so release migration
  gating, upgrade planning, and install-managed assets share one migration
  boundary instead of adding another formatter-only check.
- Watch consumer-visible surface classes, not every changed file. Tests,
  internal implementation modules outside install, and Radar authoring records
  are intentionally excluded unless they also move a shipped surface.
- Use explicit Radar markers shaped as
  `migration-observer:<version>:<surface>:<fingerprint>` so the release gate
  can verify target-specific and changed-path-content-specific migration
  assessment without fuzzy title matching.
- Treat generated dashboard refresh as reviewability evidence, not a release
  migration. Changed rendered contracts still require observer assessment.

## Must-Ship
- [x] Add `migration_observer.py` with path classification, marker extraction,
      JSON-ready reporting, and Git changed-path fallback.
- [x] Wire observer output into `ReleaseMigrationGateReport` and
      `odylith release migration-gate` stdout/JSON.
- [x] Update agent guidelines and skills so future surface changes require
      installed-consumer impact assessment.
- [x] Mirror changed guidance and skills into the shipped bundle assets.
- [x] Add B-140 as the completed migration-assessment record for the current
      0.1.12 surface classes.

## Non-Goals
- Do not make generated dashboard refresh a migration.
- Do not create a background daemon or automatic GitHub issue authoring path in
  this slice.
- Do not gate ordinary tests or internal implementation files that are not
  shipped consumer-visible surfaces.

## Impacted Areas
- [x] `src/odylith/install/migration_observer.py`
- [x] `src/odylith/install/migration_runtime.py`
- [x] `src/odylith/cli.py`
- [x] `odylith/agents-guidelines/UPGRADE_AND_RECOVERY.md`
- [x] `odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`
- [x] `odylith/skills/odylith-code-hygiene-guard/SKILL.md`
- [x] `odylith/skills/odylith-sync/SKILL.md`
- [x] `src/odylith/bundle/assets/odylith/` mirrors for the changed guidance
      and skills.

## Validation
- [x] `PYTHONPATH=src python3 -m py_compile src/odylith/install/migration_observer.py src/odylith/install/migration_runtime.py src/odylith/cli.py tests/unit/install/test_migration_runtime.py tests/unit/test_cli.py tests/unit/runtime/test_source_bundle_mirror.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_migration_runtime.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py::test_release_migration_gate_json_reports_registered_runtime tests/unit/runtime/test_source_bundle_mirror.py::test_repo_governance_docs_preserve_watcher_and_brief_contract_in_bundle_mirrors`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_codex_project_assets.py::test_live_claude_skill_shims_and_review_assets_match_bundle_content tests/unit/install/test_codex_project_assets.py::test_codex_skill_shims_stay_on_the_curated_command_surface`
- [x] `PYTHONPATH=src python3 -m odylith.cli release migration-gate --repo-root . --target-version 0.1.12 --json`
- [x] `PYTHONPATH=src python3 -m odylith.cli release migration-gate --repo-root . --target-version 0.1.12`
- [x] `git diff --check`

## Closure
- Closed on 2026-04-29 after the source release gate detected five surface
  migration-observer needs and accepted B-140 as the target-specific completed
  assessment record.
- Maintained on 2026-04-30 after the v0.1.12 recovery-release sweep changed
  public docs/release guidance, browser surfaces, and install-managed assets
  again. B-140 now carries the new target-specific markers and an explicit
  upgrade assessment for those fingerprints, keeping `release migration-gate`
  fail-closed without creating a duplicate migration-observer workstream.
