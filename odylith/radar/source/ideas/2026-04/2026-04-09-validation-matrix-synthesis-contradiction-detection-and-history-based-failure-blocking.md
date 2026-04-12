---
status: finished
idea_id: B-078
title: Validation Matrix Synthesis, Contradiction Detection, and History-Based Failure Blocking
date: 2026-04-09
priority: P1
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: validation synthesis, contradiction records, casebook-backed preflight blocking, and operator-facing execution-governance readouts
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: This wave closes the loop by turning known failure classes, contradictions, and validation obligations into executable product behavior instead of searchable memory. It depends on closure and receipts so the engine can reason from real scope and state.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-12-validation-matrix-synthesis-contradiction-detection-and-history-based-failure-blocking.md
execution_model: standard
workstream_type: child
workstream_parent: B-072
workstream_children:
workstream_depends_on: B-076,B-077
workstream_blocks:
related_diagram_ids: D-030,D-031
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
Odylith still relearns known failure classes from live failure, and it does not
yet synthesize one minimum validation matrix or contradiction record from the
active execution contract.

## Customer
- Primary: operators who want known failure classes blocked before execution.
- Secondary: product surfaces that need one shared answer for validation and
  contradiction posture.

## Opportunity
Promote historical failure knowledge and active contradictions into executable
preflight policy.

## Proposed Solution
- add `ValidationMatrix` and `ContradictionRecord`
- synthesize minimal validation obligations from the active contract
- detect contradictions across user instruction, governed docs, live state, and
  intended action
- turn Casebook-known failure patterns into preflight rules
- surface contract, frontier, admissibility, closure, waits, and resumes in
  Shell, Compass, and packet outputs

## Scope
- validation synthesis
- contradiction detection
- history-based blocking hooks

## Non-Goals
- replacing human review for novel failure classes

## Risks
- contradiction rules could become noisy if evidence freshness is too loose

## Dependencies
- `B-076`
- `B-077`

## Success Metrics
- repeated rediscovery count drops
- validation obligations are explicit and minimal instead of ad hoc

## Validation
- validation matrix, contradiction, and history-rule tests

## Rollout
Land after closure and receipt posture are available.

## Why Now
This is how the engine converts lessons learned into durable product blocking
behavior.

## Product View
Known failure classes should be prevented, not rediscovered.

## Impacted Components
- `execution-governance`
- `casebook`
- `compass`
- `dashboard`

## Interface Changes
- additive validation and contradiction contracts

## Migration/Compatibility
- additive and fail-closed

## Test Strategy
- focused preflight blocking and contradiction coverage

## Open Questions
- how much of the first validation matrix should be rendered directly in shell
  vs packet-only detail
