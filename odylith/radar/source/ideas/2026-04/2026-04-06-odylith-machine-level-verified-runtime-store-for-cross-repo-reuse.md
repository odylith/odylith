---
status: queued
idea_id: B-057
title: Machine-Level Verified Runtime Store for Cross-Repo Reuse
date: 2026-04-06
priority: P1
commercial_value: 4
product_impact: 5
market_value: 4
impacted_parts: managed runtime storage, install materialization, feature-pack overlay safety, runtime retention, and operator posture reporting
sizing: L
complexity: High
ordering_score: 100
ordering_rationale: Odylith now installs cleanly per repo, but the next adoption barrier is disk amplification. The same verified Python runtime is duplicated across every repo, so a shared verified base store with safe repo-local materialization is the next bounded step to make multi-repo use feel sane without weakening trust or repair semantics.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-005,B-040
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
Odylith currently installs a full managed runtime under each repo's
`.odylith/runtime/versions/<version>` tree. That keeps trust and repair
repo-local, but it also means the same 0.4-0.5 GB Python runtime gets copied
into every repo on the same machine. The earlier packaging split reduced
download and upgrade transport cost, but it did not solve at-rest duplication
across repos.

## Customer
- Primary: operators and maintainers who use Odylith across several repos and
  do not want every repo to consume another full managed runtime footprint.
- Secondary: Odylith maintainers who need the install story to stay
  defensible at multi-repo scale without weakening trust, repair, or feature
  pack behavior.

## Opportunity
If Odylith can verify one machine-local base runtime and then materialize
repo-local copies from that trusted store, it can keep the current repo-local
operator contract while cutting repeated disk usage sharply on the common
same-filesystem path.

## Proposed Solution
- add a machine-level verified runtime store keyed by version, platform, and
  content digest
- keep repo-local launchers, activation state, trust evidence, and repair
  semantics under `.odylith/`
- materialize repo-local runtime trees from the shared store using reflinks or
  hardlinks when possible, with plain-copy fallback across filesystems
- make feature-pack application and any later mutable overlay paths break
  shared links before mutation so shared bytes cannot be edited in place
- surface shared-store reuse in `version` and `doctor` so operators can see
  when Odylith reused verified base bytes versus copying a fresh tree

## Scope
- shared verified runtime-store contract and retention rules
- repo-local runtime materialization from the shared store
- copy-on-write or unlink-before-overlay safety for feature packs and other
  mutable runtime paths
- cross-filesystem fallback to plain copy
- focused install, repair, and status reporting tests

## Non-Goals
- directly symlinking a repo's active runtime to one global tree
- weakening repo-local trust validation or repair convergence
- introducing cross-machine shared caches or hosted runtime mounts in this
  first slice

## Risks
- link-based materialization can corrupt shared bytes if overlay writes do not
  break sharing first
- cross-filesystem fallback can regress into confusing partial reuse if error
  handling is not explicit
- retention or cleanup could delete shared-store content that another repo
  still depends on

## Dependencies
- `B-005` already split runtime transport and pruned per-repo retention, which
  makes the remaining disk problem clearly about cross-repo reuse
- `B-040` owns runtime trust and supply-chain posture, which the shared store
  must preserve instead of bypassing

## Success Metrics
- multiple repos on the same machine can reuse one verified base runtime for
  the same Odylith version instead of storing full duplicate copies
- feature-pack or repair activity in one repo does not mutate another repo's
  runtime or the shared store
- cross-filesystem installs fall back cleanly to copy mode without trust drift
- `version` and `doctor` can explain whether the active runtime came from
  shared-store materialization

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_runtime.py tests/unit/install/test_release_assets.py tests/integration/install/test_manager.py tests/unit/test_cli.py`
- two-repo install and repair smoke that proves same-version reuse and
  copy-fallback behavior
- `git diff --check`

## Rollout
Land the shared-store and materialization helpers first, then switch install
and reinstall to prefer the shared base runtime, then expose the new operator
readout once the storage and overlay behavior is proven.

## Why Now
Single-repo install is no longer the only adoption bar. Once operators start
using Odylith in several repos, repeated full-runtime duplication becomes an
obvious product tax.

## Product View
Odylith should stay full-stack by default, but it should not make users pay
the full byte cost repeatedly when one verified base runtime can safely serve
many repos.

## Impacted Components
- `odylith`
- `release`
- `dashboard`

## Interface Changes
- `odylith install` and `odylith reinstall` reuse a machine-local verified
  base runtime when possible
- `odylith version` and `odylith doctor` explain shared-runtime reuse posture

## Migration/Compatibility
- repo-local `.odylith/` remains the operator-owned activation and repair
  surface
- repos on different filesystems degrade cleanly to the current copy-based
  behavior
- no direct operator migration should be required beyond normal install or
  reinstall

## Test Strategy
- characterize same-version multi-repo reuse on one filesystem
- prove hardlink or reflink failure falls back to plain copy
- prove overlay writes and repair flows do not mutate shared-store bytes
- prove operator status output reflects shared-store materialization honestly

## Open Questions
- where the shared store should live by default on macOS, Linux, and future
  supported platforms
- whether store garbage collection should be purely automatic or also expose a
  maintenance command later

## Outcome
- Queued as `B-057` for future implementation.
- This slice keeps repo-local trust semantics while targeting cross-repo disk
  amplification directly.
