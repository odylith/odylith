status: queued

idea_id: B-135

title: v0.1.15+ MCP and A2A Governed Protocol Boundary

date: 2026-04-29

priority: P0

commercial_value: 5

product_impact: 4

market_value: 5

impacted_parts: MCP tool context boundary, A2A agent communication boundary, harness adapters, Context Engine, Execution Engine, Memory Contracts, policy packs, connector security, Registry specs, Atlas diagrams, and protocol benchmark fixtures

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: MCP and A2A are becoming ecosystem protocols, but Odylith needs a governed boundary that treats them as inputs and transports rather than authority over repo truth or internal memory.

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
MCP standardizes access to tools and external systems, while A2A standardizes communication between independent agents. Both can improve interoperability, but both can also introduce untrusted metadata, tool confusion, prompt injection, overbroad permissions, opaque remote agents, and memory leakage. Odylith lacks an explicit protocol boundary that governs what MCP and A2A data can influence, what they may execute, and how their evidence enters Context Engine, Execution Engine, and Memory Contracts.

## Customer
Primary customers are teams connecting Odylith-governed repos to MCP servers, A2A agents, and enterprise tool gateways. Secondary customers are security and platform reviewers who need clear trust boundaries for tool access, remote agent collaboration, and cross-system context exchange.

## Opportunity
A governed MCP/A2A boundary lets Odylith participate in the emerging protocol ecosystem without inheriting its unsafe defaults. Odylith can expose context and policy envelopes, validate remote capabilities, suppress untrusted memory writes, and require action gates for tool use or agent-to-agent task execution.

## Proposed Solution
Create the workstream for v0.1.15+ MCP and A2A Governed Protocol Boundary and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.15+ MCP and A2A Governed Protocol Boundary.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
Odylith can parse and classify MCP tool metadata and A2A agent/task metadata into safe compact evidence. Policy packs can deny risky tools, untrusted remote agents, lookalike capabilities, and memory-write attempts. Context packets can include protocol-derived context only with provenance and trust class. Benchmarks cover malicious tool descriptions, remote-agent overclaiming, context exfiltration attempts, stale capability data, and unsupported protocol modes.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Define MCP as tool/context access and A2A as agent-to-agent task communication. Neither protocol becomes authoritative. Odylith should validate tool and agent metadata, bind capabilities to policy packs, redact sensitive context, require provenance on imported evidence, and record protocol interactions as compact observational artifacts. Atlas should show the protocol boundary separately from the local context graph and execution gate.

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
