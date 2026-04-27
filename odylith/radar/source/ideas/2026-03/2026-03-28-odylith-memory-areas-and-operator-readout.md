status: finished

idea_id: B-008

title: Memory Areas and Operator Readout

date: 2026-03-28

priority: P1

commercial_value: 4

product_impact: 5

market_value: 4

impacted_parts: context-engine memory snapshot contract, runtime status output, operator readouts, and context-engine source truth

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Odylith already had real local-first retrieval, guidance, session, and evaluation state, but operators still had to infer that from raw JSON or backend jargon. The product needed one explicit memory-area readout that says what is live, cold, or still missing.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-28-odylith-memory-areas-and-operator-readout.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on:

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

## Problem
Odylith could describe its local backend, compiler bundle, and evaluation
posture, but it still did not tell an operator which memory areas actually
exist today, which ones are only partial, and which ones are still missing.
That made the product’s memory story feel more complex than it really is.

## Customer
- Primary: Odylith operators and maintainers trying to understand what memory
  Odylith really has on a fresh install or active repo.
- Secondary: future Odylith contributors who need one explicit memory posture
  contract instead of scattered backend-specific terminology.

## Opportunity
By turning memory posture into named areas, Odylith can expose its real current
strengths and gaps without pretending that planned collaboration and durable
judgment memory already exist.

## Proposed Solution
Add a first-class `memory_areas.v1` section to the runtime memory snapshot and
surface it in `odylith context-engine status` plus operator readouts. This
record must not be read as permission to recreate a shell status drawer,
cockpit, recorder, chart, or status slab in the dashboard.

## Scope
- add explicit memory-area posture to `memory_snapshot.v1`
- print concise memory-area posture in runtime status output
- keep memory-area strengths and gaps in runtime/diagnostic readouts without
  rendering status chrome into the dashboard shell
- update the Odylith Context Engine source contract to describe the new readout

## Non-Goals
- implementing durable decision memory
- implementing workspace or actor identity memory
- implementing durable contradiction memory
- changing the local or remote backend providers

## Risks
- the new readout can become marketing copy instead of an honest contract if it
  overstates what Odylith currently remembers
- the shell can become noisier if the memory-area section repeats backend
  jargon instead of simplifying it

## Dependencies
- no hard prerequisite; this is a bounded product readout slice on top of
  existing Context Engine, shell, and diagnostics contracts

## Success Metrics
- `memory_snapshot.v1` includes named memory areas with live, cold, planned, or
  disabled posture
- `odylith context-engine status` prints a concise memory-area summary
- runtime and diagnostic readouts expose a human-readable memory-area section
  without reintroducing dashboard shell status UI
- tests cover the new snapshot and rendering contract

## Validation
- `pytest -q tests/unit/runtime/test_odylith_runtime_surface_summary.py tests/unit/runtime/test_odylith_memory_areas.py tests/unit/runtime/test_render_tooling_dashboard.py`

## Rollout
Ship the memory-area readout as part of the existing Context Engine and shell
contracts without changing install or upgrade behavior.

## Why Now
Odylith’s install and shell experience improved, which made the remaining
memory-story ambiguity more obvious. This is the right time to make the memory
contract legible before deeper collaboration-memory work lands.

## Product View
If Odylith has real memory power, it should show that power plainly and admit
the missing areas just as plainly.

## Impacted Components
- `odylith-context-engine`
- `dashboard`
- `odylith`

## Interface Changes
- `memory_snapshot.v1` gains a `memory_areas` section
- `odylith context-engine status` prints memory-area counts and headline
- dashboard product surfaces do not render memory posture as shell status
  chrome; diagnostic readouts remain runtime-owned

## Migration/Compatibility
- additive only; existing memory snapshot consumers keep the previous fields
- no backend migration required

## Test Strategy
- unit-test the memory-area snapshot builder
- unit-test runtime status output for the new memory-area lines
- verify the rendered shell contains the memory-area section

## Open Questions
- when durable decision, collaboration, and contradiction memory land, should
  they remain part of the Context Engine contract or graduate into separate
  Registry-owned components
