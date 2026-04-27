---
status: queued
idea_id: B-044
title: External Benchmark Failure Taxonomy, Slice Analytics, and Publication Discipline
date: 2026-04-02
priority: P1
commercial_value: 4
product_impact: 4
market_value: 5
impacted_parts: external benchmark evidence, failure taxonomy, slice analytics, publication fairness, score reproducibility, and benchmark narrative discipline
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: External benchmark scores will attract disproportionate attention, so Odylith needs a stronger evidence and publication contract before those numbers become part of the public story; otherwise the repo will optimize toward headlines instead of learning.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-022
workstream_children:
workstream_depends_on: B-022,B-041,B-042,B-043
workstream_blocks:
related_diagram_ids: D-024
workstream_reopens:
workstream_reopened_by:
workstream_split_from: B-022
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
An external benchmark percentage by itself is not a useful steering signal.
Without per-instance failure taxonomy, slice analytics, and strict publication
rules, Odylith will not know whether a miss came from environment setup, issue
misread, localization failure, under-validation, wrong fix, timeout, or
hidden-test mismatch. It also becomes dangerously easy to publish misleading numbers
by mixing dev and test, local harness and official submission, zero-prep and
bootstrapped lanes, or warm and cold container postures.

## Customer
- Primary: Odylith maintainers deciding what to improve next after an external
  benchmark run.
- Secondary: external reviewers and technical decision-makers who need to
  understand what an Odylith score actually means before trusting it.

## Opportunity
If Odylith treats external benchmarks as governed evidence rather than only as
marketing numbers, then every run becomes a structured learning signal. The
same framework also prevents accidental or deliberate publication drift once
leaderboard-style reporting enters the product narrative.

## Proposed Solution
Add an external benchmark reporting contract that captures:

- per-instance terminal outcome classes such as environment-build failure,
  dependency-resolution failure, repo-grounding miss, wrong localization,
  partial fix, regression introduced, under-validation, timeout, no patch,
  invalid patch serialization, and hidden-test mismatch
- slice-level aggregations by repository, difficulty, issue length, patch size,
  test count, package topology, container build cost, and lane type
- publication metadata including dataset, split, instance set, time budget,
  token budget, architecture, Docker namespace, model identifier, seed, and
  whether the run was local harness, official submission, zero-prep, or
  bootstrapped
- pairwise comparisons that keep same-instance, same-budget, same-model runs
  together instead of comparing mixed populations
- explicit no-mixing rules for dev versus test, zero-prep versus bootstrapped,
  and local-harness versus official-submission numbers

The taxonomy should be actionable enough to drive engineering:

- localization failures go to retrieval and slice selection
- under-validation failures go to the test ladder and regression discipline
- environment failures go to harnessing and container posture
- hidden-test mismatches go to issue interpretation and patch generality

## Scope
- external benchmark report schema and storage
- per-instance failure classifier and aggregation logic
- report-generation rules for public and internal external benchmark views
- publication gating that rejects mixed-contract score summaries
- lightweight graphing and reviewer guidance for external benchmark reports

## Non-Goals
- replacing the official SWE-bench evaluator with Odylith's own scoring logic
- publishing every internal experiment externally
- building a full hosted analytics product in the first wave
- pretending that taxonomy removes the need for stronger runtime performance

## Risks
- weak or overly broad failure labels can become subjective and useless
- too many slices or charts can obscure the actual engineering bottlenecks
- publication rules may be ignored unless enforced mechanically in generated
  artifacts and README-facing pipelines
- taxonomy maintenance cost can grow if the categories are not kept compact and
  stable

## Dependencies
- `B-041` provides the external artifact and harness integration
- `B-042` and `B-043` provide the external lanes whose results need to be
  distinguished honestly
- `B-022` remains the anti-gaming umbrella for benchmark publication

## Success Metrics
- every external run can explain unresolved instances via a bounded taxonomy
  instead of a generic miss bucket
- Odylith can publish external benchmark numbers without mixing incompatible
  run contracts
- engineering follow-up work can be prioritized from taxonomy evidence rather
  than only from anecdotal miss review
- public and internal reporting remain mechanically traceable back to exact run
  manifests and instance sets

## Validation
- unit tests for taxonomy normalization, schema validation, and no-mixing
  publication guards
- report-generation smoke tests across zero-prep and bootstrapped run manifests
- reviewer dry run on a small external slice to confirm the taxonomy is compact
  and decision-useful
- `git diff --check`

## Rollout
Land the taxonomy and publication schema before any broad external score
publication, then backfill it onto early smoke runs, and only after it proves
decision-useful should Odylith publish external benchmark summaries prominently.

## Why Now
As soon as Odylith starts running outside benchmarks, the repo will face
pressure to summarize results quickly. Publication discipline has to arrive
before that pressure does.

## Product View
External scores are only useful if they teach us why we won or lost. Otherwise
they become a vanity metric that crowds out the real engineering work.

## Impacted Components
- `benchmark`
- `dashboard`
- `compass`
- `tribunal`

## Interface Changes
- external benchmark reports gain explicit failure classes, lane labels, and
  run-contract metadata
- reviewers can inspect slice-level deltas without confusing local smoke runs
  with official external submissions
- publication pipelines reject mixed or ambiguous external benchmark summaries

## Migration/Compatibility
- no consumer migration required
- external benchmark reporting is additive and should not change the existing
  Odylith-native benchmark report contract
- early external smoke runs may need backfill tooling once the schema lands

## Test Strategy
- keep the taxonomy compact enough for deterministic classification tests
- add publication-gate tests that fail on mixed splits, mixed lanes, or missing
  run-manifest fields
- rehearse report generation on small slices before any README-facing external
  benchmark narrative is allowed

## Open Questions
- whether a single shared taxonomy can serve both internal smoke runs and
  official external submissions without losing too much detail
- whether hidden-test mismatches should remain a terminal bucket or be further
  decomposed once enough failure evidence accumulates
