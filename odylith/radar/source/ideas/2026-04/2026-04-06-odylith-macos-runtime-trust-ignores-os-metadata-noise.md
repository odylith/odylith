---
status: queued
idea_id: B-049
title: Odylith macOS Runtime Trust Ignores OS Metadata Noise
date: 2026-04-06
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: managed runtime tree manifest generation, trust validation, feature-pack preflight, and macOS metadata handling
sizing: S
complexity: Medium
ordering_score: 100
ordering_rationale: A trusted runtime that fails closed on `.DS_Store` is not actually robust on macOS. This is the first hard blocker because it prevents install, repair, and feature-pack activation from using the runtime Odylith itself just staged.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-048
workstream_children:
workstream_depends_on: B-040
workstream_blocks: B-050
related_diagram_ids: D-019,D-020
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
Known macOS metadata files such as `.DS_Store` and AppleDouble `._*` can appear
inside managed runtime trees after staging or inspection. Odylith currently
treats those entries as fatal trust drift and blocks feature-pack activation
and runtime reuse.

## Customer
- Primary: macOS operators installing or repairing Odylith on real repos.

## Opportunity
Ignore only explicit OS noise while keeping trust validation strict on real
runtime drift.

## Proposed Solution
- extract a runtime-tree policy helper that classifies ignorable OS metadata
- apply it to trust-manifest generation, verification, and residue scrubbing
- keep arbitrary dotfiles, symlinks, and unexpected runtime content fatal

## Scope
- runtime-tree entry enumeration and integrity checking
- tests for `.DS_Store` and `._*`

## Non-Goals
- ignoring arbitrary hidden files

## Risks
- an overbroad ignore list could hide genuine tamper

## Dependencies
- `B-040`

## Success Metrics
- `.DS_Store` and `._*` no longer break trusted runtime validation
- unexpected non-allowlisted entries still fail closed

## Validation
- `pytest -q tests/unit/install/test_runtime.py`

## Rollout
Ship with the repair convergence work so the trust and recovery story stays
coherent.

## Why Now
The reported migration failed repeatedly on this exact case.

## Product View
Failing closed on Apple Finder noise is not a security win; it is a platform
blind spot.

## Impacted Components
- `odylith`
- `release`

## Interface Changes
- trust validation ignores explicit macOS metadata noise only

## Migration/Compatibility
- additive hardening for macOS installs

## Test Strategy
- characterize `.DS_Store` and AppleDouble drift separately

## Open Questions
- whether future platform-specific noise should be explicit metadata in the
  trust manifest instead of code policy

## Outcome
- Bound to `B-049` under `B-048`.
