---
status: implementation
idea_id: B-029
title: Odylith Install-Time Gitignore Bootstrap for Managed State
date: 2026-03-30
priority: P1
commercial_value: 4
product_impact: 4
market_value: 3
impacted_lanes: service
impacted_parts: install flow, upgrade backfill, doctor repair, .gitignore bootstrap, and CLI install guidance
sizing: S
complexity: Low
ordering_score: 100
ordering_rationale: Odylith-managed runtime state should never start by polluting the consumer worktree. The current install path only writes `/.odylith/` into `.gitignore` after `.git` already exists, which leaves fresh consumer folders with avoidable state noise and an inconsistent bootstrap story.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-03/2026-03-30-odylith-install-time-gitignore-bootstrap-for-managed-state.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-016
workstream_blocks:
related_diagram_ids:
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
Odylith already knows that `/.odylith/` should stay untracked, but install,
upgrade, and repair only backfill the root `.gitignore` after the folder is
already a Git repo. That means a fresh consumer folder can install Odylith and
still lack the ignore rule until Git is initialized later.

## Customer
- Primary: new consumer repos installing Odylith before or during initial Git
  setup.
- Secondary: maintainers validating install and repair flows in clean temp
  folders.

## Opportunity
If Odylith writes the managed-state ignore rule whenever it installs, then the
consumer repo starts with the right hygiene immediately and later Git init can
pick up the prepared ignore file without extra user cleanup.

## Proposed Solution
- create the root `.gitignore` during install-time flows when it does not exist
- append `/.odylith/` when the file exists but is missing the managed-state
  entry
- keep duplicate detection so install, upgrade, and repair remain idempotent

## Scope
- update the install helper that maintains `.gitignore`
- cover first install, reinstall, and non-Git repo behavior with focused tests
- keep CLI messaging coherent when the repo still lacks `.git`

## Non-Goals
- adding broader ignore rules beyond Odylith-managed state
- changing the meaning of the `git_repo_present` summary flag
- auto-initializing Git repositories

## Risks
- creating `.gitignore` in non-Git folders could surprise users if it happens
  silently
- helper changes could accidentally duplicate existing ignore entries

## Dependencies
- `B-016` established install-time consumer bootstrap and CLI guidance

## Success Metrics
- first install creates or updates `.gitignore` with `/.odylith/` even when
  `.git` is not present yet
- repeat install, upgrade, and repair flows remain idempotent
- focused manager and CLI tests prove the new behavior

## Validation
- `PYTHONPATH=src python -m pytest -q tests/integration/install/test_manager.py tests/unit/test_cli.py`
- `git diff --check`

## Rollout
Ship as an install-hygiene fix. The change is additive and should be visible on
the next consumer install without requiring any migration.

## Why Now
The first-run shell is now a front-door workflow, so the install path should
not leave managed state hygiene half-done just because the folder has not been
turned into a Git repo yet.

## Product View
The first install should leave the repo cleaner, not noisier. Creating or
backfilling `.gitignore` for `/.odylith/` is basic product hygiene and should
not depend on whether Git was initialized five minutes earlier.

## Impacted Components
- `odylith`

## Interface Changes
- install may now create `.gitignore` in a consumer repo root before `.git`
  exists
- CLI install output can report both the `.gitignore` update and the missing
  Git caveat in the same run

## Migration/Compatibility
- backward compatible; existing `.gitignore` files are preserved and only gain
  the managed-state entry when missing

## Test Strategy
- cover non-Git install creation, existing-entry idempotency, and CLI install
  messaging

## Open Questions
- whether a future slice should also backfill `.git/info/exclude` for unusual
  consumer repos that intentionally avoid committed ignore files

## Outcome
- Bound to `B-029`; implementation in progress.
