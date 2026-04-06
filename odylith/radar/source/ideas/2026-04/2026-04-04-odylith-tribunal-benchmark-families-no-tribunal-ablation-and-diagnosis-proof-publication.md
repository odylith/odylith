---
status: queued
idea_id: B-046
title: Odylith Tribunal Benchmark Families, No-Tribunal Ablation, and Diagnosis-Proof Publication
date: 2026-04-04
priority: P1
commercial_value: 4
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: internal benchmark corpus, Tribunal-specific evaluation families, benchmark ablation lanes, diagnosis and recovery proof, and README benchmark publication discipline
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith is now leaning on Tribunal as a product strength, but the current benchmark corpus does not isolate or measure that diagnosis advantage directly. Tribunal-shaped families plus a no-Tribunal ablation are the cleanest way to prove the claim without weakening the honest `odylith_on` versus `odylith_off` headline.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-022
workstream_children:
workstream_depends_on: B-022,B-039
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
Odylith can honestly say Tribunal is a product strength, but the current
benchmark corpus still underrepresents diagnosis-heavy and recovery-heavy
shapes, and the runner has no secondary lane that isolates the contribution of
Tribunal itself.

Without Tribunal-specific families and a no-Tribunal ablation, Odylith can talk
about diagnosis and structured recovery, but it cannot yet prove where that
engine materially improves outcomes and where it does not.

## Customer
- Primary: Odylith maintainers and reviewers who want Tribunal claims to be
  backed by hard benchmark evidence instead of product intuition.
- Secondary: skeptical evaluators who need to see whether diagnosis quality is
  a real Odylith advantage or just a narrative layer around the same coding
  behavior.

## Opportunity
If Odylith can show that Tribunal improves diagnosis-heavy cases on the same
repo, same model, and same validator contract, it gets a much more defensible
benchmark story. The same work also tells maintainers whether the next limit is
diagnosis quality, implementation quality, or something else.

## Proposed Solution
Expand the internal benchmark with Tribunal-shaped cases and add a secondary
`odylith_on_no_tribunal` lane that keeps the same task, model, budget, and
validator contract while removing Tribunal as a measured ablation.

The new cases should cover diagnosis and recovery shapes such as:

- wrong-but-plausible first fixes
- competing ownership or authority explanations
- evidence-insufficient stop or no-edit cases
- rival-explanation selection
- discriminating next-check selection
- rollback versus forward-fix choice after failed validation

README and benchmark-publication copy should only make stronger Tribunal claims
after the expanded corpus reruns and the measured evidence supports them.

## Scope
- add Tribunal-specific benchmark families or family slices to the internal
  corpus
- add `odylith_on_no_tribunal` as a secondary benchmark ablation lane
- extend benchmark reporting and graphs so Tribunal delta is inspectable
  without replacing the public `odylith_on` versus `odylith_off` headline pair
- gate any stronger Tribunal benchmark claims on reruns from the expanded
  corpus

## Non-Goals
- changing the primary public benchmark comparison away from `odylith_on`
  versus `odylith_off`
- benchmarking Tribunal on flows that do not actually invoke it
- weakening the corpus to manufacture a cleaner Tribunal story
- turning README copy into benchmark proof without a rerun

## Risks
- diagnosis-shaped cases could become too synthetic if they do not resemble
  real repo work
- a no-Tribunal ablation could blur the boundary between Tribunal and
  Remediator unless the lane contract is explicit
- additive lanes and graphs can make benchmark reporting harder to read if the
  primary pair is not kept visually central

## Dependencies
- `B-022` remains the honest-benchmark umbrella
- `B-039` is the current corpus-expansion and publication-refresh baseline this
  follow-on extends

## Success Metrics
- the benchmark corpus includes explicit Tribunal-shaped diagnosis or recovery
  coverage
- the benchmark runner can compare `odylith_on`, `odylith_on_no_tribunal`, and
  `odylith_off` on the same scenarios without disturbing the primary public
  pair
- README and benchmark docs can ground Tribunal-specific claims in measured
  rerun evidence instead of inference

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_odylith_benchmark_graphs.py`
- focused benchmark reruns on the added Tribunal-shaped cases and the new
  ablation lane
- `git diff --check`

## Rollout
Land the new cases and the no-Tribunal lane first, rerun the benchmark, inspect
whether Tribunal materially changes diagnosis-heavy outcomes, and only then
upgrade any public Tribunal benchmark language.

## Why Now
Odylith now names Tribunal explicitly in the product story. The benchmark
should catch up before the next release makes that story sound more proven than
it is.

## Product View
If Tribunal is real leverage, the scoreboard should show it directly. If it
does not survive a no-Tribunal ablation on diagnosis-heavy cases, then it is
not yet a benchmark-ready claim.

## Impacted Components
- `benchmark`
- `tribunal`
- `remediator`

## Interface Changes
- internal benchmark reports gain an `odylith_on_no_tribunal` secondary lane
- benchmark graphs and review docs can show Tribunal-specific deltas on the
  expanded corpus
- README benchmark claims about Tribunal become explicitly tied to measured
  reruns from that corpus

## Migration/Compatibility
- no consumer migration required
- the new lane is additive and should not change the primary public benchmark
  pair
- older benchmark history should remain readable even when the new lane is
  absent

## Test Strategy
- add corpus tests that keep Tribunal-shaped cases distinct and realistic
- add runner tests proving the no-Tribunal lane stays isolated from the
  primary pair
- add graph and report tests that degrade cleanly on older reports without the
  new lane

## Open Questions
- whether `odylith_on_no_tribunal` should remove only Tribunal reasoning or
  also remove Remediator packet shaping
- whether Tribunal cases deserve one new family or should be distributed across
  existing weak families with an explicit diagnosis tag
