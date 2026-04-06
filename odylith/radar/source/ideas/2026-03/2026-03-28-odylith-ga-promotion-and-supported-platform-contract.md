status: finished

idea_id: B-007

title: Odylith GA Promotion and Supported Platform Contract

date: 2026-03-28

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_lanes: both

impacted_parts: public product stance, supported platform contract, release source truth, maintainer release guidance, and GA-facing product documentation

sizing: S

complexity: Medium

ordering_score: 100

ordering_rationale: Odylith already shipped `v0.1.0` and passed the full post-publish proof lane, but the repo still described that supported contract as preview. The product stance needed to catch up with the actual release evidence.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-28-odylith-ga-promotion-and-supported-platform-contract.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on: B-005

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
The hosted release exists, the product repo is pinned on the published runtime,
and dogfood plus consumer rehearsal plus `ga-gate` all passed. But README,
runbook, and Registry source truth still described the supported install and
release contract as preview.

## Customer
- Primary: Odylith maintainers who need source truth to match the actual
  published product stance.
- Secondary: downstream repo maintainers who need a clear statement of what is
  GA-supported today and what remains intentionally unsupported.

## Opportunity
By promoting the already-proved `v0.1.0` contract to GA in source truth,
Odylith can present one coherent public story without inventing a second
release event.

## Proposed Solution
Treat `v0.1.0` as the GA baseline for the supported platform matrix, carry the
latest release-reset hardening into the GA branch, and rewrite the checked-in
product docs/specs so they no longer claim preview posture.

## Scope
- GA promotion of the supported hosted install and release contract
- README, runbook, Registry-spec, backlog, and plan updates
- carry the release-reset pin-realignment hardening into the GA promotion slice

## Non-Goals
- cutting a new release number
- adding Windows or Intel macOS support
- defining a broad support-team or disclosure-process program

## Risks
- source truth can remain self-contradictory if preview wording survives in
  product docs after the GA claim
- GA can look cosmetic if the latest release-reset hardening remains stranded
  on a side branch instead of being included in the promotion slice

## Dependencies
- `B-005` completed the release reset, full-stack packaging, and hosted proof lane

## Success Metrics
- source-truth docs/specs describe the supported macOS Apple Silicon and Linux
  matrix as GA, not preview
- `B-005` is closed as finished
- the release-reset pin-realignment hardening is carried into the GA promotion branch
- `make validate` stays green after the source-truth update

## Validation
- `./.odylith/bin/odylith version --repo-root .`
- `make validate`

## Rollout
Treat published `v0.1.0` as the GA baseline for supported platforms and
increment future releases from that line.

## Why Now
The proof lane is already complete. Leaving the repo on `preview` language
after that evidence only creates avoidable ambiguity.

## Product View
If Odylith is already released, dogfooding correctly, and passes the public
consumer contract, the repo should say so plainly.

## Impacted Components
- `odylith`
- `release`
- `registry`

## Interface Changes
- public docs now describe the supported install/release matrix as GA
- maintainer guidance now treats `v0.1.0` as the GA baseline rather than a
  preview restart

## Migration/Compatibility
- no installer or CLI behavior changes
- unsupported platforms remain unsupported

## Test Strategy
- rely on the already-completed dogfood, consumer rehearsal, and `ga-gate`
  evidence from `v0.1.0`
- rerun repo validation after the source-truth updates

## Open Questions
- should Odylith later adopt a `1.0.0` semantic milestone, or keep GA as a
  product/support stance independent of semver magnitude
