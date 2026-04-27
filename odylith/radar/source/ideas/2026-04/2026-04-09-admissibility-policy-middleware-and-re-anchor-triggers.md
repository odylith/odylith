---
status: finished
idea_id: B-074
title: Admissibility Policy Middleware and Re-Anchor Triggers
date: 2026-04-09
priority: P1
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: admissibility policy engine, tool-call middleware, re-anchor policy, nearest admissible alternative suggestions, and host-aware action hints
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Admissibility screening is the biggest single product improvement because it blocks the wrong next move before the tool call happens. It depends on the contract layer and should land immediately after it.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-12-admissibility-policy-middleware-and-re-anchor-triggers.md
execution_model: standard
workstream_type: child
workstream_parent: B-072
workstream_children:
workstream_depends_on: B-073
workstream_blocks: B-075
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
Odylith still lets agents invoke technically valid but procedurally wrong
commands because no policy middleware evaluates admissibility against an active
execution contract before the action runs.

## Customer
- Primary: operators who want non-admissible next actions blocked upfront.
- Secondary: agent hosts that need one truthful "why not this nearby command"
  answer.

## Opportunity
Move from soft guidance to a hard `admit|deny|defer` execution-policy gate.

## Proposed Solution
- evaluate every intended action against the active execution contract
- return violated preconditions and the nearest admissible alternative
- auto-trigger re-anchor after repeated denials, contradictory evidence, or
  multiple off-contract actions
- keep host/model-specific command hints behind the detected host profile
  rather than embedding them into the shared decision contract

## Scope
- admissibility decision primitives
- re-anchor trigger policy
- alternative suggestion contract

## Non-Goals
- replacing execution planning
- replacing host capability detection

## Risks
- deny policy could be too coarse and block truthful work
- host-specific affordances could leak into the shared policy canon

## Dependencies
- `B-073`

## Success Metrics
- non-admissible actions return structured denies instead of executing
- repeated off-contract drift forces a re-anchor step

## Validation
- unit tests for `admit`, `deny`, `defer`, and re-anchor triggers

## Rollout
Land after the task-contract wave so policy has a stable input.

## Why Now
This is the highest-leverage correction to Odylith's current failure mode.

## Product View
Admissibility is the first hard execution guardrail, not a doc note.

## Impacted Components
- `execution-governance`

## Interface Changes
- additive admissibility decision contract

## Migration/Compatibility
- additive; existing execution-wave programs stay intact

## Test Strategy
- direct policy decision coverage

## Open Questions
- how strict the first re-anchor thresholds should be before operator tuning
