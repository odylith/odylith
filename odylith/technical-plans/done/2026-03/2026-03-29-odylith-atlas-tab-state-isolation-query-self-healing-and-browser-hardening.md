Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-023

Goal: Make Atlas count and filter behavior deterministic across shell tab
switches, normalize bad Atlas route pairs, and prove the contract in headless
browser automation.

Assumptions:
- Atlas count drift was a shell/route-state problem, not catalog corruption.
- The existing Playwright harness was the right lane to prove and harden the
  regression.
- Fixing the shell tab-state model would be safer than special-casing every
  Atlas entry path independently.

Constraints:
- Do not regress explicit Atlas deep links from Radar, Registry, or direct URL
  entry.
- Keep the shell URL honest about the active tab's state.
- Prefer deterministic self-healing over partially filtered Atlas views.

Reversibility: Reverting this slice restores the previous shared-query-state
behavior and Atlas mismatch handling, with the same regression risk.

Boundary Conditions:
- Scope included shell routing, Atlas filtering, generated surface rerenders,
  and browser proof.
- Scope excluded Atlas visual redesign and catalog-authoring changes.

Related Bugs:
- [2026-03-29-atlas-tab-reuses-cross-surface-shell-state-and-shows-inconsistent-diagram-counts.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-29-atlas-tab-reuses-cross-surface-shell-state-and-shows-inconsistent-diagram-counts.md)

## Context/Problem Statement
- [x] Atlas totals and visible diagrams drifted based on the previous shell tab.
- [x] Shell query routing leaked Atlas and non-Atlas state across tabs.
- [x] Atlas tolerated mismatched `workstream + diagram` routes instead of
  normalizing them.
- [x] The browser suite did not yet prove this exact failure path.

## Success Criteria
- [x] Atlas tab entry restores Atlas-owned state instead of inheriting unrelated
  Radar/Compass scope.
- [x] Mismatched Atlas `workstream + diagram` links normalize to a consistent
  `All Workstreams` view.
- [x] Focused browser proof covers both direct bad routes and cross-tab
  round-trips.
- [x] The widened runtime/browser lane remains green after the fix.

## Non-Goals
- [x] Atlas redesign.
- [x] Catalog content changes.
- [x] Screenshot-based approval testing.

## Impacted Areas
- [x] [control.js](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js)
- [x] [render_mermaid_catalog.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_mermaid_catalog.py)
- [x] [test_render_mermaid_catalog.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_mermaid_catalog.py)
- [x] [test_render_tooling_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_tooling_dashboard.py)
- [x] [test_surface_browser_smoke.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_smoke.py)

## Risks & Mitigations

- [x] Risk: tab-local state restoration drops legitimate deep-link context.
  - [x] Mitigation: explicit cross-surface deeplinks still drive the URL
    directly; only top-tab switching restores remembered destination state.
- [x] Risk: Atlas normalization hides real state inconsistencies instead of
  - [x] Mitigation: normalize only when the selected diagram and workstream are
    representing them.
    provably incompatible, and cover the route with browser proof.
- [x] Risk: browser proof becomes brittle.
  - [x] Mitigation: assert stable shell query state, selected ids, and stat
    totals instead of incidental styling.

## Validation/Test Plan
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_render_tooling_dashboard.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_smoke.py -k 'atlas_bad_cross_surface_route_self_heals_to_full_catalog or atlas_tab_switch_restores_atlas_state_instead_of_leaking_radar_scope'`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_smoke.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py`
- [x] `odylith sync --repo-root . --force --impact-mode full`
- [x] `git diff --check`

## Rollout/Communication
- [x] Treat this as a route-contract hardening slice and note the Casebook bug
  so future shell-routing work sees the exact failure mode.
- [x] Regenerate Atlas and shell assets before browser validation so proof runs
  against shipped artifacts.

## Current Outcome
- The shell now keeps Atlas state local to Atlas instead of reusing unrelated
  surface params on top-tab switches.
- Atlas now normalizes bad selected-diagram/workstream pairs to a coherent
  `All Workstreams` view before filtering.
- Focused and widened browser proof now covers this class of bug directly.
