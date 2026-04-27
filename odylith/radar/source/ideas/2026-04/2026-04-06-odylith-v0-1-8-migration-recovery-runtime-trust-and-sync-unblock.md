---
status: implementation
idea_id: B-048
title: v0.1.8 Migration Recovery, Runtime Trust Robustness, and Sync Unblock
date: 2026-04-06
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: managed runtime trust validation, repair and reinstall convergence, legacy migration auditing, Radar normalization before sync, sync failure summaries, lifecycle-plan output, and verifier warning presentation
sizing: L
complexity: High
ordering_score: 100
ordering_rationale: Migration into 0.1.8 surfaced concrete install and sync blockers in a real downstream repo. Shipping the next release without hardening these paths would leave Odylith looking brittle exactly where operators expect trust, recovery, and immediate sync success.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-06-odylith-v0-1-8-migration-recovery-runtime-trust-and-sync-unblock.md
execution_model: standard
workstream_type: child
workstream_parent: B-033
workstream_children: B-049,B-050,B-051,B-052,B-053,B-054,B-055,B-056
workstream_depends_on: B-030,B-040
workstream_blocks:
related_diagram_ids: D-018,D-019,D-020
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
Odylith itself can install, query memory, and render surfaces, but a real
April 6 migration on macOS Apple Silicon still exposed three release-blocking
gaps: managed runtime trust is too fragile against OS metadata noise, partial
repair does not converge cleanly, and legacy Radar truth can leave `sync`
blocked immediately after migration. Operator output also stays too noisy and
too inconsistent about what is actually broken.

## Customer
- Primary: consumer-repo operators migrating or reinstalling Odylith on a real
  repo and expecting repair plus sync to converge without filesystem surgery.
- Secondary: Odylith maintainers who need the release story, install lane, and
  migration contract to remain trustworthy under realistic downstream drift.

## Opportunity
If Odylith treats migration recovery, runtime trust, sync normalization, and
operator-summary clarity as one bounded release wave, then the product can turn
an embarrassing “healthy enough to run but not healthy enough to trust” moment
into a stronger install and upgrade contract.

## Proposed Solution
- add a runtime-tree policy helper that ignores only known OS metadata noise,
  scrubs target-version residue, and keeps trust validation fail-closed on real
  drift
- make repair, reinstall, and same-version runtime reuse converge after
  partial failure without manual cleanup of `.backup-*` or stale staging state
- unify runtime-status classification so `version` and `doctor` agree on
  wrapped-runtime trust degradation
- add stale-reference auditing for legacy `odyssey` paths outside the managed
  tree
- normalize legacy Radar backlog rationale before strict sync validation
- replace noisy sync and lifecycle-plan output with compact summaries plus
  genuinely different next actions
- suppress or translate benign Sigstore/TUF warning chatter when verification
  still succeeds

## Scope
- install/runtime trust helpers, repair sweeps, and runtime status reporting
- migrate-legacy-install auditing and reporting
- Radar normalization before sync contract enforcement
- sync summary rendering, lifecycle-plan verbosity defaults, and release-note
  messaging
- focused tests and repo-local CLI smoke for install, repair, version, and
  sync

## Non-Goals
- broad renaming of the historical `B-033` release umbrella
- permissive trust rules for arbitrary dotfiles or unmanaged runtime drift
- rewriting user-owned docs during migration

## Risks
- if cleanup widens too far, repair could delete operator-owned local state
- if trust ignores too much, real runtime tamper could become invisible
- if normalization rewrites too aggressively, Radar source could lose authored
  rationale instead of only backfilling missing contract bullets

## Dependencies
- `B-030` already owns reinstall and post-upgrade operator flow
- `B-040` already owns runtime trust and supply-chain posture
- `B-033` remains the parent release-hardening umbrella

## Success Metrics
- `.DS_Store` and AppleDouble noise no longer strand trusted runtimes
- repeated `install`, `reinstall --latest`, and `doctor --repair` converge
  after partial failure without manual cleanup
- `version` and `doctor` describe wrapped-runtime degradation consistently
- migration emits stale-reference audit results without rewriting user docs
- `sync` auto-normalizes legacy Radar rationale gaps once, then either passes
  or fails with a deduped top-N summary and a distinct next action
- default lifecycle plans collapse `dirty_overlap` into counts and samples
- successful verification prints one explicit success line and does not bury it
  in scary benign warnings

## Validation
- `pytest -q tests/unit/install/test_runtime.py tests/integration/install/test_manager.py tests/unit/test_cli.py tests/unit/runtime/test_validate_backlog_contract.py`
- focused sync and migration fixtures plus repo-local CLI smoke
- `git diff --check`

## Rollout
Land the source-truth records first, then ship runtime trust and repair
hardening, then land migration plus sync normalization, and finish with
operator-output cleanup and 0.1.8 release-note refresh.

## Why Now
The migration failure is concrete, recent, and reproducible. The next release
needs to prove Odylith can survive the exact maintenance path it is asking
operators to trust.

## Product View
Install and sync are not side quests. If Odylith cannot recover from a common
macOS migration shape and immediately re-enter a truthful governed state, the
product story collapses at first maintenance contact.

## Impacted Components
- `odylith`
- `release`
- `dashboard`
- `radar`

## Interface Changes
- `odylith install`, `odylith reinstall`, `odylith doctor`, `odylith version`,
  and `odylith sync` gain the hardened behavior described above
- migration now emits a stale-reference audit summary and stores a full report
- sync auto-normalizes legacy Radar rationale before strict validation
- lifecycle plans gain a default compact mode plus an explicit verbose path

## Migration/Compatibility
- legacy `odyssey` repos gain a non-destructive audit and normalization bridge
- modern installs remain fail-closed on real trust drift
- no user-doc rewrite is required for stale-reference reporting

## Test Strategy
- characterize the reported macOS and migration failure modes directly
- prove the runtime-status and sync-summary paths through CLI-visible output
- keep the Radar normalization tests authored against real legacy `INDEX.md`
  fixtures rather than synthetic one-line stubs

## Open Questions
- whether stale-reference audit output should later gain a machine-readable
  companion format in addition to the repo-local report

## Outcome
- Bound to `B-048` as the 0.1.8 migration-recovery umbrella under `B-033`.
- Child workstreams `B-049` through `B-056` carry the concrete feedback items.
