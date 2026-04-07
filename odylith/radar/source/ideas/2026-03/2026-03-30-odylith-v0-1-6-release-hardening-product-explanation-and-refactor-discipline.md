---
status: implementation
idea_id: B-033
title: Odylith v0.1.6 Release Hardening, Product Explanation, and Refactor Discipline
date: 2026-03-30
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: release candidate proof lane, single-source version truth, backlog burn-down discipline, isolated canonical-checkout proof, lane introspection, release session validity, maintainer repair and dogfood idempotence, source-authored release notes, shell explainers, version-delta UX, empty-repo onboarding, benchmark comparison and history UX, and targeted large-file decomposition
sizing: XL
complexity: VeryHigh
ordering_score: 100
ordering_rationale: v0.1.5 proved the product is ahead of the release machinery. The next release should harden release truth, release proof, and maintainer lane safety first, then spend that safety budget on clearer product explanation and a targeted refactor wave instead of another burst of loosely coupled feature work.
confidence: high
founder_override: yes
promoted_to_plan: odylith/technical-plans/in-progress/2026-03/2026-03-30-odylith-v0-1-6-release-hardening-product-explanation-and-refactor-discipline.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children: B-040,B-048
workstream_depends_on: B-006,B-021,B-022,B-028,B-030
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
`v0.1.5` shipped with meaningful product gains, but the release showed that the
release system still trails the product. Version truth was still too manual,
governance drift still surfaced too late, isolated canonical-checkout proof was
not strong enough, benchmark regressions were not treated as an early release
signal, and the shell still does not explain its own surfaces crisply enough at
first contact. At the same time, the repo now has enough oversized central
files that maintainability has become a release concern, but the wrong response
would be a repo-wide big-bang rewrite in the same window.

## Customer
- Primary: Odylith maintainers cutting and proving releases from the product
  repo.
- Secondary: consumer-repo operators who need the product to explain itself,
  narrate upgrades clearly, and feel more polished right after install or
  update.

## Opportunity
If `v0.1.6` hardens the maintainer release lane first, then Odylith can ship
the next round of user-facing polish from a safer foundation. That means
release notes can become a real source artifact, shell explanation can get much
clearer, and the refactor wave can reduce structural risk without pretending a
single threshold-based rewrite is the right way to improve the codebase.

## Proposed Solution
Ship this as one umbrella release contract with bounded execution waves.

### Wave 1: Release machinery and truth hardening
- add a pre-merge release-candidate lane that runs `release-preflight`,
  isolated-checkout `ga-gate`, benchmark compare against the last shipped
  release, and docs/version/source-of-truth consistency checks
- make release truth single-sourced and generated outward instead of manually
  synchronized across multiple files
- add explicit lane introspection so pinned dogfood versus detached
  `source-local` is obvious from one supported command
- make release sessions self-invalidating when `HEAD` changes
- make maintainer repair and dogfood flows idempotent in product-repo mode so
  they do not leave tracked guidance drift behind
- keep governance drift visible early enough that backlog contract failures are
  burned down before release crunch

### Wave 2: Product explanation and release narrative
- promote plain-English release notes into a maintained source artifact that
  powers both the upgrade popup and a persistent release-notes page
- add one crisp first-use explainer sentence each for Radar, Registry, Atlas,
  and Compass
- add a persistent "What changed since my version?" view for consumer repos
- improve empty-repo onboarding so Odylith can help shape a repo before there
  is much local code to inspect

### Wave 3: Benchmark visibility and targeted refactor wave
- treat benchmark compare against the last shipped release as an earlier hard
  release signal
- add benchmark history UI that shows better, worse, or unchanged versus the
  last release directly in maintainer workflow
- run a dedicated refactor wave prioritized by size x churn x centrality, not
  size alone
- codify file-size discipline so oversized hand-maintained source gets planned
  decomposition instead of more unrelated feature growth

## Scope
- maintainer release-lane proof, validity, idempotence, and source-truth
  hardening
- source-authored release notes and persistent version-delta storytelling
- first-use surface explanation and better empty-repo onboarding
- benchmark release-signal and history visibility improvements
- targeted large-file decomposition policy and prioritized refactor wave

## Non-Goals
- a repo-wide "all files above X" rewrite in one release
- another manual three-file version-truth synchronization loop
- leaking maintainer-only release process detail into bundled consumer
  guidance
- using onboarding or other shell polish to defer the maintainer release-lane
  hardening that `v0.1.5` exposed

## Risks
- one umbrella record could become mush if it is allowed to absorb every
  unrelated improvement that someone wants in `v0.1.6`
- refactor enthusiasm could destabilize the most central release-critical paths
  if it is not constrained to characterization-tested, bounded slices
- release notes and version-delta UX could drift from shipped truth if they are
  not sourced from one maintained artifact
- benchmark compare could still arrive too late if it is treated as release-day
  ceremony instead of pre-merge signal

## Dependencies
- `B-030` already carries upgrade spotlight, recovery, and shell refresh work
  that this release-narrative wave should build on instead of replacing
- `B-028` already carries starter launchpad redesign work that should absorb
  the first-use explainer follow-through
- `B-006` remains the tracked dark-theme workstream and should be pulled into
  this release window
- `B-021` and `B-022` already define benchmark frontier and integrity work that
  this release should treat as part of the hard proof lane

## Success Metrics
- a pre-merge release-candidate lane fails before release crunch when release
  truth, docs, benchmarks, or canonical-checkout proof drift
- one source of truth generates outward version files and release-facing
  version-state and readout artifacts
- maintainers can inspect current lane and release eligibility explicitly from
  one supported command
- release sessions cannot survive `HEAD` drift silently
- repair and dogfood flows can be rerun safely without leaving tracked drift
- release notes are authored once and reused by popup and permanent page
- the shell explains Radar, Registry, Atlas, and Compass on first use
- consumer repos can inspect "what changed since my version?" after the initial
  popup moment
- benchmark history and compare are visible in maintainer workflow
- refactor work lands as targeted decompositions backed by characterization
  tests rather than one repo-wide rewrite

## Validation
- release-candidate lane proof: `make release-preflight`, isolated-checkout
  `ga-gate`, benchmark compare, and docs/version/source-of-truth consistency
  checks
- focused CLI, install, dashboard, and browser proof for the product-facing UX
  work
- characterization tests before each large-file extraction wave
- `git diff --check`

## Rollout
Land this as the umbrella `v0.1.6` release record, then execute it in bounded
waves. Keep release machinery hardening ahead of net-new feature surface, use
existing in-progress workstreams where they already match the scope, and open
child refactor workstreams only for the specific high-risk files that earn
separate execution.

## Why Now
`v0.1.5` already taught us the right lesson: the product is believable enough
that the next failure mode is no longer "can Odylith do anything useful?" but
"does the release system deserve the same trust as the product?"

## Product View
The next release should feel like a product that understands both its users and
its own shipping discipline. That means stronger release machinery, clearer
explanation, and a refactor wave with judgment instead of thrash.

## Impacted Components
- `odylith`
- `release`
- `dashboard`
- `benchmark`
- `atlas`
- `compass`

## Interface Changes
- maintainers gain a clearer release-candidate and lane-status contract
- release notes become source-authored and reusable across popup and persistent
  page
- consumer repos gain a persistent version-delta readout and stronger first-use
  explanation
- benchmark history and compare become maintainer-facing product UI, not just
  buried release artifacts

## Migration/Compatibility
- the release-truth hardening should reduce manual synchrony rather than change
  the supported semver contract
- release-note and history artifacts should stay additive and safe to ignore in
  older local surfaces until the newer shell reads them
- refactor policy is governance tightening, not a backwards-incompatible
  runtime change

## Test Strategy
- prove the release lane from the exact path that matters: isolated canonical
  checkout plus the maintainer product repo lane
- prove product explanation and release storytelling in browser-visible flows,
  not just payload builders
- treat each refactor extraction as behavior-preserving until characterization
  tests say otherwise

## Open Questions
- whether lane introspection should be `odylith lane status`, `odylith status`,
  or a `make lane-show` wrapper over the canonical CLI
- whether benchmark compare and release-history readout should live in one
  shared release dashboard panel or two separate maintainer views
- which of the largest central files deserve the first dedicated decomposition
  wave after the release-lane hardening lands

## Outcome
- Bound to `B-033`; implementation planning is in progress for `v0.1.6`.
- This workstream explicitly carries release-system hardening, product
  explanation, benchmark visibility, and targeted refactor discipline together
  as the next release contract.
