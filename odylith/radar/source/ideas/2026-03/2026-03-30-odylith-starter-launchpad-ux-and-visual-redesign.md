---
status: implementation
idea_id: B-028
title: Odylith Starter Launchpad UX and Visual Redesign
date: 2026-03-30
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: first-run launchpad, starter prompt handoff, chosen-slice framing, shell visual hierarchy, responsive onboarding layout, dismiss/reopen recovery affordances, and browser proof
sizing: M
complexity: Medium
ordering_score: 100
ordering_rationale: The first-run launchpad is now the literal product handshake for new installs, but the current screen buries the one action that matters, wastes space at laptop widths, and makes Odylith feel visually confused at the moment it should feel sharp and opinionated.
confidence: high
founder_override: yes
promoted_to_plan: odylith/technical-plans/in-progress/2026-03/2026-03-30-odylith-starter-launchpad-ux-and-visual-redesign.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-016,B-017,B-018
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
Odylith's first-run shell currently looks and feels like a dense internal
dashboard instead of a confident launchpad. The prompt handoff competes with
secondary cards, the visual hierarchy collapses at laptop widths, and the
screen does not create a strong "do this first" moment for a new operator.
Closing the first-run state also risks feeling ambiguous unless Odylith makes
it obvious that the screen is only hidden for now, not lost forever.

## Customer
- Primary: first-time Odylith users opening `odylith/index.html` immediately
  after install or upgrade.
- Secondary: maintainers and benchmark reviewers using the first-run shell as
  a proxy for product polish and product clarity.

## Opportunity
If the launchpad feels intentional, visually strong, and sharply ordered
around one starter action, then Odylith's first impression will match the
quality of its runtime and governance mechanics instead of undermining them.

## Proposed Solution
Redesign the starter launchpad around a real hero layout:
- make the starter prompt the dominant action surface
- compress secondary information into clearer support cards
- improve spacing, type hierarchy, and responsive behavior
- make first-run dismissal easy to understand, easy to recover, and hard to
  get stuck behind stale browser state
- preserve the existing onboarding truth while making the screen feel more
  productized and easier to scan

## Scope
- redesign the welcome-state layout and styling for the first-run launchpad
- tighten onboarding copy hierarchy around the starter prompt and chosen slice
- rebalance supporting cards so the screen feels clear at common laptop widths
- add a clear close/reopen model for the first-run state, including
  persistence that resets when the onboarding state materially changes
- prove the redesign with rendered HTML plus headless-browser screenshots

## Non-Goals
- redesigning the rest of Compass, Radar, Registry, Atlas, or Casebook
- changing the starter prompt contract itself beyond presentational framing
- introducing a broad theming system in this slice

## Risks
- stronger visual styling could reduce clarity if the prompt card becomes too
  decorative
- responsive changes could look good in one viewport while breaking another
- layout changes could accidentally weaken accessibility or copy affordances

## Dependencies
- `B-016` established the install-time launchpad and consumer-safe onboarding
  guidance
- `B-017` established the browser-proof lane for Odylith surfaces
- `B-018` established standalone surface browser proof for query and shell
  flows

## Success Metrics
- the first-run screen has one obvious primary action without forcing users to
  decode the rest of the dashboard first
- chosen-slice context and next-step guidance remain visible without dominating
  the layout
- the launchpad holds up visually at laptop and desktop widths
- closing the first-run state is explicit, reversible, and does not leave the
  operator trapped behind stale dismissal state
- headless-browser proof captures a materially improved first-run shell

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_shell_onboarding.py tests/unit/runtime/test_render_tooling_dashboard.py`
- `PYTHONPATH=src python -m odylith.runtime.surfaces.render_tooling_dashboard --repo-root . --output odylith/index.html`
- headless browser screenshot proof of the first-run launchpad
- `git diff --check`

## Rollout
Ship as a focused shell-surface polish slice. Keep the onboarding logic intact,
but rerender the launchpad and prove the new HTML in a browser before merging.

## Why Now
The product just cleared GA release proof, which makes the first-run shell more
important than ever. Shipping a weak welcome screen right after that undercuts
the release at the exact moment users evaluate it.

## Product View
The first-run screen cannot feel like filler. It should look like a product
with a point of view, not a pile of cards around a paragraph.

## Impacted Components
- `dashboard`
- `odylith`

## Interface Changes
- the launchpad becomes a stronger hero-style onboarding screen
- supporting guidance is reorganized into clearer secondary cards
- the prompt handoff becomes visually dominant and easier to copy/use
- the welcome state now hides via `Hide for now` and can be restored from a
  stable `Show starter guide` recovery affordance in the shell viewport
- the action cards now open the live Radar, Registry, and Atlas views with
  explicit notes about why those surfaces may still look sparse on first use

## Migration/Compatibility
- no data migration required
- onboarding truth and starter prompt remain backward compatible
- existing runtime and browser proof flows remain valid

## Test Strategy
- rerun focused onboarding and tooling-dashboard unit coverage
- rerender the shell from source
- inspect the rendered launchpad in a headless browser and capture evidence
- prove the final launchpad in a dedicated browser suite for first install,
  empty-repo honesty, dismiss/reopen persistence, and clean tab handoff
- prove the actual `odylith install` operator path can render a browser-valid
  first-run launchpad, not just the renderer in isolation
- prove storage-failure behavior so `Hide for now` still exits cleanly when
  browser persistence is partially or fully unavailable
- browser-audit dismiss, reload, reopen, Escape, CTA navigation, and
  onboarding-shape reset paths so the welcome state never feels stuck

## Open Questions
- whether a later slice should personalize the launchpad more aggressively by
  detected stack or repo shape

## Outcome
- Bound to `B-028`; implementation in progress.
