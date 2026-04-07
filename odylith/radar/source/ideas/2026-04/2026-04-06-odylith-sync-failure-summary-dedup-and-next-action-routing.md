---
status: queued
idea_id: B-054
title: Odylith Sync Failure Summary Dedup and Next-Action Routing
date: 2026-04-06
priority: P1
commercial_value: 4
product_impact: 5
market_value: 3
impacted_lanes: both
impacted_parts: sync failure UX, duplicate error collapsing, failure-class routing, and operator guidance
sizing: S
complexity: Medium
ordering_score: 100
ordering_rationale: Even once sync can normalize legacy Radar truth, operators still need a compact explanation when something real remains broken. Recommending the same forced command after it already failed is a product-clarity miss.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-048
workstream_children:
workstream_depends_on: B-053
workstream_blocks:
related_diagram_ids: D-004,D-006
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
Current sync failures can dump hundreds of lines, repeat duplicates, and then
recommend rerunning a command that already failed with the same blocker.

## Customer
- Primary: operators using `odylith sync` as the main governed refresh path.

## Opportunity
Summarize top unique failure classes, count duplicates, and route operators to
the next distinct action based on what actually failed.

## Proposed Solution
- collapse duplicate validation errors into a top-N summary
- keep file anchors and representative examples
- route next actions by failure class instead of one static retry string

## Scope
- sync CLI messaging
- failure classification helpers
- focused CLI tests

## Non-Goals
- changing validation semantics themselves

## Risks
- too much collapsing could hide useful specifics

## Dependencies
- `B-053`

## Success Metrics
- sync failures show a compact deduped summary
- next actions differ between legacy-normalization failure, remaining contract
  failure, and repair-needed runtime failure

## Validation
- `pytest -q tests/unit/test_cli.py tests/unit/runtime/test_sync_cli_compat.py`

## Rollout
Land after the normalizer so the summary logic targets remaining real failures.

## Why Now
The reported rerun guidance was wrong in exactly the case it was trying to
help.

## Product View
Operator guidance has to respond to the failure that happened, not to the one
Odylith was hoping for.

## Impacted Components
- `odylith`
- `radar`

## Interface Changes
- sync failure output becomes deduped and next-action aware

## Migration/Compatibility
- output-only improvement

## Test Strategy
- assert duplicate counts, representative errors, and next-action routing

## Open Questions
- whether later work should expose the full collapsed error JSON in a saved
  report file as well as the terminal summary

## Outcome
- Bound to `B-054` under `B-048`.
