---
status: queued
idea_id: B-051
title: Odylith Runtime Posture Reporting Explains Wrapped Runtime Degradation
date: 2026-04-06
priority: P1
commercial_value: 4
product_impact: 5
market_value: 3
impacted_lanes: both
impacted_parts: runtime-source classification, `version` output, `doctor` messaging, and product-repo self-host posture reporting
sizing: S
complexity: Medium
ordering_score: 100
ordering_rationale: Once trust drift is bounded and repair converges, Odylith still has to explain its posture honestly. A healthy-but-wrapped result that reads like a pinned runtime is a trust bug in the operator contract.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-048
workstream_children:
workstream_depends_on: B-040,B-050
workstream_blocks:
related_diagram_ids: D-018,D-020
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
`doctor` can return healthy while `version` still reports `Runtime source:
wrapped_runtime` with only a generic fallback explanation. The live trust state
and the operator-facing posture story are not aligned.

## Customer
- Primary: maintainers and operators using `version` and `doctor` to decide
  whether the repo is truly pinned or only locally wrapped.

## Opportunity
Move runtime-source classification behind one shared status helper that consults
live trust evidence, then explain wrapped-runtime degradation directly in both
commands.

## Proposed Solution
- centralize runtime-source/status derivation
- classify trust-degraded wrapped runtime explicitly
- make `version` explain why wrapped runtime is shown
- make `doctor` report “healthy but trust-degraded” rather than implying full
  pinned health

## Scope
- install status derivation
- CLI output text
- focused status tests

## Non-Goals
- inventing a new lane model

## Risks
- too many new status labels could confuse operators more than they help

## Dependencies
- `B-040`
- `B-050`

## Success Metrics
- `version` and `doctor` agree on trust-degraded wrapped posture
- product-repo release eligibility remains fail-closed

## Validation
- `pytest -q tests/unit/test_cli.py tests/unit/runtime/test_validate_self_host_posture.py tests/integration/install/test_manager.py`

## Rollout
Ship after the trust and repair semantics are stable so the new explanation
describes real behavior, not transitional logic.

## Why Now
The current mismatch makes healthy output look more trustworthy than it is.

## Product View
Status output is part of the product contract. If it hides the difference
between pinned and merely runnable, Odylith is teaching the wrong repair story.

## Impacted Components
- `odylith`
- `dashboard`

## Interface Changes
- `odylith version` and `odylith doctor` explain wrapped-runtime degradation
  explicitly

## Migration/Compatibility
- additive status clarification only

## Test Strategy
- characterize product-repo and consumer wrapped-runtime cases separately

## Open Questions
- whether a future release should split wrapped-runtime into more than one
  visible subtype

## Outcome
- Bound to `B-051` under `B-048`.
