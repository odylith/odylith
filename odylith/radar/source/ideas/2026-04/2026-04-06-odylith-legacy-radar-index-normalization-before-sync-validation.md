---
status: queued
idea_id: B-053
title: Legacy Radar Index Normalization Before Sync Validation
date: 2026-04-06
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: legacy Radar upgrader, backlog rationale normalization, sync preflight, and strict backlog-contract gating
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Once the runtime itself is recoverable, the next hard blocker is that migrated repos can still fail `sync` immediately on legacy Radar truth. Odylith should bridge that source format once before enforcing the stricter contract.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-048
workstream_children:
workstream_depends_on: B-030
workstream_blocks: B-054
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
Migrated Radar `INDEX.md` files can still use older rationale formats that do
not satisfy the stricter current backlog contract. `odylith sync` then fails
immediately even though the legacy structure is mechanically normalizable.

## Customer
- Primary: operators expecting `sync` to work right after migration.

## Opportunity
Bridge legacy Radar structure once before strict validation so `sync` can move
from migration into governed steady state without a manual rationale surgery
step.

## Proposed Solution
- add a legacy Radar normalizer that only backfills missing required bullets
- preserve existing prose and authored reasoning
- synthesize missing rationale bullets from current backlog-authoring defaults
- backfill missing `ranking basis` plus review checkpoint for manual overrides
- run this normalization automatically once before strict sync validation

## Scope
- Radar `INDEX.md` normalization helpers
- sync preflight integration
- focused validation tests

## Non-Goals
- reordering the backlog automatically
- rewriting authored rationale that already satisfies the contract

## Risks
- normalization could accidentally overwrite deliberate authored text

## Dependencies
- `B-030`

## Success Metrics
- migrated legacy Radar files normalize once and then pass strict validation
- authored rationale is preserved when already contract-complete

## Validation
- `pytest -q tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_backlog_authoring.py tests/unit/runtime/test_sync_cli_compat.py`

## Rollout
Land the normalizer before sync-summary cleanup so the main reported failure
class becomes fixable in one run.

## Why Now
The reported downstream repo proves the stricter contract is landing before the
migration bridge.

## Product View
Stricter truth is good, but only after Odylith can actually carry old truth
into the new contract.

## Impacted Components
- `radar`
- `odylith`

## Interface Changes
- `odylith sync` auto-normalizes legacy Radar rationale before strict
  validation

## Migration/Compatibility
- additive compatibility bridge for legacy Radar source

## Test Strategy
- use real legacy `INDEX.md` fixtures with missing bullets and overrides

## Open Questions
- whether future Radar schema upgrades should carry explicit version markers

## Outcome
- Bound to `B-053` under `B-048`.
