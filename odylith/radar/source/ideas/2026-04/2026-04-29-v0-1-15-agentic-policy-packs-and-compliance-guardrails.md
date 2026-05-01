status: queued

idea_id: B-137

title: v0.1.15+ Agentic Policy Packs and Compliance Guardrails

date: 2026-04-29

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: Execution Engine policy, Memory Contracts, harness adapters, MCP/A2A boundary, enterprise connectors, approval gates, release/public-claim policy, data classification, retention, audit, Dashboard, Compass, and validation commands

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Enterprise multi-agent systems fail without explicit policy alignment. Odylith should package policy as governed, testable packs instead of burying compliance expectations in prompts or adapter code.

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
Agents need to understand which actions require approval, which data can enter memory, which tools are allowed, which external writes are prohibited, which claims need benchmark proof, and which compliance expectations apply. Today those expectations are spread across guidance, component specs, Execution Engine logic, Memory Contracts, and release policy. Future enterprise use needs policy packs that are explicit, composable, validated, and harness-facing.

## Customer
Primary customers are enterprise teams that need agent behavior to respect data handling, approval, compliance, release, and audit requirements. Secondary customers are maintainers who need one governed way to extend policy without duplicating hard laws across runtime components.

## Opportunity
Policy packs can make Odylith's governance portable across harnesses and protocols. A repo can apply a production-change pack, data-classification pack, public-claim pack, PII/secrets pack, dependency-risk pack, or external-write pack and have Context Engine, Execution Engine, Memory, connectors, and adapters consume the same contract.

## Proposed Solution
Create the workstream for v0.1.15+ Agentic Policy Packs and Compliance Guardrails and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.15+ Agentic Policy Packs and Compliance Guardrails.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
At least three built-in policy packs exist: data and memory safety, production/external write approval, and public claim/release proof. Validation catches contradictory or incomplete pack rules. Execution Engine gate decisions cite pack obligations. Memory compaction honors retention/redaction rules. Benchmarks cover policy false allows, false blocks, stale policy, missing approval, and cross-harness parity.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Introduce policy packs as repo-local governed configuration with validation. Packs define action classes, resource classes, memory retention rules, approval gates, validation obligations, connector permissions, protocol trust classes, and public-claim proof gates. Execution Engine should consume pack summaries for admissibility; Memory Contracts should consume retention and redaction rules; adapters should expose pack-driven action gates.

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
