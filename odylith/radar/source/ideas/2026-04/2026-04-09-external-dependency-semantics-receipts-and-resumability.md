---
status: queued
idea_id: B-077
title: External Dependency Semantics, Receipts, and Resumability
date: 2026-04-09
priority: P1
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: external dependency adapters, semantic wait-state normalization, typed receipts, resume handles, and rerun reattachment policy
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Opaque waiting and replay-from-scratch behavior undermine execution trust even when the agent stayed on the right lane. This wave adds semantic wait states and typed resumability after the frontier exists.
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
Odylith still renders too much external work as generic `running` state and
reruns often rediscover work that already has a resumable handle.

## Customer
- Primary: operators who need truthful wait-state visibility and trustworthy
  resume semantics.

## Opportunity
Normalize external execution state into meaningful product truth and make
receipts first-class.

## Proposed Solution
- add `ExternalDependencyState`, `SemanticReceipt`, and `ResumeHandle`
- normalize local long-running commands, Compass/agent-stream activity, and
  GitHub Actions into semantic wait states
- default reruns to receipt reattachment instead of replay from scratch

## Scope
- receipt and resume-handle types
- semantic wait-state mapping
- initial external adapter stubs

## Non-Goals
- exhaustive provider coverage in v1

## Risks
- weak semantic mapping could over-promise what an external adapter really
  knows

## Dependencies
- `B-075`

## Success Metrics
- semantic wait coverage increases
- reruns reattach by default when a receipt exists

## Validation
- semantic wait-state and receipt reattach tests

## Rollout
Land in parallel with closure after frontier derivation exists.

## Why Now
Opaque waiting and replay-from-scratch are trust killers for governed
execution.

## Product View
Receipts make execution continuity durable instead of accidental.

## Impacted Components
- `execution-governance`
- `compass`

## Interface Changes
- additive external dependency and receipt contracts

## Migration/Compatibility
- additive state normalization and receipt emission

## Test Strategy
- wait-state and resumability-focused unit tests

## Open Questions
- which external ids should become first-class links in Compass and packets
