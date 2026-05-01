status: queued

idea_id: B-134

title: v0.1.15+ Execution Policy Adapters and Universal Action Gate

date: 2026-04-29

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: Execution Engine, Context Engine handshake, Subagent Router, Subagent Orchestrator, Remediator, harness adapters, shell/edit/tool/PR action screening, approval policy, Compass audit, Proof State, and benchmark harness-policy families

sizing: XL

complexity: VeryHigh

ordering_score: 74

ordering_rationale: Execution Engine is already the policy surface, but future enterprise claims require supported harness adapters to route high-risk actions through pre-action gates instead of only consuming advisory snapshots.

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
Odylith currently provides strong execution contracts where callers consume Context Engine packets and Execution Engine snapshots, but it is not a universal interceptor for every raw host tool call, file edit, shell command, external write, or PR action. Enterprise multi-agent workflows need consistent pre-action screening across harnesses, especially when agents can run commands, edit files, call tools, invoke subagents, or update external systems.

## Customer
Primary customers are enterprise operators and maintainers who need action-level governance for agent execution across Codex, Claude, OpenAI Agents SDK, and future harnesses. Secondary customers are reviewers who need audit trails showing that high-risk actions passed policy and proof gates before execution.

## Opportunity
Odylith can turn Execution Engine from an advisory contract into a harness-integrated action gate for supported transports. This preserves local-first semantics while giving future adapters a concrete way to enforce policy before action, approval, or external write.

## Proposed Solution
Create the workstream for v0.1.15+ Execution Policy Adapters and Universal Action Gate and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.15+ Execution Policy Adapters and Universal Action Gate.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
Supported harness adapters can call a pre-action gate and receive deterministic admissibility receipts. High-risk actions are denied or deferred when target scope, proof, approval, or policy posture is incomplete. Compass records gate decisions. Benchmarks cover false allow, false block, wrong next move, missing approval, stale proof, unsupported transport, and rollback-path gaps. Public docs clearly distinguish supported gated paths from raw host bypass paths.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Define a Universal Action Gate contract for supported adapters. Actions such as shell command, file edit, apply patch, tool call, external write, commit, PR, hosted sync, and subagent delegation should carry intent, actor, workspace, target resources, policy pack, proof posture, and rollback/validation expectation. Execution Engine returns admit, deny, or defer with nearest recovery and validation receipts. Unsupported raw host paths must stay explicitly out of claim scope.

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
