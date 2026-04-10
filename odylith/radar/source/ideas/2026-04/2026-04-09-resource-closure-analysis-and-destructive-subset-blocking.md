---
status: queued
idea_id: B-076
title: Resource Closure Analysis and Destructive-Subset Blocking
date: 2026-04-09
priority: P1
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: resource graph, closure classification, destructive subset detection, and blast-radius explanation
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Closure analysis is how the execution engine blocks technically valid but incomplete destructive subsets before they execute. It should land once frontier and mode posture exist.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-072
workstream_children:
workstream_depends_on: B-075
workstream_blocks: B-078
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
Agents still operate on subsets without understanding closure, dependencies, or
destructive side effects because Odylith does not compute safe vs incomplete vs
destructive scope.

## Customer
- Primary: operators who need destructive subset mistakes blocked before the
  command runs.

## Opportunity
Turn closure and blast radius into computed contract, not operator intuition.

## Proposed Solution
- add `ResourceClosure` and a minimal resource graph
- classify requested subsets as `safe`, `incomplete`, or `destructive`
- explain blast radius for path scopes, workstream sets, release members,
  benchmark families/shards, and test matrices

## Scope
- closure types and classifier
- first-domain resource graph helpers

## Non-Goals
- full graph coverage for every external platform

## Risks
- too much inferred topology could produce false destructive warnings

## Dependencies
- `B-075`

## Success Metrics
- destructive subset operations are blocked before execution
- incomplete scopes are surfaced explicitly

## Validation
- resource-closure classification tests

## Rollout
Land after frontier and mode so closure decisions have contextual state.

## Why Now
Partial-scope mistakes are one of the main execution failure classes the product
needs to prevent.

## Product View
Closure is how execution governance becomes safer than command validity alone.

## Impacted Components
- `execution-governance`

## Interface Changes
- additive resource-closure contract

## Migration/Compatibility
- additive classification and explanation only

## Test Strategy
- closure and destructive-subset unit tests

## Open Questions
- which topology sources should seed the first resource graph outside repo-local
  path and workstream truth
