status: queued

idea_id: B-118

title: v0.1.12 Governed Harness: Agent SDK Control Plane And Deep Benchmark Proof

date: 2026-04-18

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: Radar backlog, Benchmark, Context Engine, Execution Engine, Proof State, Compass, Casebook, Registry, Atlas, OpenAI Agents SDK adapter strategy

sizing: XL

complexity: High

ordering_score: 83

ordering_rationale: Queued through `odylith backlog create` from the current maintainer lane.

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
Agent harnesses now provide execution primitives such as tools, approvals, guardrails, tracing, resumability, and sandboxed runs, but repos still need durable engineering judgment about the correct slice, component boundaries, admissible moves, proof obligations, bug memory, and artifacts that survive across sessions. Odylith needs a queued v0.1.12 strategy that captures this Governed Harness direction without disturbing the active v0.1.11 release lane.

## Customer
Odylith maintainers and operators using Codex, Claude Code, OpenAI Agents SDK, or another agent harness against serious repositories where agent execution must stay grounded in repo-local governance truth.

## Opportunity
Queue v0.1.12 around Odylith as the repo-governance control plane for any agent harness, with OpenAI Agents SDK as the first explicit adapter target and deep benchmark proof as the first release gate.

## Proposed Solution
Create the workstream for v0.1.12 Governed Harness: Agent SDK Control Plane And Deep Benchmark Proof and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.12 Governed Harness: Agent SDK Control Plane And Deep Benchmark Proof.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
The v0.1.12 Governed Harness umbrella and its wave-slice backlog records remain queued; W1 establishes deep benchmark coverage before implementation claims; every later slice carries an explicit benchmark gate; no program activation, release assignment, or public harness claim occurs until v0.1.11 closes and release proof is intentionally started.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Agents SDK gives the harness. Odylith gives that harness durable repo judgment: the right context packet, workstream state, component boundaries, bug memory, admissible next moves, proof requirements, and governed artifacts. The v0.1.12 lane should remain benchmark-first and queued until v0.1.11 closes.

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
