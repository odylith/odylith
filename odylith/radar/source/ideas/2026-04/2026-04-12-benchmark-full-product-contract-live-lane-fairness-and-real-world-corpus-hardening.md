status: implementation

idea_id: B-093

title: Benchmark Full-Product Contract, Live-Lane Fairness, and Real-World Corpus Hardening

date: 2026-04-12

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: benchmark contract honesty, live fairness scoring, benchmark corpus realism, benchmark docs, benchmark graphs, benchmark publication truth, and release proof truth

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: The current benchmark harness and docs disagree about what `odylith_on` actually measures, and the tracked corpus is still not strong enough for a serious release-safe coding-agent claim. This workstream closes the fairness contract and seriousness gap in the same release without inventing a second benchmark story.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-12-benchmark-full-product-contract-live-lane-fairness-and-real-world-corpus-hardening.md

execution_model: standard

workstream_type: child

workstream_parent: B-021

workstream_children:

workstream_depends_on: B-021,B-022,B-091

workstream_blocks:

related_diagram_ids: D-024

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Odylith's live benchmark pair still mixes two different stories. The older
spec language described the primary comparison as grounding-scaffold-only, but
the live `odylith_on` lane already carries broader product affordances such as
focused preflight evidence and richer benchmark-facing support surfaces. At
the same time, the current corpus is still too Odylith-shaped to support a
strong claim that the benchmark reflects serious real-world coding-agent work.

## Customer
- Primary: Odylith benchmark readers, release reviewers, and maintainers who
  need the benchmark claim to be honest and technically defensible.
- Secondary: coding-agent users evaluating whether the full Odylith assistance
  stack is materially better than the same host agent without it.

## Opportunity
If Odylith explicitly defines the live benchmark as full-product assistance
versus raw agent, hardens the fairness boundaries, and expands the corpus with
more serious validator-backed real-world scenarios, the benchmark becomes much
harder to dismiss as a product-maintainer vanity exercise.

## Proposed Solution
Reframe the primary `odylith_on` versus `odylith_off` publication comparison as
`full_product_assistance_vs_raw_agent`, enumerate the allowed Odylith
affordances in code and docs, fix the live observed-path scoring asymmetry,
surface preflight evidence and fairness findings directly in the report
contract, and raise the corpus seriousness floor with more multi-file,
producer-consumer, recovery, external-wait, and destructive-scope scenarios.

## Scope
- update benchmark governance truth, release targeting, component truth, and
  Atlas storytelling for the full-product comparison contract
- capture the existing fairness failures in Casebook before changing the
  harness
- harden the live benchmark runner so preflight evidence and observed-path
  credit are explicit, symmetric where required, and inspectable in reports
- keep packet-only diagnostic scaffolding explicit by whitelisting
  `benchmark.packet_fixture` usage and surfacing focused no-op proof through
  `validator_status_basis` instead of implicit validator success
- expand the implementation corpus to a release-safe seriousness floor with
  validator-backed, repo-grounded real-world scenarios
- align benchmark docs, graphs, and proof outputs to the new contract on the
  same release tree
- keep full-corpus proof operationally feasible by allowing shard execution
  only when the release lane is rebuilt into one merged full-proof report
  before publication

## Non-Goals
- inventing a second public benchmark lane in `0.1.11`
- weakening the raw baseline or repo-scan lanes to flatter Odylith
- expanding into Claude-host benchmark proof before the Codex-host proof is
  honest and strong enough

## Risks
- a more honest and harder benchmark could reduce the published Odylith
  advantage before later product improvements recover it
- corpus expansion can increase proof cost if scenario distribution is not kept
  deliberate
- fairness and report-field additions could accidentally reopen `B-091` sync
  churn if they are not kept additive and content-addressed

## Dependencies
- `B-021` owns the broader benchmark corpus and proof-hardening umbrella
- `B-022` established the benchmark reporting and publication flow being
  hardened
- `B-091` owns the governed-sync invariants that this workstream must preserve

## Success Metrics
- the primary published benchmark claim explicitly says
  `full_product_assistance_vs_raw_agent`
- live benchmark results surface declared affordances, preflight evidence
  provenance, observed-path sources, fairness findings, and corpus composition
- the tracked implementation corpus reaches a serious release-safe floor with
  enough write-plus-validator and correctness-critical scenarios
- the latest proof covers the full tracked corpus instead of a stale smaller
  subset

## Validation
- run focused benchmark fairness, runner, and corpus tests for the changed
  paths
- run `odylith benchmark --repo-root . --profile diagnostic`
- run `odylith benchmark --repo-root . --profile proof`
- run full sync, standalone check-only sync, backlog validation, component
  registry validation, and Atlas render for `D-024`

## Rollout
Land the benchmark contract and fairness fixes first, then expand the corpus
and regenerate the proof and publication artifacts from the validated report
selected for `0.1.11`.

## Why Now
The execution-governance benchmark family is already in flight, and its proof
is only credible if the parent comparison contract is honest and the corpus is
serious enough to mean something outside the product repo.

## Product View
The benchmark should answer the real product question: whether the full
Odylith assistance stack makes the same host agent perform better on real
coding work.

## Impacted Components
- `benchmark`
- `execution-governance`
- `odylith-context-engine`

## Interface Changes
- benchmark report contract gains explicit comparison, fairness, and corpus
  composition fields
- benchmark publication language and graphs shift from “grounding-only” to the
  full-product assistance framing

## Migration/Compatibility
- additive benchmark contract only
- no consumer migration required
- generated benchmark docs, graphs, and bundle mirrors must stay aligned to the
  same source-of-truth report

## Test Strategy
- add focused fairness tests for prompt-visible paths, preflight evidence, and
  focused no-op proxy basis
- add corpus-hardening tests for seriousness thresholds and publication
  coverage
- rerun full benchmark proof, browser coverage, governed-sync proof, and repo
  validators on the same tree

## Open Questions
- whether a later post-`0.1.11` wave should publish narrower internal ablations
  such as grounding-only or no-preflight-evidence once the primary full-product
  comparison is stabilized
