---
status: finished
idea_id: B-017
title: Odylith Surface Browser Stability and End-to-End Hardening
date: 2026-03-29
priority: P0
commercial_value: 4
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: rendered surface stability, shell routing, deep links, browser smoke coverage, and release confidence
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith now has a real multi-surface shell, but the browser proof lane is still too shallow for release confidence. We need deeper headless validation across rendered surfaces, URL-state routing, deep links, and browser failures so stability regressions get caught before they reach consumers.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-surface-browser-stability-and-end-to-end-hardening.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-012, B-013, B-016
workstream_blocks:
related_diagram_ids:
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Odylith’s rendered surfaces now cover real product workflows, but the current
browser smoke tests still only prove a thin happy path. They do not yet
exercise deeper URL-state routing, shell history behavior, more surface
deeplinks, or browser-level request failures across the main operator flows.

## Customer
- Primary: Odylith consumers who need the local shell and its five surfaces to
  behave reliably after install and upgrade.
- Secondary: Odylith maintainers who need stronger release confidence before
  cutting and dogfooding new versions.

## Opportunity
If Odylith validates its rendered surface contract through deeper headless
browser flows, then shell regressions, iframe breakage, deeplink drift, and
broken asset fetches will get caught earlier and the product will feel
substantially more trustworthy.

## Proposed Solution
Expand the browser proof lane to assert clean network and console behavior,
exercise deeper Radar/Registry/Atlas/Casebook/Compass navigation flows, and
use those tests to harden any routing or rendering defects the new coverage
finds.

## Scope
- strengthen the Playwright-based browser harness to capture failed requests and
  HTTP error responses
- add deeper shell navigation and back/forward tests
- add deeper Radar, Registry, Atlas, Casebook, and Compass deeplink coverage
- harden any routing or rendering defects surfaced by the stronger browser
  proof lane
- run the expanded browser suite plus nearby runtime tests

## Non-Goals
- visual snapshot testing
- hosted/browser-cloud compatibility work
- redesigning the shell UI

## Risks
- browser tests become flaky if selectors depend on unstable incidental markup
- deeper test coverage finds legitimate routing defects that require product
  changes late in the slice
- runtime-backed surface flows may slow the test lane materially if the
  browser proof is not scoped carefully

## Dependencies
- `B-012` improved Compass runtime/provider behavior, which this browser slice
  now needs to validate at the surface level
- `B-013` reduced renderer duplication, which makes cross-surface hardening
  safer and lower-risk
- `B-016` improved install activation, making the rendered consumer shell a
  higher-value proof target

## Success Metrics
- browser proof catches failed requests, JS errors, and broken shell routing
  across the main operator flows
- deeper deeplinks across Radar, Registry, Atlas, Casebook, and Compass remain
  stable under headless browser navigation
- the expanded browser suite passes consistently alongside the nearby runtime
  integration tests

## Validation
- `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_render_compass_dashboard.py tests/integration/runtime/test_surface_browser_smoke.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py`

## Outcome
- the Playwright browser harness now fails on console errors, page errors,
  request failures, and local HTTP error responses
- browser coverage now exercises deeper shell history, Radar-to-Registry,
  Radar-to-Atlas, Casebook history, and Compass routing flows
- Radar row selection now syncs its selected workstream back into the shell URL,
  so browser history and deeplinks restore the correct detail state
- the widened runtime and browser suite now passes cleanly

## Rollout
Ship as a browser-proof tightening slice. Keep the tests targeted at the real
rendered consumer shell and use any discovered regressions to harden the
surface contract before release.

## Why Now
The shell is now the consumer front door. If Odylith cannot prove deep browser
navigation and routing reliability locally, release confidence is overstated.

## Product View
Odylith should treat the rendered product as a real product surface, not as a
best-effort local artifact. Browser proof is part of the contract.

## Impacted Components
- `dashboard`
- `radar`
- `registry`
- `atlas`
- `casebook`
- `compass`

## Interface Changes
- no intentional UI redesign
- shell route and deeplink behavior is now more strongly validated end to end
- Radar selection now updates the shell URL more reliably

## Migration/Compatibility
- no migration required
- browser proof remains local and headless
- existing rendered surface entrypoints keep the same public paths

## Test Strategy
- expand headless browser coverage across the five surfaces
- fail on console, page, request, and local HTTP errors
- rerun nearby runtime renderer tests with the widened browser suite

## Open Questions
- should Odylith eventually add lightweight visual diff checks on top of the
  functional browser proof
