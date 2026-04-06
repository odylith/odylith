Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-017

Goal: Expand Odylith’s browser proof lane so rendered surfaces, deeplinks, and
shell history behavior are validated more comprehensively and hardened where
needed.

Assumptions:
- The existing Playwright smoke harness was the right place to deepen browser
  proof instead of adding a second browser stack.
- The checked-in rendered surfaces were representative enough for the main
  stability lane once regenerated after source changes.
- Stronger browser proof should focus on operator-critical routing and request
  health, not visual snapshots.

Constraints:
- Keep the browser suite deterministic and release-viable.
- Avoid brittle selectors that depend on incidental styling markup.
- Keep the browser lane fast enough to run regularly.

Reversibility: Reverting this slice restores the previous browser smoke suite
and Radar route-sync behavior without requiring data migration.

Boundary Conditions:
- Scope included browser harness hardening, deeper surface navigation tests, and
  any rendering/routing fixes discovered through that work.
- Scope excluded snapshot testing and broader UI redesign.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] Browser proof did not yet fail on request failures or HTTP error
  responses.
- [x] Shell history and deeper deeplink flows were under-tested.
- [x] Radar, Registry, Atlas, Casebook, and Compass did not all get deeper
  cross-surface navigation proof.
- [x] Surface defects found through stronger browser proof still needed to be
  hardened.

## Success Criteria
- [x] Browser helper captures console errors, page errors, request failures, and
  HTTP error responses.
- [x] Shell tab/back/forward behavior is validated under headless navigation.
- [x] Deeper cross-surface deeplinks are validated across the main rendered
  operator flows.
- [x] Nearby runtime/surface tests remain green with the stronger browser lane.

## Non-Goals
- [x] Visual screenshot approval testing.
- [x] Hosted browser compatibility work.
- [x] UI redesign.

## Impacted Areas
- [x] [test_surface_browser_smoke.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_smoke.py)
- [x] [render_backlog_ui.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui.py)
- [x] [2026-03-29-odylith-subagent-reasoning-ladder-and-grounded-spawn-defaults.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-03/2026-03-29-odylith-subagent-reasoning-ladder-and-grounded-spawn-defaults.md)
- [x] [2026-03-29-odylith-subagent-reasoning-ladder-and-grounded-spawn-defaults.md](/Users/freedom/code/odylith/odylith/technical-plans/done/2026-03/2026-03-29-odylith-subagent-reasoning-ladder-and-grounded-spawn-defaults.md)
- [x] [radar.html](/Users/freedom/code/odylith/odylith/radar/radar.html)

## Risks & Mitigations

- [x] Risk: selectors become brittle and create flaky browser tests.
  - [x] Mitigation: use stable IDs, roles, explicit chip/button classes, and
    shell query-state assertions instead of incidental layout assumptions.
- [x] Risk: deeper browser proof uncovers real shell routing defects.
  - [x] Mitigation: patch the affected surface contract instead of weakening the
    test.
- [x] Risk: browser proof becomes too slow for regular use.
  - [x] Mitigation: keep flows targeted, reuse a shared browser context, and
    widen only after the focused lane is green.

## Validation/Test Plan
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_smoke.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_render_compass_dashboard.py tests/integration/runtime/test_surface_browser_smoke.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py`
- [x] `PYTHONPATH=src .venv/bin/python -m odylith.runtime.surfaces.render_backlog_ui --repo-root . --output odylith/radar/radar.html`
- [x] `git diff --check`

## Rollout/Communication
- [x] Keep browser proof focused on real operator-critical flows.
- [x] Close the slice only after the strengthened browser lane and nearby
  runtime tests pass together.
- [x] Update backlog and plan indexes when the slice closes.

## Current Outcome
- The Playwright browser harness now fails on console errors, page errors,
  request failures, and local HTTP error responses.
- Browser coverage now exercises shell history, Compass-to-Radar deeplinks,
  Radar-to-Registry routing, Radar-to-Atlas routing, and Casebook history
  restoration under headless navigation.
- Radar now reports row-selection changes back to the shell, so the shell URL
  and browser history restore the actual selected workstream instead of stale
  deep-link state.
- The widened runtime/browser lane now passes cleanly.
