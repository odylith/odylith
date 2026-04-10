---
status: finished
idea_id: B-059
title: Atlas Memory Substrate and Runtime Topology Refresh
date: 2026-04-07
priority: P1
commercial_value: 3
product_impact: 5
market_value: 3
impacted_parts: Atlas source diagrams, Mermaid catalog metadata, Registry diagram linkage, Atlas component coverage, and rendered Atlas navigation
sizing: M
complexity: Medium
ordering_score: 100
ordering_rationale: Odylith's Registry and runtime contracts now expose a much richer memory substrate and conversation/runtime topology than Atlas currently shows. Shipping broad runtime maps with stale or blunt memory boxes would leave the architecture surface behind the product.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-07-odylith-atlas-memory-substrate-and-runtime-topology-refresh.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-031,B-058
workstream_blocks:
related_diagram_ids: D-002,D-018,D-020,D-025
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
Atlas still tells an older, flatter story than the runtime and Registry now
deserve. The broad runtime maps collapse the memory substrate into one generic
box, and Atlas has no dedicated diagram that treats projection bundle, snapshot
fallback, local backend, remote retrieval, and packet-safe memory contracts as
first-class topology.

## Customer
- Primary: Odylith maintainers using Atlas to understand where memory, runtime
  conversation intelligence, and governed execution boundaries actually live.
- Secondary: operators and evaluators who rely on Atlas links from Radar and
  Registry to understand why the product behaves the way it does.

## Opportunity
Bring Atlas back in line with current product truth so the runtime maps reveal
the actual memory seams and the conversation/runtime flow instead of forcing
maintainers to reconstruct the architecture from specs alone.

## Proposed Solution
- refresh the broad Atlas runtime maps so they show the governed memory family
  and the current conversation/runtime flow
- add a dedicated memory-substrate diagram with first-class links to the new
  Registry components
- widen Registry diagram linkage so the memory components point at that new
  Atlas artifact
- rerender Atlas and prove the new diagram is navigable in headless browser

## Scope
- `odylith/atlas/source/*.mmd` for the impacted runtime maps
- `odylith/atlas/source/catalog/diagrams.v1.json`
- the new dedicated memory-substrate diagram assets
- related Registry component diagram references
- Atlas component documentation and focused browser proof

## Non-Goals
- changing memory runtime behavior
- redesigning the Atlas renderer itself
- redrawing every product diagram in one sweep

## Risks
- over-explaining the runtime in the broad maps could make them less legible
- adding a new memory diagram without updating Registry linkage would create
  another orphaned architecture asset

## Dependencies
- `B-031`
- `B-058`

## Success Metrics
- Atlas exposes one dedicated memory-substrate diagram
- broad runtime maps no longer hide the governed memory family behind one vague
  memory box
- Registry and Atlas both link to the new diagram where relevant
- headless browser proof can open the new diagram and round-trip its links

## Validation
- `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_validate_component_registry_contract.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_mermaid_catalog.py`
- `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_ux_audit.py -k 'atlas or registry'`
- Atlas and related surface rerenders from current catalog truth

## Rollout
Update the governed Atlas source first, then rerender Atlas and any affected
cross-surface outputs, then lock it down with focused browser proof.

## Why Now
Registry now has the real memory-component topology. Atlas should not still look
like it missed the memo.

## Product View
When the product becomes deeper, Atlas should become clearer, not vaguer. This
slice makes the architecture surface worthy of the runtime and governance work
that already landed.

## Impacted Components
- `atlas`
- `registry`
- `odylith`
- `odylith-context-engine`
- `odylith-memory-backend`
- `odylith-projection-bundle`
- `odylith-projection-snapshot`
- `odylith-remote-retrieval`
- `odylith-memory-contracts`

## Interface Changes
- Atlas now exposes a dedicated memory-substrate diagram `D-025`
- the broad runtime diagrams `D-002`, `D-018`, and `D-020` now show the
  governed memory family and current conversation/runtime flow more explicitly
- Registry component detail can now deep-link into the dedicated memory
  topology artifact instead of only broad runtime maps

## Migration/Compatibility
- additive Atlas and Registry linkage refinement only
- no runtime migration required

## Test Strategy
- rerender Atlas and related surfaces from updated source truth
- validate catalog, Registry linkage, and Atlas hygiene contracts
- prove the new diagram and its cross-surface links in headless browser

## Open Questions
- whether the next Atlas refresh should split the Tribunal-backed conversation
  flow into its own dedicated diagram once more runtime families graduate into
  first-class topology artifacts

## Outcome
- Landed on 2026-04-07.
- Atlas now refreshes `D-002`, `D-018`, and `D-020` so the governed memory
  family, Tribunal-backed delivery flow, and conversation/runtime path are
  explicit instead of implied.
- Atlas now includes `D-025`, a dedicated memory-substrate topology map that
  links projection bundle, snapshot, local backend, remote retrieval, and
  memory-contract boundaries directly.
- Registry components now point at `D-025`, and the refreshed Atlas and Radar
  surfaces keep those cross-surface links live.
- Focused unit and headless browser proof now cover the new diagram, its Atlas
  deep links, and the `B-058` Radar route into `D-025`.
