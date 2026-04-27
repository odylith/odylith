---
status: finished
idea_id: B-075
title: Frontier Extraction, User-Correction Invariants, and Critical-Path Modes
date: 2026-04-09
priority: P1
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: frontier derivation, execution-mode gating, user-correction invariants, and critical-path budget policy
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Once admissibility exists, Odylith still needs one canonical frontier and explicit critical-path mode so execution does not collapse back into open-ended exploration. This wave turns the contract into a truthful current-state runtime.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-12-frontier-extraction-user-correction-invariants-and-critical-path-modes.md
execution_model: standard
workstream_type: child
workstream_parent: B-072
workstream_children:
workstream_depends_on: B-074
workstream_blocks: B-076,B-077
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
Even with better policy, the product can still reason from stale memory instead
of one current frontier. It also lacks explicit `explore`, `implement`,
`verify`, and `recover` execution modes that budget exploration differently.

## Customer
- Primary: operators who need the system to act from the current truth state.
- Secondary: coding agents that need one canonical next move instead of
  replaying search from scratch.

## Opportunity
Make execution state resumable, truthful, and mode-aware.

## Proposed Solution
- derive one `ExecutionFrontier` after starts, reruns, failures, and
  corrections
- materialize explicit execution modes with tighter exploration budgets in
  `verify` and `recover`
- preserve promoted user corrections as invariants when frontier recomputes

## Scope
- frontier payload
- execution mode policy
- user-correction invariant carry-forward

## Non-Goals
- external dependency adapters
- closure analysis

## Risks
- frontier derivation could over-trust stale evidence
- critical-path mode could be too permissive to matter

## Dependencies
- `B-074`

## Success Metrics
- one truthful next move is always derivable
- verify/recover modes deny or budget side exploration explicitly

## Validation
- frontier recomputation and mode-gating tests

## Rollout
Land after admissibility so the frontier drives real decisions.

## Why Now
Execution governance fails if the policy engine still acts from stale context.

## Product View
Frontier is the runtime "current truth" layer for governed execution.

## Impacted Components
- `execution-governance`
- `proof-state`
- `delivery-intelligence`

## Interface Changes
- additive frontier and execution-mode contracts

## Migration/Compatibility
- additive; no existing surfaces lose data

## Test Strategy
- frontier and mode-focused unit tests

## Open Questions
- whether critical-path mode should eventually integrate proof-state severity
  directly
