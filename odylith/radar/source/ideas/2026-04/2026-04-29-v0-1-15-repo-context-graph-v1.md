status: queued

idea_id: B-131

title: v0.1.15+ Repo Context Graph v1

date: 2026-04-29

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: Context Engine projections, Projection Bundle, Projection Snapshot, Memory Backend, Memory Contracts, Radar traceability, Registry component graph, Atlas catalog, Casebook links, Compass runtime, Dashboard navigation, and benchmark context-continuity families

sizing: XL

complexity: VeryHigh

ordering_score: 74

ordering_rationale: The shared-context program needs one durable graph model for intent, work, ownership, dependencies, policy, proof, and artifacts before enterprise connectors or hosted augmentation start adding more inputs.

confidence: high

founder_override: no

promoted_to_plan: 

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
Odylith currently compiles several strong read models, but business intent, task state, ownership, dependencies, policy expectations, compliance obligations, proof artifacts, harness runs, and decisions are not yet represented as one explicit context graph. Without that graph, multi-agent handoffs can still lose why a task exists, which component owns it, what proof is required, what policy applies, and which artifacts are authoritative.

## Customer
Primary customers are coding agents and maintainers who need a compact but complete handoff model across sessions, workstreams, components, and harnesses. Secondary customers are enterprise reviewers who need to audit how an agent decision was grounded in intent, policy, dependencies, and proof.

## Opportunity
A first-class Context Graph lets Odylith become the durable memory and coordination layer for engineering work. It can power packets, Compass readouts, Atlas diagrams, benchmark scenarios, collaboration memory, enterprise connectors, and protocol adapters from one governed model rather than ad hoc joins.

## Proposed Solution
Create the workstream for v0.1.15+ Repo Context Graph v1 and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.15+ Repo Context Graph v1.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
Context Engine can emit a context-graph payload and derive packet evidence from it. Projection Bundle and Snapshot include graph-ready documents and edges. Memory Backend can retain compact graph-derived judgment without raw thread pollution. Radar, Registry, Atlas, Compass, and Casebook can cross-link through graph identifiers. Benchmarks prove that graph-backed packets reduce lost requirements, wrong-owner handoffs, stale dependency use, and missing proof obligations.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Add Context Graph v1 as a derived, rebuildable read model compiled from tracked truth plus compact runtime evidence. The graph should include typed nodes for intent, task, workstream, plan, component, bug, diagram, policy, owner, actor, workspace, harness run, trace, artifact, proof, dependency, decision, annotation, and external source summary. Edges should preserve provenance and freshness so packet compaction can prefer durable decisions over raw conversation history.

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
