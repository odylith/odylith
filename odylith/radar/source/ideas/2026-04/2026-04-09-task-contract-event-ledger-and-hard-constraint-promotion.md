---
status: finished
idea_id: B-073
title: Task Contract, Event Ledger, and Hard-Constraint Promotion
date: 2026-04-09
priority: P1
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: execution contract schema, task event ledger, hard-constraint mutation, user-correction capture, host profile detection, and execution-governance state transitions
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: The execution-governance package needs one canonical state model before any admissibility or frontier policy can be trustworthy. This workstream establishes the typed contract and event-sourced execution ledger the rest of the engine depends on.
confidence: high
founder_override: yes
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-12-task-contract-event-ledger-and-hard-constraint-promotion.md
execution_model: standard
workstream_type: child
workstream_parent: B-072
workstream_children:
workstream_depends_on:
workstream_blocks: B-074,B-075,B-079
related_diagram_ids: D-030
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Odylith has no single typed task contract that survives user corrections,
external events, retries, and policy decisions. The current state lives across
memory, prompts, and tool outputs, which makes execution governance too soft.

## Customer
- Primary: operators who need corrections like "use only this lane" to become
  hard constraints immediately.
- Secondary: downstream execution-governance waves that need one event-sourced
  state model instead of ambient prompt memory.

## Opportunity
Create one append-only task ledger and one machine-readable execution contract
that future policy, frontier, contradiction, and receipt systems can trust.

## Proposed Solution
- add `ExecutionContract`, `HardConstraint`, `ExecutionEvent`, and
  `ExecutionHostProfile` contracts
- record user corrections, policy decisions, tool intents, tool outcomes, and
  external dependency updates as append-only events
- promote user corrections into explicit hard constraints instead of leaving
  them as narrative guidance
- keep the base contract host-general across Codex and Claude Code while
  recording the detected host and model-family profile additively

## Scope
- execution contract schema
- append-only event ledger shape
- hard-constraint mutation helpers
- host/model-family detection envelope for later policy use

## Non-Goals
- full policy enforcement
- full external dependency adapter coverage
- CLI ergonomics by themselves

## Risks
- overfitting the contract to one host instead of keeping the shared shape
  general
- treating user corrections as log-only instead of invariant-bearing events

## Dependencies
- parent umbrella `B-072`

## Success Metrics
- user corrections become visible hard constraints in the active contract
- the execution ledger can replay contract state deterministically
- host/model detection is explicit without becoming the shared policy surface

## Validation
- unit tests for contract mutation and host-profile recording

## Rollout
Land the types and ledger first so later waves can reuse them.

## Why Now
Without one typed contract, the rest of the execution-governance plan would be
heuristic glue.

## Product View
This is the schema foundation for the whole execution-governance engine.

## Impacted Components
- `execution-governance`

## Interface Changes
- additive execution contract and event-ledger types

## Migration/Compatibility
- additive; no existing contract is removed

## Test Strategy
- direct contract round-trip coverage

## Open Questions
- whether the first persisted ledger should live under `.odylith/` or stay
  source-local until runtime integration deepens
