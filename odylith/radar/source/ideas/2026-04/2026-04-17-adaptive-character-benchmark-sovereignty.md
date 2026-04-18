status: implementation

idea_id: B-116

title: Discipline Benchmark Sovereignty

date: 2026-04-17

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: B-110 Odylith Discipline execution waves, Radar, technical plan, Registry, Atlas, Compass, benchmark proof, host guidance

sizing: M

complexity: High

ordering_score: 100

ordering_rationale: Queued through `odylith backlog create` from the current maintainer lane.

confidence: high

founder_override: yes

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-17-adaptive-agent-operating-character-credit-safe-and-benchmark-proved.md

execution_model: standard

workstream_type: child

workstream_parent: B-110

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
B-110 needs explicit child execution slices so Odylith Discipline can land through governed waves instead of collapsing governance, runtime, learning, host parity, benchmarks, and release proof into one unbounded record.

## Customer
Odylith maintainers and host-lane operators who need v0.1.11 Odylith Discipline work to stay decomposed, auditable, benchmark-proved, low-latency, and credit-safe across Codex, Claude, dogfood, and consumer lanes.

## Opportunity
Create bounded child workstreams under B-110 so each major platform slice has a clear owner, proof obligation, and wave gate while the umbrella retains the full Odylith Discipline loop.

## Proposed Solution
Create the workstream for Odylith Discipline Benchmark Sovereignty and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for Odylith Discipline Benchmark Sovereignty.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
- B-110 execution waves are explicit and CLI-authorable\n- each child slice maps to one governance/runtime/proof concern\n- release targeting and wave status are visible in Radar and Compass\n- implementation can add focused tests without growing red-zone files

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Each child slice should strengthen the same Odylith Discipline platform: deterministic hard laws, adaptive stance, zero-credit hot paths, compact learning, subsystem integration, host parity, benchmark sovereignty, and public surface accountability.

## Impacted Components
- `odylith`

## Interface Changes
- None decided yet; record interface changes once implementation is scoped.

## Migration/Compatibility
- No migration impact recorded yet.

## Test Strategy
- Add targeted regression coverage when implementation begins.

## Open Questions
- Which existing workstreams or component specs should this attach to first?
