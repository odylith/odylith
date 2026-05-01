status: queued

idea_id: B-130

title: v0.1.15+ Harness-Neutral Run Trace and Artifact Contract

date: 2026-04-29

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: Harness adapter boundary, OpenAI Agents SDK adapter, LangGraph and AgentCore future adapters, Compass timeline, Execution Engine receipts, Memory Contracts, benchmark runner, artifact provenance, and trace import validation

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Odylith needs a neutral harness contract before integrating more SDKs or importing traces, otherwise every adapter will define run state, handoffs, memory events, approvals, and artifacts differently.

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
Agent platforms expose overlapping but incompatible concepts: runs, traces, spans, handoffs, guardrails, tool calls, sandbox manifests, memory updates, approvals, checkpoints, artifacts, and long-running resumability. Odylith already has Context Engine packets, Execution Engine receipts, Compass streams, and Memory Contracts, but it lacks a harness-neutral interface that maps external run evidence into those surfaces without letting vendor-specific trace schemas become source truth.

## Customer
Primary customers are maintainers adding OpenAI Agents SDK, LangGraph, AgentCore, or other harness adapters. Secondary customers are enterprise operators who need imported trace and artifact evidence to be auditable, comparable, and governed across agent runtimes.

## Opportunity
A neutral contract lets Odylith integrate fast-moving harnesses while keeping stable product semantics. OpenAI Agents SDK can be the first adapter, but the same run, trace, approval, memory, and artifact model can later support LangGraph checkpoints, AgentCore runtime traces, MCP tool sessions, and A2A task lifecycles.

## Proposed Solution
Create the workstream for v0.1.15+ Harness-Neutral Run Trace and Artifact Contract and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.15+ Harness-Neutral Run Trace and Artifact Contract.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
A harness-neutral schema exists with at least one OpenAI Agents SDK mapping. Compass can project imported run evidence without treating it as repo truth. Execution Engine can attach admissibility receipts to harness runs. Memory Contracts can compact harness memory events without leaking secrets or raw transcripts. Benchmarks can compare harness traces across providers using the same evidence fields.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Define HarnessRun, HarnessTrace, HarnessSpan, HarnessHandoff, HarnessApproval, HarnessMemoryEvent, HarnessArtifact, and HarnessEnvironment as Odylith-owned concepts. External schemas should map into these concepts, then into Compass, Execution Engine, Memory Contracts, and benchmark evidence. The contract must be provenance-rich, redaction-aware, and explicit about authoritative versus observational fields.

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
