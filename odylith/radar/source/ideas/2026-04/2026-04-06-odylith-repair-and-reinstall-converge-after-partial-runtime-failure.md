---
status: queued
idea_id: B-050
title: Repair and Reinstall Converge After Partial Runtime Failure
date: 2026-04-06
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: runtime replacement, repair cleanup, reinstall convergence, stale wrapper residue, and `.backup-*` handling
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: A release-recovery path that needs manual filesystem cleanup after one failed attempt is not an operator-grade repair contract. This sits immediately after the macOS noise fix because partial residue currently turns one failure into a repeating failure loop.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-048
workstream_children:
workstream_depends_on: B-030,B-040,B-049
workstream_blocks:
related_diagram_ids: D-018,D-019
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
After a partial repair or reinstall failure, Odylith can leave target-version
backups, failed staging trees, or stale wrapper state behind. The next repair
attempt then hits secondary errors such as `Directory not empty` instead of
converging.

## Customer
- Primary: operators relying on `doctor --repair` or `reinstall --latest` to
  recover the repo in place.

## Opportunity
Make recovery idempotent so repeating the supported command always moves the
repo toward one valid runtime state.

## Proposed Solution
- extract target-version residue cleanup around runtime staging
- remove or reuse stale `.backup-*`, failed staging directories, and stale
  wrapper outputs safely
- prove repeated repair and reinstall converge after injected partial failure

## Scope
- runtime replacement helpers
- repair flow cleanup
- install/reinstall tests

## Non-Goals
- broad deletion of unrelated runtime versions

## Risks
- residue sweeps could become too wide and delete valid rollback material

## Dependencies
- `B-030`
- `B-040`
- `B-049`

## Success Metrics
- repeated repair converges without manual cleanup
- reinstall after partial failure converges on the pinned runtime

## Validation
- `pytest -q tests/unit/install/test_runtime.py tests/integration/install/test_manager.py`

## Rollout
Land with direct injected-failure tests before changing CLI messaging.

## Why Now
The reported failure chain shows the current recovery contract is not
idempotent.

## Product View
Repair has to be boring. If the second run is worse than the first, Odylith is
teaching operators not to trust its own recovery commands.

## Impacted Components
- `odylith`
- `release`

## Interface Changes
- repair and reinstall clean target-version residue before retrying staging

## Migration/Compatibility
- backward compatible; improves convergence only

## Test Strategy
- inject failed staging and backup residue, then rerun repair and reinstall

## Open Questions
- whether the cleanup helper should later record residue classes in the install
  ledger for operator forensics

## Outcome
- Bound to `B-050` under `B-048`.
