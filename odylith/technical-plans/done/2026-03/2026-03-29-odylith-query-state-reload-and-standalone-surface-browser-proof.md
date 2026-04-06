Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-018

Goal: Prove and harden Odylith’s direct query-state routing, reload
persistence, and standalone child-surface shell redirects under headless
browser automation.

Assumptions:
- The existing Playwright-based browser harness remained the correct proof lane.
- The rendered surface artifacts in this repo were the right target for the
  consumer-facing route contract.
- Route and reload correctness mattered more here than snapshot-style visual
  checks.

Constraints:
- Keep the browser lane deterministic and fast enough to run regularly.
- Prefer stable route and selected-state assertions over brittle incidental DOM
  checks.
- Harden real product defects instead of relaxing route expectations.

Reversibility: Reverting this slice restores the previous browser-proof depth
without data migration.

Boundary Conditions:
- Scope included browser-proof expansion, shell/child-surface route hardening,
  and widened runtime/browser validation.
- Scope excluded UI redesign and visual approval testing.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] Direct shell query-state entry was not comprehensively proven across the
  main surfaces.
- [x] Browser reload restoration of selected surface state was under-tested.
- [x] Standalone child-surface entrypoints were not yet proven to preserve
  query state when redirecting into the shell.
- [x] Any route-loss defects found through this deeper proof still needed to be
  hardened.

## Success Criteria
- [x] Direct shell query-state routes restore the expected selected context.
- [x] Reload preserves selected surface state across the main surfaces.
- [x] Standalone child-surface entrypoints preserve query state into the shell.
- [x] The wider runtime/browser validation lane remains green.

## Non-Goals
- [x] Visual screenshot approval testing.
- [x] Hosted browser compatibility work.
- [x] Shell redesign.

## Impacted Areas
- [x] [test_surface_browser_smoke.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_smoke.py)
- [x] nearby runtime/browser validation lanes

## Risks & Mitigations

- [x] Risk: the deeper route lane exposes real state drift across shell and
  - [ ] Mitigation: TODO (add explicit mitigation).
  child surfaces.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: patch the route contract instead of weakening the test.
- [x] Risk: the wider browser lane becomes brittle or slow.
  - [x] Mitigation: keep selectors stable and scenarios focused on operator
    routes.
- [x] Risk: intentional shell navigation aborts iframe document fetches and
  - [ ] Mitigation: TODO (add explicit mitigation).
  create browser-test noise.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: ignore only that narrow aborted local child-surface
    document class while still failing on real request, console, page, and HTTP
    errors.

## Validation/Test Plan
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_smoke.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py tests/unit/test_cli.py tests/integration/install/test_manager.py`
- [x] `git diff --check`

## Rollout/Communication
- [x] Keep the browser proof focused on real route contracts users hit through
  copied links, refreshes, and local surface entrypoints.
- [x] Close the slice only after the widened runtime/browser lane passes
  together.

## Current Outcome
- Direct shell query-state and reload restoration are now covered end to end
  for Radar, Registry, Atlas, Casebook, and Compass.
- Standalone surface entrypoints now have proof that they preserve selected
  state when redirecting into the shell.
- The browser harness now filters only the narrow class of expected aborted
  local child-surface document requests caused by deliberate shell navigation,
  while keeping all stronger browser-failure assertions intact.
- The widened runtime/browser plus core CLI/install lane passed cleanly.
