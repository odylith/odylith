Status: In progress
Created: 2026-04-18
Updated: 2026-04-18
Backlog: B-126

# Conditional Release-Targeted Backlog Authoring

## Goal
Add a narrow `odylith backlog create --release <selector>` path so new queued
backlog workstreams can be assigned to `next` or an explicit release in the
same authoring flow without weakening release truth, queue status, or owned
surface freshness.

## Decisions
- Preserve queue-only behavior when `--release` is omitted.
- Treat release targeting as conditional authoring ergonomics, not a new
  release-planning model.
- Validate the release selector and candidate assignment events before writing
  any backlog files.
- Preserve `status: queued` for every newly created workstream, even when it is
  release-targeted.
- Reuse the release-planning authoring contract for release event validation
  instead of duplicating selector semantics in backlog authoring.
- Refresh Radar after backlog source truth changes and refresh Compass after
  release-targeted creation changes release visibility.

## Related Records
- Backlog: B-126.
- Release planning foundation: B-063.
- Owned-surface freshness learning: CB-112.

## Must-Ship
- [x] Add `--release` to `odylith backlog create`.
- [x] Preflight invalid release selectors before any partial backlog or release
      event write.
- [x] Append one release assignment event for every created ID when release
      targeting is requested.
- [x] Preserve queued workstream status.
- [x] Print and emit JSON summary fields for created IDs, release target,
      queued-status preservation, Radar refresh, and Compass refresh/status.
- [x] Keep `odylith backlog create` without `--release` from touching release
      assignment truth.

## Should-Ship
- [x] Add batch coverage for multiple created IDs.
- [x] Add dry-run coverage for release targeting.
- [x] Add terminal-release and missing-selector no-partial-write coverage.
- [x] Add `release show next` visibility coverage for queued targeted records.
- [x] Add CLI help coverage for the new flag.

## Non-Goals
- Do not change the one-active-release-per-workstream model.
- Do not activate v0.1.12 implementation waves or alter release alias policy.
- Do not broaden backlog creation into a generic release-planning front door.

## Impacted Areas
- [x] [backlog_authoring.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/backlog_authoring.py)
- [x] [release_planning_authoring.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/release_planning_authoring.py)
- [x] [test_backlog_authoring.py](/Users/freedom/code/odylith/tests/unit/runtime/test_backlog_authoring.py)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)

## Validation
- [x] `PYTHONPATH=src python -m py_compile src/odylith/runtime/governance/backlog_authoring.py src/odylith/runtime/governance/release_planning_authoring.py`
- [x] `PYTHONPATH=src pytest -q tests/unit/runtime/test_backlog_authoring.py tests/unit/runtime/test_release_planning.py tests/unit/test_cli.py -q`
- [x] `PYTHONPATH=src pytest -q tests/unit/runtime/test_backlog_authoring.py tests/unit/runtime/test_release_planning.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_owned_surface_refresh_authoring.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/test_cli.py tests/unit/test_cli_audit.py` (`365 passed`)
- [x] Source-local temp-repo dry-run smoke for `odylith backlog create --release next --json` proved created IDs, `release-0-1-12`, queued-status preservation, and skipped dry-run refresh status.
- [x] `./.odylith/bin/odylith validate backlog-contract --repo-root .`
- [x] `./.odylith/bin/odylith sync --repo-root . --impact-mode selective --proceed-with-overlap -- <B-126/code/test/governance paths>`
- [x] `./.odylith/bin/odylith sync --repo-root . --check-only --impact-mode selective --proceed-with-overlap`
- [x] `PYTHONPATH=src pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_atlas_sort_browser.py tests/integration/runtime/test_compass_browser_regression_matrix.py` (`29 passed`)

## Open Questions
- [ ] Whether the eventual v0.1.12 implementation should also expose a
      `--release-note` override for assignment event text; this slice keeps the
      first contract intentionally narrow.
