---
status: queued
idea_id: B-055
title: Odylith Lifecycle Plan Dirty Overlap Summary Defaults
date: 2026-04-06
priority: P2
commercial_value: 3
product_impact: 4
market_value: 2
impacted_lanes: both
impacted_parts: install and sync lifecycle-plan output, dirty-overlap summarization, and verbose-mode expansion
sizing: S
complexity: Low
ordering_score: 100
ordering_rationale: The dirty-overlap dump is not the main functional blocker, but it makes migration and release output much harder to read exactly when operators are already trying to understand a failure.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-048
workstream_children:
workstream_depends_on: B-030,B-054
workstream_blocks:
related_diagram_ids: D-018
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
Lifecycle plans currently print the full dirty-overlap listing by default,
which floods the operator with generated and expected local paths during
install, reinstall, and sync.

## Customer
- Primary: operators reading lifecycle plans in the terminal.

## Opportunity
Default to counts plus representative paths, then keep the full listing behind
an explicit verbose mode.

## Proposed Solution
- summarize dirty overlap by count and a few sample paths
- add `--verbose` to print the full listing
- keep plan output stable and machine-readable enough for tests

## Scope
- lifecycle-plan printers in CLI and sync helpers
- focused CLI tests

## Non-Goals
- changing which paths are considered dirty overlap

## Risks
- sampling could omit the one path the operator cares about most

## Dependencies
- `B-030`
- `B-054`

## Success Metrics
- default lifecycle plans show concise overlap summaries
- `--verbose` restores the full listing

## Validation
- `pytest -q tests/unit/test_cli.py tests/unit/runtime/test_sync_cli_compat.py`

## Rollout
Ship alongside the sync-summary cleanup so the operator output gets quieter in
one pass.

## Why Now
This noise showed up directly in the reported migration logs.

## Product View
If Odylith wants people to trust the plan output, it needs to summarize signal,
not print the whole working tree back at them.

## Impacted Components
- `odylith`
- `dashboard`

## Interface Changes
- install, reinstall, and sync plans default to compact dirty-overlap summaries
- `--verbose` prints the full overlap list

## Migration/Compatibility
- output-only change

## Test Strategy
- assert default compact output and verbose full output separately

## Open Questions
- whether later work should classify dirty overlap by source versus generated
  paths

## Outcome
- Bound to `B-055` under `B-048`.
