---
status: queued
idea_id: B-043
title: Odylith Bootstrapped Consumer Governance Lane for SWE-bench Verified
date: 2026-04-02
priority: P1
commercial_value: 4
product_impact: 5
market_value: 5
impacted_lanes: both
impacted_parts: consumer bootstrap truth generation, same-truth external benchmarking, generated-governance provenance, frozen snapshot fairness, and governance-value attribution
sizing: L
complexity: VeryHigh
ordering_score: 92
ordering_rationale: Once Odylith can run honest zero-governance external evals, the next missing proof is whether generated repo-local governance truth widens the gap against the same raw coding agent on the same benchmark repo without relying on hidden-answer leakage or hand-authored overlays.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-022
workstream_children:
workstream_depends_on: B-022,B-041,B-042
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
Zero-governance external performance can prove that Odylith has intrinsic
control-plane value, but it still cannot answer the more product-specific
question: does generated repo-local governance truth materially improve coding
outcomes when both Odylith and the raw coding agent can read the same truth?

Today there is no benchmark-safe bootstrap lane for external repos that:

- creates a minimal consumer-owned `odylith/` tree from only the allowed
  benchmark inputs
- freezes that generated truth so both lanes use the exact same snapshot
- lets `odylith_off` explicitly read the generated truth while still denying it
  Odylith's grounding and execution scaffold
- proves that the generated truth did not leak hidden tests or solution-only
  information

Without that lane, Odylith can either prove zero-governance control-plane value
or governed internal-repo value, but not the causal middle ground on an
external benchmark.

## Customer
- Primary: Odylith evaluators who want a clean experimental design separating
  governance value from raw orchestration value.
- Secondary: enterprise architects who care less about benchmark names than
  about whether a governance system compounds with the same underlying coding
  model on the same repo.

## Opportunity
If Odylith can create a mechanically auditable same-truth external lane, then
it gains a much stronger causal story:

- zero-prep external proves intrinsic operating-policy value
- bootstrapped external proves generated governance value on top of that
- governed internal-repo proof remains the strongest product-native case

That three-part story is more technically honest than collapsing everything
into one headline percentage.

## Proposed Solution
Create a benchmark bootstrap pipeline for external repos that:

- installs or materializes a minimal Odylith consumer substrate into the target
  repo snapshot using only allowed inputs: benchmark repo contents, issue text,
  deterministic repo analysis, and explicitly declared benchmark heuristics
- generates bounded repo-local truth such as an active workstream record,
  scoped component or topology hints, validation obligations, and known
  confidence gaps
- annotates every generated artifact with provenance pointing back to the exact
  allowed inputs and heuristics that produced it
- freezes the bootstrapped repo into a snapshot hash that both `odylith_on` and
  `odylith_off` consume identically
- forbids any generated artifact from referencing hidden tests, patch diffs, or
  solution metadata unavailable to the raw benchmark contract

This lane should publish results separately from zero-prep external runs and
should optionally support a 2x2 study:

- raw agent, no generated governance
- raw agent, generated governance available
- Odylith, no generated governance
- Odylith, generated governance available

## Scope
- benchmark-safe Odylith bootstrap for external benchmark repos
- generated-governance schema and provenance format
- snapshot freezing and artifact hashing so both lanes share the same inputs
- fairness checks that reject suspicious generated truth or solution leakage
- reporting that separates orchestration delta from governance delta

## Non-Goals
- hand-authoring benchmark-specific workstreams or plans
- pulling in maintainer discussion, hidden tests, or merged-PR content as
  generated truth
- treating bootstrapped external results as a replacement for Odylith's native
  governed-repo benchmark
- making every external benchmark repo look like a fully governed enterprise
  repo in one wave

## Risks
- generated truth can accidentally encode answer hints if provenance checks are
  weak
- even allowed-input generation may produce noisy or low-value governance that
  adds cost without helping solve rate
- bootstrapped runs may be misunderstood as zero-prep external results unless
  publication boundaries stay explicit
- the bootstrap contract may become too benchmark-specific if it is tuned only
  to SWE-bench Python repos

## Dependencies
- `B-041` provides the external harness and artifact pipeline
- `B-042` should first establish a strong zero-governance external baseline so
  governance gains are measured on top of a credible control-plane baseline
- `B-022` remains the fairness and anti-gaming umbrella

## Success Metrics
- Odylith can generate a frozen same-truth benchmark repo snapshot from allowed
  inputs only
- `odylith_off` can explicitly read the generated truth while remaining free of
  Odylith scaffold or automatic guidance
- provenance checks can explain every generated artifact without hidden or
  solution-only sources
- bootstrapped external reporting separates governance delta from orchestration
  delta clearly enough that skeptical reviewers can audit the claim

## Validation
- provenance-audit tests for every generated truth artifact
- snapshot-hash checks proving both compared lanes consumed the identical
  bootstrapped repo state
- paired runs comparing zero-prep and bootstrapped external lanes on the same
  public development slice
- `git diff --check`

## Rollout
Prove zero-governance external capability first, then add the bounded bootstrap
generator on a tiny slice, and only after provenance and fairness checks are
strong should Odylith publish same-truth external comparisons.

## Why Now
Odylith's long-term claim is not merely that it can search a repo well. It is
that governed repo truth compounds model performance. External benchmarks need a
benchmark-safe way to test that claim.

## Product View
The right question is not whether Odylith can make up a governance story on an
outside repo. It is whether Odylith can generate honest local truth from the
same allowed evidence and then operationalize that truth better than the raw
agent.

## Impacted Components
- `benchmark`
- `radar`
- `registry`
- `atlas`
- `odylith-context-engine`

## Interface Changes
- external benchmark runs gain a distinct bootstrapped-consumer lane with
  generated-truth provenance
- reports can separate zero-prep external deltas from same-truth external
  deltas
- maintainers gain explicit artifact hashes and provenance trails for generated
  governance in external runs

## Migration/Compatibility
- no consumer migration required
- bootstrapped external benchmarking is additive and should not affect normal
  consumer installs or product-repo benchmark runs
- generated external truth should use a bounded schema subset so future
  contract changes remain migratable

## Test Strategy
- add provenance and snapshot-consistency tests first
- add guard tests proving that generated external truth never references hidden
  tests, solution patches, or post-issue maintainer discussion
- use paired public slices to verify whether generated governance improves
  solve rate, localization, and validation without blowing up cost

## Open Questions
- how small the initial generated-truth schema should be to maximize fairness
  and minimize leakage risk
- whether the 2x2 external study should be required before any public
  governance-delta claim ships
