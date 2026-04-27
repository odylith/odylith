---
status: finished
idea_id: B-023
title: Atlas Tab-State Isolation, Query Self-Healing, and Browser Hardening
date: 2026-03-29
priority: P0
commercial_value: 4
product_impact: 5
market_value: 4
impacted_parts: shell tab-state routing, Atlas query normalization, Atlas count consistency, and browser proof depth
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Atlas is a core product surface and cannot show different catalog totals based on where the operator came from. Shell-state leakage plus weak Atlas query normalization makes the surface feel untrustworthy even when the underlying catalog is correct.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-atlas-tab-state-isolation-query-self-healing-and-browser-hardening.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-018
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
Atlas could render different diagram totals and filtered lists depending on the
previous shell tab. The shell leaked Atlas-specific and non-Atlas-specific
query state across tabs, and Atlas itself tolerated mismatched `workstream +
diagram` pairs instead of normalizing them.

## Customer
- Primary: Odylith operators using the shared shell to move between Radar,
  Atlas, Compass, Registry, and Casebook.
- Secondary: maintainers relying on headless browser proof to catch route
  regressions before release.

## Opportunity
If Atlas restores only Atlas-owned state on tab entry and self-heals bad route
pairs, then the same catalog becomes stable and trustworthy regardless of the
previous surface route.

## Proposed Solution
Give the shell tab-local navigation memory and tab-specific URL sanitation, and
teach Atlas to normalize mismatched selected-diagram/workstream routes back to
`All Workstreams` before filtering. Lock the route contract with focused
Playwright coverage.

## Scope
- isolate shell query state by tab instead of leaking a shared global param bag
- normalize mismatched Atlas `workstream + diagram` query pairs before list
  filtering
- add headless browser proof for both the bad-route self-heal path and the
  cross-tab Atlas round-trip path
- rerender the shell and Atlas assets

## Non-Goals
- redesigning Atlas
- changing Atlas catalog truth
- adding screenshot-based visual approval testing

## Risks
- tab-local state restoration could accidentally drop legitimate deep-link state
- Atlas filter normalization could hide a real routing contract bug if it is
  too aggressive
- browser tests could become brittle if they depend on unstable incidental DOM

## Dependencies
- `B-018` established the broader shell query-state browser proof lane.

## Success Metrics
- Atlas shows the same total catalog count when entered through the shell tab
  regardless of the prior non-Atlas tab
- mismatched Atlas `workstream + diagram` routes normalize to a consistent
  `All Workstreams` view instead of a mixed or collapsed list
- focused and widened browser proof passes cleanly

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_render_tooling_dashboard.py`
- `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py -k 'atlas_bad_cross_surface_route_self_heals_to_full_catalog or atlas_tab_switch_restores_atlas_state_instead_of_leaking_radar_scope'`
- `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py`
- `odylith sync --repo-root . --force --impact-mode full`
- `git diff --check`

## Outcome
- the shell now restores destination-tab state instead of leaking unrelated
  surface params into Atlas
- Atlas now self-heals mismatched selected-diagram/workstream routes before
  filtering
- focused and widened headless browser proof now covers this exact regression
  path

## Rollout
Ship as a route-contract hardening slice. No migration is required; the fix is
entirely in local shell state and rendered surface behavior.

## Why Now
Atlas is now a core surface in the consumer shell. A count mismatch driven only
by previous-tab state makes the product feel broken.

## Product View
The surface has to feel deterministic. If the same Atlas catalog changes count
just because I clicked from Compass or Radar first, the shell looks untrustworthy.

## Impacted Components
- `dashboard`
- `atlas`

## Interface Changes
- top-tab Atlas entry now restores Atlas-owned state instead of inheriting
  unrelated shell params
- mismatched Atlas deep links normalize to a consistent view

## Migration/Compatibility
- no data migration required
- explicit Atlas deep links continue to work
- cross-tab leakage no longer changes Atlas counts

## Test Strategy
- add focused browser regressions for the exact failure mode
- keep unit guards on shell routing and Atlas filter normalization
- rerun the broader browser/runtime lane after the focused fix

## Open Questions
- should the shell eventually preserve tab-local state for all surfaces in an
  explicit persisted session model instead of the current in-memory routing
  contract
