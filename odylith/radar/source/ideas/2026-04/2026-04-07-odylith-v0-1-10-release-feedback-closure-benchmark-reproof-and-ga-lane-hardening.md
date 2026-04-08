---
status: implementation
idea_id: B-060
title: Odylith v0.1.10 Release Feedback Closure, Benchmark Re-Proof, and GA Lane Hardening
date: 2026-04-07
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: release identity validation, benchmark proof and publication discipline, first-install shell refresh robustness, GitHub Actions runtime posture, post-publish dogfood cleanliness, and maintainer release workflow truth
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: `v0.1.9` shipped, but the release itself exposed a handful of precise truths that should become the next release scope instead of calcifying into normal release tax: a narrow GitHub merge-identity exception, a recoverable but ugly first-install shell render wobble, a deliberately skipped benchmark proof lane, CI runtime warnings, and a dirty post-publish maintainer checkout.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-07-odylith-v0-1-10-release-feedback-closure-benchmark-reproof-and-ga-lane-hardening.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-030,B-039
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
`v0.1.9` reached GA on 2026-04-07, but the release lane still carried several
truths that should not become permanent operating posture. Canonical release
proof needed a narrow compatibility exception for the currently observed GitHub
squash-merge committer shape, the disposable consumer lane emitted a first
shell-only missing-surface warning before broad sync settled it, benchmark
proof was intentionally skipped under a maintainer override, GitHub Actions
warned that pinned first-party actions still rely on the Node 20 runtime,
hosted-install upgrades could fail late on read-only stale-runtime cleanup or
leave the repo pin behind the newly active runtime, and post-publish dogfood
reactivation left tracked generated surfaces dirty in the maintainer checkout.
Fresh downstream sync feedback on 2026-04-07 added another trust slice:
operator-facing sync behavior is stronger than its public surface suggests, but
it still hides supported controls, runs too quietly during some long steps,
understates large dirty-overlap risk, and can rewrite unchanged generated JSON
artifacts in ways that make file mtimes disagree with embedded
`generated_utc`. Another downstream packet the same day exposed a Compass
refresh trust gap: bounded `shell-safe` refresh behaved as designed, but the
advertised deeper `--compass-refresh-profile full` path still shared the same
hard dashboard timeout, could fail twice under realistic repo state, suggested
the wrong recovery command, and silently left the old `shell-safe` payload
active with no explicit failure marker. A 2026-04-08 follow-up packet showed
the shell host still projecting stale Compass state poorly: `tooling_shell`
could refresh successfully after that failed deeper Compass rerender and keep
presenting the older Compass brief with no shell-level admission that the
wrapper had refreshed separately from the child runtime. The same day, pinned
dogfood release proof exposed a fresh benchmark truth: the full
`--profile proof` benchmark lane can wedge mid-corpus and block release prep
without persisting a fresh release-safe report, so `v0.1.10` now needs an
explicit tracked benchmark override instead of pretending benchmark re-proof
landed cleanly.

## Customer
- Primary: Odylith maintainers cutting, proving, and recovering canonical
  releases from the product repo.
- Secondary: consumer-repo operators whose first upgrade, welcome, and shell
  refresh moments should feel deliberate instead of slightly haunted.

## Opportunity
Capture the `v0.1.9` release learnings as explicit `v0.1.10` engineering scope
so the next release no longer depends on special-case release memory, temporary
identity exceptions, or hand-waved benchmark deferrals.

## Proposed Solution
- remove the dependency on GitHub-generated merge committer metadata from
  canonical release ancestry, either by a cleaner merge policy or by a release
  integration path that preserves canonical maintainer identity end to end
- record a one-release benchmark override for `v0.1.10`, capture the
  pinned-dogfood proof-run wedge as a product bug, and move benchmark runner
  tuning plus proof restoration into the next release instead of pretending
  `v0.1.10` landed a clean full re-proof
- harden first-install and first-refresh shell rendering so disposable consumer
  proof repos never flash missing Radar, Atlas, Compass, Registry, or Casebook
  surfaces before full sync completes
- refresh pinned first-party GitHub Actions inputs so release CI does not drag
  an upcoming Node 20 deprecation into the next release cut
- make hosted-installer closeout converge on one truthful posture: the new
  runtime stays live, stale retention cleanup is best-effort with exact
  remediation, and existing consumer installs do not land in a silent
  active-versus-pin split state
- make `odylith sync` operator proof as trustworthy as the engine underneath
  it: visible help for real controls, heartbeat progress on long steps,
  stronger dirty-overlap acknowledgement, durable warning-report pointers, and
  truthful generated-artifact timestamps
- make Compass explicit refresh truthful end to end: aligned defaults between
  the public dashboard CLI and the underlying renderer, a viable timeout budget
  for `full`, an honest rerender hint on failure, and a live payload marker
  when the requested deeper refresh does not land
- make shell refresh truthful about Compass child-runtime freshness: when only
  the wrapper rerenders, the shell must project stale or failed Compass
  child-runtime state instead of implying the visible brief is current
- keep post-publish `dogfood-activate` and related surface refresh flows from
  dirtying the maintainer checkout, or isolate that generated drift into a
  clean proof workspace instead of the active branch
- preserve the already-green welcome screen and upgrade popup proof while the
  release machinery underneath them gets stricter

## Scope
- release identity validation and merge/publication posture
- benchmark override truth for `v0.1.10` plus benchmark-publication
  discipline and runner restoration for the next release
- first-install and consumer-rehearsal shell refresh robustness
- sync operator-surface discoverability, progress, and audit fidelity
- Compass explicit refresh timeout, hinting, and payload-truth hardening
- tooling-shell versus Compass child-runtime freshness projection
- release workflow CI input hardening
- hosted-installer closeout robustness and repo-pin convergence
- post-release maintainer checkout cleanliness and generated-surface handling
- governed release feedback capture for `v0.1.10`

## Non-Goals
- reopening `v0.1.9` or pretending its ship decision was invalid
- broad new feature work unrelated to the concrete `v0.1.9` release feedback
- weakening canonical release authority checks just to make automation easier

## Risks
- if the GitHub committer exception stays implicit, it will quietly become the
  de facto release policy
- if benchmark overrides stay under-documented or become routine, the product
  story can run ahead of measured proof and normalize a broken proof runner
- if the first-install shell wobble stays untreated, the default consumer proof
  lane will keep feeling less trustworthy than the broader system actually is
- if hosted-install closeout keeps failing late or leaving the pin behind, the
  public "latest and greatest" path will keep feeling less trustworthy than the
  verified runtime it just activated
- if sync keeps hiding its real controls, mutating large dirty worktrees
  without a stronger acknowledgement gate, or rewriting unchanged artifacts
  with stale embedded timestamps, operators will trust the engine less than the
  evidence warrants
- if the shell can refresh successfully while still showing an older Compass
  brief without saying so, operators will learn not to trust parent-surface
  success signals
- if post-publish dogfood keeps dirtying tracked surfaces, maintainers will
  normalize release aftermath drift instead of fixing the release path

## Dependencies
- `B-030` already owns the welcome screen, upgrade spotlight, and narrow shell
  refresh UX that this release feedback should harden rather than replace
- `B-039` already owns the benchmark-audit and publication-refresh direction
  that the `v0.1.10` proof lane should stop deferring

## Success Metrics
- canonical release proof no longer relies on the GitHub-generated
  `noreply@github.com` committer exception
- `v0.1.10` ships with an explicit tracked benchmark override instead of a
  shell-only exception, and the release story stays honest that full
  pinned-dogfood proof did not land for that version
- disposable consumer first install and GA-gate rehearsal render shell surfaces
  cleanly without transient missing-surface warnings
- hosted-installer upgrades on already-installed consumer repos finish with a
  healthy active runtime, a matching tracked repo pin, and no retention-prune
  hard failure from read-only stale trees
- downstream `odylith sync` runs expose their real control surface, stay visibly
  alive during long steps, require explicit acknowledgement for large dirty
  overlap, and keep generated-artifact metadata truthful on semantic no-op runs
- downstream Compass full-refresh proof no longer times out under the old
  shell-safe timeout budget, leaves a visible stale-and-failed marker when a
  deeper refresh does fail, and never points operators at `odylith compass
  update --repo-root .` as if that were a rerender command
- release CI no longer emits the Node 20 deprecation warning on pinned
  first-party actions
- post-publish maintainer checkout stays clean or uses an isolated proof path
  that keeps generated surface drift out of the active branch

## Validation
- `make release-preflight VERSION=0.1.10`
- `make consumer-rehearsal PREVIOUS_VERSION=0.1.9`
- `make ga-gate PREVIOUS_VERSION=0.1.9`
- benchmark override truth for `v0.1.10` plus explicit next-release benchmark
  restoration plan
- focused install and release browser proof for welcome plus upgrade UX
- focused hosted-install closeout proof for retention cleanup and repo-pin
  convergence
- focused sync proof for help discoverability, heartbeat progress,
  dirty-overlap guardrails, warning summaries, and generated-artifact audit
  fidelity
- `git diff --check`

## Rollout
Capture the release feedback first, execute the release-lane hardening before
the `v0.1.10` cut, and treat the current branch as the truthful home of the
post-`v0.1.9` maintainer drift that still needs cleanup.

## Why Now
The right time to process release feedback is right after the release, while
the evidence is still crisp and before temporary exceptions turn into folklore.

## Product View
The release lane should feel as trustworthy as the product itself. `v0.1.9`
proved Odylith can ship; `v0.1.10` should prove the shipping path deserves the
same confidence as the runtime and surfaces it delivers.

## Impacted Components
- `release`
- `odylith`
- `dashboard`
- `benchmark`
- `compass`

## Interface Changes
- no immediate product-runtime interface change from this capture step
- `v0.1.10` follow-up work will tighten release proof, shell refresh, and
  benchmark obligations before the next version cut

## Migration/Compatibility
- additive governance capture only in this step
- later implementation should preserve the canonical public install and upgrade
  contract while tightening the maintainer release lane and first-install proof

## Test Strategy
- prove the next release from the exact path that mattered this time:
  canonical release proof, consumer rehearsal, GA gate, and benchmark audit
- keep welcome-screen and upgrade-popup browser proof as explicit regression
  gates so release-lane hardening does not quietly break the user-facing shell
- fail the next release on lingering temporary overrides rather than documenting
  them after the fact

## Open Questions
- whether the cleanest long-term answer to the GitHub committer exception is a
  local canonical merge path, a different GitHub merge policy, or a stricter
  release-authority check that no longer cares about GitHub-generated
  committer metadata at all
- whether post-publish surface refresh should move fully into an isolated proof
  checkout instead of touching the active maintainer workspace

## Outcome
- Opened on 2026-04-07 as the governed `v0.1.10` release-feedback slice.
- Carries the concrete `v0.1.9` lessons: the narrow identity exception, the
  transient first-install shell warning, the skipped benchmark proof,
  first-party CI runtime drift, the hosted-installer retention and pin-closeout
  gaps, the sync operator-contract gaps, the stale generated-artifact audit
  mismatch, and the dirty post-publish maintainer checkout.
- The active maintainer branch `2026/freedom/v0.1.10` now holds the real
  post-release worktree drift instead of leaving it stranded on `main`.
- `v0.1.10` now also carries a tracked benchmark override instead of silent
  shell history: pinned-dogfood proof run `0047192366d8bf1c` wedged mid-corpus
  without producing a fresh release-safe report, so benchmark runner tuning and
  full proof restoration move to the next release under `CB-069`.
- Compass explicit-refresh hardening is now part of the landed `v0.1.10`
  release-feedback slice: explicit `full` refresh no longer shares the old
  shell-safe timeout budget, the failure hint points back to a real Compass
  rerender command, and failed deeper refresh attempts mark the live payload so
  operators do not silently keep serving a stale bounded snapshot.
- The same release-feedback slice now also owns shell-host truth for Compass:
  a successful wrapper refresh must not masquerade as fresh Compass runtime
  data when the visible brief still comes from an older or failed child
  snapshot.
- Shell-host Compass freshness hardening is now landed too: the shell refresh
  payload projects stale or failed Compass child-runtime posture onto the
  Compass tab, and shell-only refresh notes now say explicitly that they did
  not rerender Compass runtime truth.
- `v0.1.10` now also has authored release-note source ready for release prep,
  and the upgrade-spotlight browser proof is tied to that exact note so the
  popup ships from the same markdown truth that will be tagged on GitHub.
