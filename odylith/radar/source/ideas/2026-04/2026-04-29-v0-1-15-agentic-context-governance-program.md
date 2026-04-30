status: queued

idea_id: B-128

title: v0.1.15+ Agentic Context Governance Program

date: 2026-04-29

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: Context Engine, Execution Engine, Memory Backend, Memory Contracts, Subagent Router, Subagent Orchestrator, Compass, Radar, Atlas, Registry, Casebook, Dashboard, benchmark, harness adapters, MCP and A2A protocol boundaries, enterprise policy packs, collaboration identity, durable annotations, and optional hosted augmentation

sizing: XL

complexity: VeryHigh

ordering_score: 74

ordering_rationale: Enterprise agent platforms are converging on memory, traces, guardrails, durable execution, sandboxed harnesses, MCP tool access, A2A interoperability, and AgentOps governance. Odylith needs a v0.1.15+ umbrella that turns that ecosystem movement into a repo-authoritative governed context program instead of scattering follow-up work across harness-specific records.

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
Agent harnesses and enterprise orchestration platforms are adding memory, traces, guardrails, approvals, sandboxing, long-running execution, MCP tool access, A2A interoperability, and hosted AgentOps surfaces, but none of those primitives by themselves establish durable repo truth about business intent, component boundaries, ownership, proof obligations, policy posture, or engineering decisions. Without a coordinated Odylith program, future harness adapters can each import their own partial context model, creating fragmented memory, duplicated policy, inconsistent execution gates, and weak public claims about multi-agent continuity.

## Customer
Primary customers are Odylith maintainers and serious engineering teams using Codex, Claude Code, OpenAI Agents SDK, LangGraph, AWS AgentCore, MCP tools, A2A agents, or comparable harnesses against complex repositories. Secondary customers are enterprise operators who need humans and specialized agents to share durable intent, policy, state, ownership, proof, and audit trails without making a hosted service the authority over repo-local governance truth.

## Opportunity
Odylith can own the missing control plane between raw model capability and generic agent orchestration: a local-first, repo-authoritative context governance layer that gives any harness the same context graph, admissible next moves, policy obligations, memory hygiene, proof requirements, and audit surfaces. This creates a differentiated path from v0.1.15 onward: harnesses provide execution primitives, while Odylith provides durable repo judgment and benchmark-proved continuity across those primitives.

## Proposed Solution
Create the workstream for v0.1.15+ Agentic Context Governance Program and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.15+ Agentic Context Governance Program.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
A release-bound program exists with child workstreams for architecture, context graph, harness contracts, collaboration memory, policy packs, protocol interop, security, benchmarks, and surfaces. Every child has a clear owned component set, proof obligation, and release target posture. Odylith can describe how business intent, task state, dependencies, ownership, policy, compliance expectations, traces, and proof artifacts flow through Context Engine, Execution Engine, Memory, Compass, Radar, Registry, Atlas, and Casebook without relying on any single harness or hosted platform. No public claim ships until benchmark families prove context continuity, handoff fidelity, policy correctness, memory integrity, trace completeness, and cost posture.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Treat this as the v0.1.15+ umbrella for governed shared context across agent harnesses. Odylith should stay local-first and source-truth bounded: tracked repo governance remains authoritative, .odylith runtime state remains derived or transient, hosted augmentation remains optional, and protocol adapters must consume or emit compact governed evidence rather than becoming new sources of truth. The program should coordinate component boundaries, Atlas topology, context graph design, harness-neutral contracts, enterprise connectors, policy packs, security posture, benchmarks, and release-gated public narrative.

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
