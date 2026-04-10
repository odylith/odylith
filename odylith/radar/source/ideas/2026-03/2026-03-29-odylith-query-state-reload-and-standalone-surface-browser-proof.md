---
status: finished
idea_id: B-018
title: Query-State Reload and Standalone Surface Browser Proof
date: 2026-03-29
priority: P0
commercial_value: 4
product_impact: 5
market_value: 4
impacted_parts: shell query-state routing, standalone surface redirects, reload persistence, browser proof depth, and release confidence
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith now has a materially stronger browser smoke lane, but it still under-proves the actual operator contract of direct query-state entry, reload persistence, and standalone child-surface redirects into the shell. Those are exactly the routes consumers hit from bookmarks, copied links, refreshes, and local surface entrypoints.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-query-state-reload-and-standalone-surface-browser-proof.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-017
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
Odylith now proves core multi-surface navigation in a browser, but it still
under-tests the direct query-state contract that real operators use: opening a
specific workstream, component, diagram, bug, or Compass scope by URL;
reloading that state; and entering through standalone child-surface entrypoints
that should redirect cleanly into the shell without losing context.

## Customer
- Primary: Odylith consumers using bookmarks, copied links, browser refresh,
  and direct local surface entrypoints.
- Secondary: Odylith maintainers who need stronger release confidence that the
  shell route contract actually survives normal browser behavior.

## Opportunity
If Odylith proves direct query-state entry, reload persistence, and standalone
redirect preservation end to end, then the shell becomes materially more
trustworthy as an operator surface and route regressions will be caught before
release.

## Proposed Solution
Extend the headless browser lane to cover direct shell query-state routes and
reload restoration for each major surface, plus standalone child-surface
redirects that preserve the selected state when they hand off into the shell.
Harden any route-loss defects these tests expose.

## Scope
- add direct shell query-state + reload coverage for Radar, Registry, Atlas,
  Casebook, and Compass
- add standalone entrypoint redirect coverage that preserves query state into
  the shell
- patch any route-loss or selected-state bugs those flows expose
- rerun the widened runtime/browser suite

## Non-Goals
- visual screenshot approval testing
- hosted browser compatibility work
- redesigning the shell or surface UI

## Risks
- direct-route tests may expose real state sync gaps across shell and child
  surfaces
- selectors for selected-state assertions may drift if they depend on weak
  markup contracts
- the wider browser suite may slow down if the scenarios are not kept focused

## Dependencies
- `B-017` established the stronger browser harness and Radar route-sync fix
  this slice will extend.

## Success Metrics
- direct shell query-state routes restore the expected selected context after
  reload across the main surfaces
- standalone surface entrypoints preserve selected state when redirecting into
  the shell
- the wider runtime/browser suite passes cleanly after hardening

## Validation
- `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py tests/unit/test_cli.py tests/integration/install/test_manager.py`
- `git diff --check`

## Outcome
- browser proof now covers direct shell query-state entry plus reload
  restoration for Radar, Registry, Atlas, Casebook, and Compass
- standalone child-surface entrypoints now have end-to-end proof that they
  preserve selected query state when redirecting into the shell
- the headless harness now ignores only the narrow class of aborted local
  child-surface document loads caused by intentional shell navigation, while
  still failing on real request, console, page, and HTTP errors
- the widened runtime/browser plus core CLI/install lane passed cleanly

## Rollout
Ship as a targeted route-contract hardening slice. Keep the focus on real
operator entry modes like copied links, reloads, and standalone surface
hand-offs into the shell.

## Why Now
Odylith is now relying on shell query state as a first-class operator contract.
That contract has to survive bookmark, reload, and redirect behavior before it
can be trusted in consumer repos.

## Product View
The shell should be linkable and restart-safe. If state disappears on reload or
redirect, the product feels fragile even when the underlying data is correct.

## Impacted Components
- `dashboard`
- `radar`
- `registry`
- `atlas`
- `casebook`
- `compass`

## Interface Changes
- no new UI surface
- query-state reload and standalone redirect behavior now has stronger
  browser-level proof

## Migration/Compatibility
- no migration required
- existing direct links and child entrypoints keep the same paths
- route preservation is tightened without changing user-visible URLs

## Test Strategy
- cover direct query-state reload flows across all primary surfaces
- cover standalone child-surface redirects into the shell
- rerun browser, runtime, CLI, and install-adjacent coverage together

## Open Questions
- should the shell surface a clearer invalid-query fallback when a bookmarked
  object no longer exists
