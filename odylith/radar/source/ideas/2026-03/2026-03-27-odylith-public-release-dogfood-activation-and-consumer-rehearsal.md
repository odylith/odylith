status: finished

idea_id: B-005

title: Release Reset, Full-Stack Runtime Packaging, and Hosted-Asset Proof

date: 2026-03-27

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: canonical release lane, hosted install and upgrade contract, full-stack managed runtime packaging, runtime/cache retention, product-repo dogfood posture, release evidence, and first consumer proof

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Odylith should not relaunch from a repo state that still narrates abandoned `0.1.x` rehearsal history as public truth, lacks a blocking local hosted-asset proof before dispatch, and ships oversized runtime payloads that stall first install and incremental upgrade.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-28-odylith-managed-runtime-bundles-and-supported-platform-contract.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on: B-001,B-004

workstream_blocks:

related_diagram_ids: D-019,D-020,D-021,D-022,D-023

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Odylith's current repo narrative and release lane still carry abandoned
`0.1.x` rehearsal history, and the runtime payloads remain too large and too
sticky for a credible preview relaunch. Install and upgrade need to stay
full-stack by default, but the asset transport and retention model must become
lighter and more deterministic.

## Customer
- Primary: Odylith maintainers who need a clean restart at `v0.1.0`, a
  canonical hosted-asset proof before dispatch, and a release lane that fails
  closed on stale or oversized payload assumptions.
- Secondary: downstream repo maintainers who need full Odylith on first
  install without stalled downloads, repeated large upgrade churn, or hidden
  dependence on machine Python.

## Opportunity
By resetting the release line locally, splitting the runtime into smaller
managed assets while keeping install full-stack by default, and proving the
generated installer against local hosted-style assets before dispatch, Odylith
can relaunch on a much tighter operator contract.

## Proposed Solution
Restart the public line at `v0.1.0`, rewrite local repo truth to treat the old
`0.1.x` sequence as abandoned prelaunch rehearsal, and make the new preview
lane ship as a full-stack install assembled from smaller managed assets.

### Wave 1: Reset the source-of-truth narrative
- lower the product source version floor and repo pin back to `0.1.0`
- clear sticky local release-session state
- rewrite README, backlog, plans, bugs, and component specs so they no longer
  describe `0.1.x` rehearsal tags as the canonical published product history

### Wave 2: Split transport, keep full-stack install
- keep the consumer contract full-stack by default for `odylith install` and
  normal `odylith upgrade`
- keep the hosted installer one-command and non-interactive so Odylith, not the
  developer, figures out the environment and the right managed assets
- preserve a zero-friction install UX by letting the installer find the repo
  root automatically and by avoiding setup choices or branching install flows
- package the runtime as a smaller base managed runtime plus a separately
  versioned managed context-engine pack so release uploads/downloads stop
  stalling on one monolithic artifact
- reuse an unchanged context-engine pack across upgrades when its asset digest
  matches, and prune older staged runtimes plus release caches after each
  successful install, upgrade, or rollback
- keep the maintainer wheel-build path explicitly Hatch-based so the canonical
  publication contract is consistent between local preflight and GitHub Actions

### Wave 3: Block on local hosted-asset proof
- make `make release-preflight` build the full local release asset set before
  dispatch
- prove `install -> version -> doctor -> sync` against the generated installer
  and local hosted-style assets
- prove `previous -> target -> rollback -> re-upgrade` whenever a prior hosted
  preview exists for the relaunch line
- keep cache writes, runtime restaging, and activation handoff crash-safe by
  committing files atomically, syncing swap directories, and validating nested
  repo-root installer execution before dispatch
- keep first install fail-closed until the full stack passes activation smoke,
  and treat same-version upgrade as a no-op or repair case instead of
  restaging the live runtime in place

## Scope
- source version and pinned-version reset to restart at `0.1.0`
- full-stack install and upgrade assembled from split managed release assets
- runtime/cache retention pruning
- local hosted-asset preflight proof before canonical dispatch
- README, runbook, backlog, plan, bug, and Registry source-truth rewrites

## Non-Goals
- GA policy and support-window definition
- Windows support in this slice
- non-GitHub distribution channels

## Risks
- a split-asset release can still regress if the installer or manifest fails to
  prove that exactly one Odylith wheel and the expected managed assets are
  present
- full-stack install can remain too heavy if upgrades keep redownloading an
  unchanged context-engine pack
- repo truth can drift again if old prelaunch history remains embedded in
  checked-in specs, plans, or generated surfaces

## Dependencies
- `B-001` established Odylith's product-owned repo-truth boundary
- `B-004` established the self-host posture and canonical release lane guards

## Success Metrics
- release preview/show restarts from `0.1.0`
- the source repo no longer claims the abandoned `0.1.x` rehearsal line as
  canonical published history
- `odylith install` and normal `odylith upgrade` still produce a full-stack
  runtime, but transport uses smaller split assets
- upgrades retain only the active runtime, one rollback target, and the
  matching cached release payloads
- `make release-preflight` proves local hosted-style install, status, doctor,
  and sync before dispatch
- verified download caching, same-version restaging, and runtime activation stay
  atomic through retry, stage-and-swap, and directory-sync hardening
- fresh consumer install does not become live until the full-stack runtime
  passes smoke, and same-version upgrade refuses live restage drift

## Validation
- `make validate`
- `make release-version-preview`
- `make release-version-show`
- `make release-preflight VERSION=X.Y.Z`
- `make consumer-rehearsal VERSION=X.Y.Z`

## Rollout
Treat the published `v0.1.0` release as the completed clean restart of the
line. Do not reuse the old abandoned `0.1.x` rehearsal story as public
compatibility truth.

## Why Now
The release reset and payload split were the shortest path to a release line
that is operationally credible instead of merely locally implemented, and that
preview-relaunch work is now complete.

## Product View
Users should get the full power of Odylith by default. The right fix is not to
ship a weaker install, but to ship full Odylith through smaller, faster,
reusable managed assets.

## Impacted Components
- `odylith`
- `odylith-context-engine`
- `release`
- `registry`
- `dashboard`
- `compass`

## Interface Changes
- `odylith install` and normal `odylith upgrade` remain full-stack by default
- the hosted installer remains one-command, non-interactive, and
  environment-smart
- `odylith version` and `odylith doctor` report context-engine mode and
  context-engine pack state
- `make release-preflight` becomes a blocking local hosted-asset proof gate

## Migration/Compatibility
- the managed-runtime contract remains repo-local under `.odylith/`
- the consumer contract stays on the `odylith` CLI and hosted `install.sh`
- the split asset model is an internal packaging change that preserves a
  full-stack runtime outcome

## Test Strategy
- focused install/runtime/release-asset tests for manifest validation, pack
  reuse, and retention pruning
- local hosted-asset preflight smoke from the generated installer
- hosted consumer rehearsal after dispatch

## Open Questions
- when the context-engine pack is unchanged across releases, should future
  manifests move to explicit content-addressed pack versioning instead of only
  release-version scoping
- after the relaunch, should watchman and other watcher accelerators become a
  separately governed optional pack or stay in the default full-stack path
