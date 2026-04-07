Status: In progress

Created: 2026-04-06

Updated: 2026-04-06

Backlog: B-048

Goal: Turn the concrete April 6 downstream migration feedback for Odylith 0.1.8
into one bounded release wave that hardens managed-runtime trust on macOS,
makes repair and reinstall converge after partial failure, unblocks legacy
Radar-backed sync, and quiets operator output without widening trust or
rewriting user-owned docs.

Assumptions:
- `B-033` remains the historical release umbrella even though this slice now
  targets `0.1.8`.
- One new active plan bound to `B-048` is preferable to scattering these fixes
  across multiple active plan files.
- Child workstreams `B-049` through `B-056` can execute under this umbrella
  plan instead of each requiring their own plan binding.
- macOS metadata noise should be ignored narrowly: `.DS_Store` and AppleDouble
  `._*` only.
- Stale `odyssey` references should be audited and reported, not rewritten
  automatically.

Constraints:
- Do not widen trust by ignoring arbitrary hidden files.
- Do not revert or rewrite user-owned documentation during stale-reference
  audit.
- Do not keep adding logic directly into oversized files when a small helper
  extraction can bound the change.
- Keep `sync` fail-closed on real contract violations after the legacy
  normalization bridge runs once.

Reversibility: The new governance records are additive. Runtime, migration,
and CLI behavior changes should be forward-fix but kept modular enough to back
out independently if a narrower regression appears.

Boundary Conditions:
- Scope includes source-truth governance updates, runtime-tree policy helpers,
  repair cleanup, runtime-status reporting, stale-reference auditing, Radar
  normalization before sync validation, sync summary cleanup, lifecycle-plan
  verbosity defaults, verifier warning handling, and 0.1.8 release-note
  refresh.
- Scope excludes historical umbrella renaming, broad user-doc rewrites, and
  any relaxation of the managed-runtime trust boundary beyond explicit OS
  metadata noise.

Related Bugs:
- [2026-04-06-macos-runtime-metadata-files-break-managed-runtime-trust-validation.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-macos-runtime-metadata-files-break-managed-runtime-trust-validation.md)
- [2026-04-06-repair-and-reinstall-do-not-converge-after-partial-runtime-failure.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-repair-and-reinstall-do-not-converge-after-partial-runtime-failure.md)
- [2026-04-06-doctor-and-version-disagree-on-wrapped-runtime-trust-degradation.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-doctor-and-version-disagree-on-wrapped-runtime-trust-degradation.md)
- [2026-04-06-legacy-migration-omits-stale-odyssey-reference-audit.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-legacy-migration-omits-stale-odyssey-reference-audit.md)
- [2026-04-06-legacy-radar-index-is-not-normalized-before-sync-validation.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-legacy-radar-index-is-not-normalized-before-sync-validation.md)
- [2026-04-06-sync-failure-summary-repeats-verbose-output-and-stale-next-action.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-sync-failure-summary-repeats-verbose-output-and-stale-next-action.md)
- [2026-04-06-lifecycle-plans-print-full-dirty-overlap-by-default.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-lifecycle-plans-print-full-dirty-overlap-by-default.md)
- [2026-04-06-successful-trust-bootstrap-still-prints-scary-non-fatal-warnings.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-successful-trust-bootstrap-still-prints-scary-non-fatal-warnings.md)
- [2026-03-28-first-install-and-same-version-upgrade-mutate-live-runtime-before-fail-closed-proof.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-first-install-and-same-version-upgrade-mutate-live-runtime-before-fail-closed-proof.md)
- [2026-03-28-release-download-cache-and-runtime-restage-lose-atomicity-on-failure.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-release-download-cache-and-runtime-restage-lose-atomicity-on-failure.md)
- [2026-03-31-product-repo-doctor-repair-rewrites-root-agents-to-stale-managed-block.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-31-product-repo-doctor-repair-rewrites-root-agents-to-stale-managed-block.md)
- [2026-03-31-radar-backlog-index-uses-absolute-workstation-links-and-breaks-clean-checkout-proof.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-31-radar-backlog-index-uses-absolute-workstation-links-and-breaks-clean-checkout-proof.md)
- [2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md)

## Must-Ship
- [ ] Add `B-048` through `B-056` and `CB-054` through `CB-061` to source truth.
- [ ] Extract a runtime-tree policy helper that ignores only `.DS_Store` and
      AppleDouble `._*`.
- [ ] Make runtime replacement, repair, and reinstall converge after
      partial-failure residue and `.backup-*` leftovers.
- [ ] Unify runtime-source classification so `version` and `doctor` agree on
      trust-degraded wrapped-runtime posture.
- [ ] Add post-migration stale-reference audit plus repo-local report
      persistence.
- [ ] Normalize legacy Radar backlog rationale before strict sync validation.
- [ ] Deduplicate sync failure summaries and route the next action by failure
      class.
- [ ] Collapse `dirty_overlap` output by default and expose `--verbose`.
- [ ] Suppress or translate benign verifier warnings and print an explicit
      verification-success line.
- [ ] Refresh the 0.1.8 authored release note to describe the migration and
      trust hardening.

## Should-Ship
- [ ] Reuse one shared helper for runtime-status explanation across CLI and
      install manager paths.
- [ ] Save stale-reference audit output under `.odylith/state/migration/` in a
      deterministic text format.
- [ ] Add direct CLI smoke coverage for `version`, `doctor`, install/reinstall,
      and sync after the focused suites pass.

## Defer
- [ ] Do not rename `B-033` or rewrite older release governance titles.
- [ ] Do not broaden the OS-noise ignore list beyond the explicit macOS files.
- [ ] Do not automatically rewrite user docs that still reference `odyssey`.

## Success Criteria
- [ ] macOS metadata noise no longer breaks trusted runtime validation.
- [ ] repeated repair and reinstall converge after partial runtime failure.
- [ ] `version` and `doctor` describe trust-degraded wrapped runtime
      consistently.
- [ ] migration emits a stale-reference audit and saves a repo-local report.
- [ ] sync normalizes legacy Radar rationale once before strict validation.
- [ ] remaining sync failures show deduped top-N summaries and distinct next
      actions.
- [ ] default lifecycle plans summarize dirty overlap while `--verbose`
      restores the full listing.
- [ ] successful verifier runs print a clear success line without scary benign
      warning spam.

## Non-Goals
- [ ] Renaming old release wave records.
- [ ] Rewriting user-owned documentation during migration.
- [ ] Relaxing real runtime trust drift into warning-only behavior.

## Impacted Areas
- [ ] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [ ] [runtime.py](/Users/freedom/code/odylith/src/odylith/install/runtime.py)
- [ ] [runtime_integrity.py](/Users/freedom/code/odylith/src/odylith/install/runtime_integrity.py)
- [ ] [release_assets.py](/Users/freedom/code/odylith/src/odylith/install/release_assets.py)
- [ ] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [ ] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [ ] [validate_backlog_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/validate_backlog_contract.py)
- [ ] [backlog_authoring.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/backlog_authoring.py)
- [ ] [INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [ ] [INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)
- [ ] [INDEX.md](/Users/freedom/code/odylith/odylith/casebook/bugs/INDEX.md)
- [ ] [v0.1.8.md](/Users/freedom/code/odylith/odylith/runtime/source/release-notes/v0.1.8.md)

## Risks & Mitigations
- [ ] Risk: helper extraction still grows oversized files indirectly.
  - [ ] Mitigation: keep new runtime and sync policy in small adjacent modules
        and use thin call-site glue only.
- [ ] Risk: benign-warning suppression hides real verification errors.
  - [ ] Mitigation: allowlist only known success-path warnings and preserve
        fatal stderr on failure.
- [ ] Risk: legacy Radar normalization overwrites authored rationale.
  - [ ] Mitigation: backfill only missing required bullets and preserve
        existing prose verbatim.
- [ ] Risk: stale-reference audit scans too much generated content.
  - [ ] Mitigation: restrict to tracked text files outside managed runtime,
        cache, and generated state trees.

## Validation/Test Plan
- [ ] `pytest -q tests/unit/install/test_runtime.py`
- [ ] `pytest -q tests/unit/install/test_release_assets.py`
- [ ] `pytest -q tests/integration/install/test_manager.py`
- [ ] `pytest -q tests/unit/test_cli.py`
- [ ] `pytest -q tests/unit/runtime/test_validate_backlog_contract.py`
- [ ] `pytest -q tests/unit/runtime/test_backlog_authoring.py tests/unit/runtime/test_sync_cli_compat.py`
- [ ] repo-local CLI smoke for `version`, `doctor`, `install`/`reinstall`, and
      `sync`
- [ ] `git diff --check`

## Rollout/Communication
- [ ] Bind all eight fixes under `B-048` so the release wave stays coherent.
- [ ] Land runtime trust and repair first, then sync unblock, then operator
      noise cleanup.
- [ ] Update the 0.1.8 release note only after the behavior is implemented and
      validated.

## Current Outcome
- [x] `B-048` is opened as the umbrella workstream for the 0.1.8 migration
      recovery wave.
- [x] Child workstreams `B-049` through `B-056` and bugs `CB-054` through
      `CB-061` are now the explicit execution slices for this feedback set.
- [ ] Runtime, migration, sync, and CLI hardening are in progress.
