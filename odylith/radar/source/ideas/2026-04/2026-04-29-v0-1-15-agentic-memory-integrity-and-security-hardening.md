status: queued

idea_id: B-138

title: v0.1.15+ Agentic Memory Integrity and Security Hardening

date: 2026-04-29

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: Memory Backend, Memory Contracts, Context Engine, policy packs, connector ingestion, MCP/A2A metadata, skill/tool provenance, secret suppression, snapshot integrity, rollback, Casebook, benchmark security families, and validation commands

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Persistent agent memory is a high-value attack surface; Odylith must harden memory integrity before expanding collaboration, connector, or hosted-memory inputs.

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
Shared memory can be poisoned by prompt injection, hostile tool metadata, malicious remote agents, compromised connector inputs, stale summaries, or accidental secret retention. Odylith already suppresses sensitive paths and retains compact judgment memory, but the v0.1.15+ program needs a broader memory-integrity lane aligned with agentic security risks, including tamper evidence, retention policy, provenance validation, rollback, and anomaly detection for memory changes.

## Customer
Primary customers are maintainers and enterprise security reviewers who need durable memory to be trustworthy before agents act on it. Secondary customers are operators who need safe recovery when memory is stale, poisoned, malformed, or contradicted by source truth.

## Opportunity
Memory integrity can become a major differentiator for Odylith. Instead of treating memory as a passive vector store, Odylith can make it governed, provenance-aware, policy-bound, and benchmark-tested against poisoning and leakage.

## Proposed Solution
Create the workstream for v0.1.15+ Agentic Memory Integrity and Security Hardening and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.15+ Agentic Memory Integrity and Security Hardening.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
Validation detects secret-bearing memory, untrusted durable refs, malformed actor/workspace ids, suspicious large memory deltas, protected-field rewrites, stale external summaries, and contradiction drift. Memory snapshots expose integrity posture and rollback anchors. Benchmarks cover memory poisoning, sensitive data leakage, prompt-injected annotations, malicious tool metadata, and stale summary replay. Casebook captures any memory-integrity failure with repro evidence.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Extend Memory Backend and Memory Contracts with integrity metadata, source-class policy, trust classes, compact fingerprints, protected memory areas, malformed update rejection, rollback to known-good snapshots, and explicit stale/contradicted posture. Connector, MCP, A2A, and harness memory events must pass through this membrane before influencing packets or durable judgment memory.

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
