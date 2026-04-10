---
status: implementation
idea_id: B-071
title: Scope Signal Ladder, Cross-Surface Focus Gating, and Low-Signal Suppression
date: 2026-04-09
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: delivery-intelligence scope escalation, Compass scope and narration gating, Radar default focus ordering, Registry component promotion ordering, Atlas active-workstream promotion, shared shell budget classes, governance guidance, and browser-proof coverage
sizing: L
complexity: VeryHigh
ordering_score: 95
ordering_rationale: Odylith now has enough live cross-surface evidence that low-signal governance churn can still outrank or leak into the operator's default view. Until one shared scope-signal ladder decides visibility, promotion, and expensive compute budgets everywhere, Compass, Radar, Registry, Atlas, and the shell will keep rediscovering the same heuristics bugs while wasting narration or reasoning budget on the wrong scopes.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-09-odylith-scope-signal-ladder-cross-surface-focus-gating-and-low-signal-suppression.md
execution_model: standard
workstream_type: child
workstream_parent: B-025
workstream_children:
workstream_depends_on: B-025,B-062,B-063
workstream_blocks:
related_diagram_ids: D-028,D-029
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
Odylith still has too many surface-local answers to the same question:
"does this scope deserve attention right now?" Compass had one set of rolling-
window heuristics, Radar had another default ordering posture, Atlas promoted
active pills from its own evidence mix, Registry could still float low-signal
component snapshots near the top, and downstream budget decisions had no
shared contract for when a scope was allowed to spend fresh provider or
reasoning work. The result was predictable drift: lone governance-file churn,
broad fanout transactions, or generated noise could make a quiet workstream
look important, while the expensive paths still had no one place to say "this
scope is too low-signal to buy fresh narration."

## Customer
- Primary: operators who need the governance surfaces to point at the work
  that is actually urgent instead of the work that merely changed.
- Secondary: maintainers who need one auditable escalation contract instead of
  fixing visibility, ranking, and budget bugs surface by surface.

## Opportunity
If Odylith promotes one deterministic scope-signal ladder into shared product
truth, then Compass, Radar, Registry, Atlas, and the shell can all focus on
the same few scopes first, keep low-signal noise available only when asked
for, and spend fresh provider budget on the rare scopes that have actually
earned it.

## Proposed Solution
Make Delivery Intelligence the sole owner of scope escalation through one
shared Scope Signal Ladder:
- `R0 suppressed_noise`
- `R1 background_trace`
- `R2 verified_local`
- `R3 active_scope`
- `R4 actionable_priority`
- `R5 blocking_frontier`

The ladder must be deterministic, cheap, and explainable. Every snapshot must
carry the rung, reasons, budget class, promotion bit, and feature vectors that
produced the rung. Compass, Radar, Registry, Atlas, and shell consumers should
read that contract instead of rebuilding local urgency heuristics. Low-signal
scopes stay hidden by default, deep links remain preserved but quiet, and
fresh provider or reasoning work is reserved for the top rungs only.

## Scope
- add the shared ladder contract under Delivery Intelligence with window-aware
  Compass helpers
- extend persisted delivery snapshots with additive `scope_signal` payloads
- gate Compass selectors, timelines, current-workstream promotion, and scoped
  narration budgets through the ladder
- make Radar default operational ordering ladder-aware while keeping the full
  backlog exhaustive
- gate Registry component ordering and Atlas active-workstream promotion
  through the same signal
- define provider-neutral budget classes for shell and downstream reasoning
  jobs so Codex, Claude, and future hosts all map from one product contract
- add Atlas diagrams, Casebook memory, specs, skills, and browser proof for
  the new cross-surface behavior

## Non-Goals
- replacing Radar's exhaustive backlog truth with a filtered source model
- introducing opaque ML ranking in v1
- redesigning the governance surfaces visually
- weakening Compass's live narration voice or moving back to canned fallback
  copy

## Risks
- if the ladder is too strict, real work could disappear from default views
- if the ladder is too loose, low-signal churn will keep wasting attention and
  budget
- parent rollups could become hard to reason about if the child-lift rules are
  not kept simple and auditable

## Dependencies
- `B-025` already hardened cross-surface freshness and browser proof, which is
  the right parent lane for this promotion-and-budget contract
- `B-062` introduced live proof-state control that now needs a clean way to
  dominate ordinary activity signals
- `B-063` added explicit release targeting that should remain visible without
  letting low-signal scopes steal default focus

## Success Metrics
- low-signal scopes such as lone governance-file churn or broad fanout rows
  stay out of default Compass selectors, timelines, and focus lists
- Timeline Audit keeps the anchor workstream visible and first in the chip
  row when a checkpoint or headline clearly names the most important fix
- Radar default operational views, Registry ordering, and Atlas active pills
  promote the same scopes instead of drifting
- `R0-R3` scopes do not buy fresh provider or Tribunal-style reasoning work by
  default
- explicit deep links still preserve quiet low-signal scopes without lying
  about local activity
- browser proof catches cross-surface promotion drift before release
- Compass itself also clears the founder release bar instead of merely avoiding
  regression: hot exact reuse `<=50ms` internal, cold shell-safe `<=1s`
  internal, and ready briefs no longer lean primarily on deterministic
  fallback

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_scope_signal_ladder.py tests/unit/runtime/test_delivery_intelligence_engine.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_render_backlog_ui_payload_runtime.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_odylith_assist_closeout.py`
- `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py`
- `PYTHONPATH=src python3 -m odylith.cli atlas render --repo-root .`
- `git diff --check`

## Rollout
Land the shared ladder contract in Delivery Intelligence first, then route the
surface promotion and budget decisions through it, then lock the whole behavior
down with governed memory and headless browser proof.

## Why Now
Compass already proved the cost of local heuristics. The more surfaces Odylith
adds, the more expensive it becomes to keep rediscovering the same
"this looked active but wasn't" bug in four different places.

## Product View
The product should not merely show everything that changed. It should help an
operator start with what matters, keep the quieter trace available when needed,
and refuse to spend expensive thinking budget on noise.

## Impacted Components
- `delivery-intelligence`
- `compass`
- `radar`
- `registry`
- `atlas`
- `dashboard`
- `proof-state`

## Interface Changes
- additive `scope_signal` payload on delivery snapshots
- additive window-aware `scope_signal` output in Compass runtime payloads
- provider-neutral `budget_class` contract shared by Compass and other
  governance consumers

## Migration/Compatibility
- keep raw Radar, Registry, Atlas, Compass, and traceability truth exhaustive
- preserve deep links for low-signal scopes, but render them as quiet state
  instead of promoted activity
- keep the ladder deterministic and auditable first; any later ML calibration
  must remain offline and advisory until explicitly productized

## Test Strategy
- direct ladder unit coverage for each rung and rollup rule
- Compass runtime tests for verified-scope gating and low-signal quiet states
- Radar, Registry, and Atlas unit proof for ladder-driven ordering or
  promotion
- headless browser proof for cross-surface default-focus behavior

## Open Questions
- whether future operator views need a user-toggleable "show background trace"
  lane once the default suppression contract proves stable
- whether `R4` should ever buy more than one fresh scoped narration per window
  in the bounded Compass refresh path
