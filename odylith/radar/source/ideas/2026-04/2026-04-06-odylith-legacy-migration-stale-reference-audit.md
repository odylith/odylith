---
status: queued
idea_id: B-052
title: Legacy Migration Stale Reference Audit
date: 2026-04-06
priority: P1
commercial_value: 4
product_impact: 4
market_value: 3
impacted_parts: legacy migration auditing, tracked-text scanning, repo-local migration reports, and stale `odyssey` reference surfacing
sizing: S
complexity: Medium
ordering_score: 100
ordering_rationale: Migration should not silently declare success while stale `odyssey` truth survives in governed docs and plans. Auditing that drift without rewriting user docs is the narrow honest bridge.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-048
workstream_children:
workstream_depends_on: B-030
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
Legacy migration renames the managed tree, but stale `odyssey` references can
still survive in tracked docs and governance Markdown outside the managed tree.
Operators currently get no report of what still needs manual follow-up.

## Customer
- Primary: operators migrating a repo from legacy layout who need a truthful
  “what still references Odyssey?” readout.

## Opportunity
Emit a post-migration audit and repo-local report without rewriting user-owned
docs or governance prose automatically.

## Proposed Solution
- scan tracked text files outside managed runtime and cache trees for `odyssey`
- print a compact top-hit summary after migration and reinstall paths
- persist a full report under `.odylith/state/migration/`

## Scope
- migrate-legacy-install reporting
- tracked-text scanning and report persistence
- focused migration tests

## Non-Goals
- automatic rewriting of user docs

## Risks
- the scan could become noisy if generated assets are not excluded carefully

## Dependencies
- `B-030`

## Success Metrics
- migration reports stale `odyssey` references in tracked text files
- no tracked file is rewritten by the audit itself

## Validation
- `pytest -q tests/integration/install/test_manager.py tests/unit/test_cli.py`

## Rollout
Ship with migration and reinstall flows so operators see the audit during the
same maintenance session.

## Why Now
Stale `odyssey` references already exist in current governed truth, so the gap
is not hypothetical.

## Product View
Migration is only honest if it admits what it did not normalize.

## Impacted Components
- `odylith`
- `radar`

## Interface Changes
- migration, install, and reinstall emit stale-reference audit summaries and
  store a detailed report

## Migration/Compatibility
- additive audit only

## Test Strategy
- build fixtures with governed Markdown and docs that still contain `odyssey`

## Open Questions
- whether the report should later classify source-of-truth versus generated
  references separately

## Outcome
- Bound to `B-052` under `B-048`.
