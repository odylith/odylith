---
status: queued
idea_id: B-041
title: SWE-bench External Harness, Predictions Contract, and Reproducible Verified Adapter
date: 2026-04-02
priority: P0
commercial_value: 5
product_impact: 5
market_value: 5
impacted_parts: external benchmark harnessing, SWE-bench Docker evaluation, SWE-bench Verified prediction artifacts, patch serialization, run manifest provenance, and benchmark publication trust
sizing: L
complexity: High
ordering_score: 100
ordering_rationale: Odylith now needs an external benchmark lane that advanced evaluators will recognize, but it has to be built in a way that stays faithful to the official SWE-bench Docker harness and the SWE-bench Verified submission contract instead of turning into a custom internal score with a familiar label.
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
Odylith's current benchmark proof is strong inside its own product repo, but it
does not yet have a first-class adapter for recognized external software
engineering benchmarks. That means there is no canonical way to run
`odylith_on` and `odylith_off` on vanilla SWE-bench repositories, emit official
prediction artifacts, preserve run provenance, or separate local Docker
evaluation from official SWE-bench Verified submission flows.

Without this adapter, external-eval claims will drift into one-off scripts,
hand-assembled patches, undocumented environment assumptions, or mixed
contracts where local smoke runs, dev slices, and leaderboard-compatible test
submissions are all conflated.

## Customer
- Primary: Odylith maintainers and reviewers who need a reproducible and
  auditable path to run Odylith on widely recognized external software-engineer
  benchmarks.
- Secondary: external evaluators, architects, and skeptical engineering leads
  who want proof that Odylith can run a standard contract instead of only a
  product-owned benchmark.

## Opportunity
If Odylith can produce deterministic external-eval artifacts that plug into the
official SWE-bench tooling, then external proof stops being a rhetorical
discussion and becomes a governed engineering workflow. That creates a stable
foundation for both zero-governance external competition and later same-truth
bootstrap experiments.

## Proposed Solution
Build a benchmark adapter layer that can:

- materialize a SWE-bench instance repo at the benchmark commit together with
  the official problem statement and only the allowed benchmark inputs
- run `odylith_on` and `odylith_off` under the same isolated home, timeout,
  model, reasoning, and tool-policy contract
- capture the resulting patch as a deterministic unified diff against the exact
  benchmark snapshot
- serialize those patches into the prediction-file shape expected by the
  official local SWE-bench harness and the official `sb-cli` submission path
- persist a machine-readable run manifest containing dataset, split, instance
  ids, repo revision, agent lane, model, time budget, token budget, container
  posture, prediction hash, and evaluator metadata
- fail closed if any prohibited inputs enter the prompt or runtime context,
  including hidden tests, solution PR diffs, or issue-discussion material that
  the benchmark contract does not allow

The adapter should explicitly separate:

- `local_harness`: local Docker evaluation for original SWE-bench and public
  slices
- `verified_submission`: leaderboard-compatible SWE-bench Verified artifact
  generation and submission preparation
- `zero_prep_external`: vanilla repo, no Odylith governance generation
- `bootstrapped_consumer`: frozen generated Odylith repo-local truth built only
  from allowed benchmark inputs

## Scope
- new benchmark adapter code inside Odylith's evaluation subsystem
- deterministic repo materialization and cleanup for external benchmark
  instances
- prediction serialization and schema validation against the official harness
  contract
- run-manifest capture for hardware, Docker namespace, image provenance, and
  patch digests
- operator documentation for local Docker runs versus official SWE-bench
  Verified submission flows
- explicit fairness guards preventing accidental inclusion of hidden or derived
  answer material

## Non-Goals
- manually editing patches after the agent run to improve the score
- building a custom benchmark that mimics SWE-bench but is not actually
  compatible with the official contract
- mixing multimodal or non-Python benchmark families into the first adapter
  wave
- publishing an external benchmark score before run provenance and prediction
  integrity are mechanical

## Risks
- Docker-heavy local evaluation is resource-intensive and may be impractical on
  undersized development machines without a remote runner path
- ARM and x86_64 differences can create evaluation drift if architecture
  posture is not captured explicitly
- prediction schema or official submission expectations could drift upstream
  and silently invalidate Odylith-generated artifacts
- a weak artifact boundary could accidentally blur dev/test, local/official,
  or zero-prep/bootstrapped comparisons

## Dependencies
- `B-022` defines the umbrella benchmark honesty contract
- `B-039` broadens benchmark diagnostics and publication discipline, which the
  external adapter should reuse instead of inventing separately
- the official SWE-bench local harness and `sb-cli` remain the canonical
  external evaluator contracts

## Success Metrics
- Odylith can generate schema-valid prediction artifacts for targeted
  SWE-bench and SWE-bench Verified runs with no manual post-processing
- every external run emits a manifest that is sufficient to reproduce the
  exact agent lane, dataset slice, repo snapshot, and patch digest
- local external runs remain clearly distinct from official SWE-bench Verified
  submissions in both filenames and published reporting
- the adapter proves that no hidden-test or solution-only artifacts were made
  available to the agent

## Validation
- smoke-test a single public instance end to end through the official local
  Docker harness using an Odylith-generated prediction file
- validate a synthetic prediction manifest against Odylith's schema checks and
  the official submission-file shape
- rehearse `sb-cli` packaging and submission preparation on a non-production
  path before any real external publication
- `git diff --check`

## Rollout
Land the adapter and manifest contract first, then prove local-harness
compatibility on a tiny curated slice, and only after that enable official
SWE-bench Verified artifact generation for real evaluation runs.

## Why Now
Odylith's internal benchmark story is now strong enough that the obvious next
question is whether the same system can compete on a standard external contract.
That answer needs infrastructure before it needs rhetoric.

## Product View
If Odylith wants to be taken seriously beyond its own repo, it has to be able
to walk into an outside benchmark without changing what the benchmark means.

## Impacted Components
- `benchmark`
- `odylith-context-engine`
- `release`
- `dashboard`

## Interface Changes
- maintainers gain an external benchmark adapter that emits official-style
  prediction artifacts instead of ad hoc patch files
- external benchmark runs produce explicit run manifests with lane, hardware,
  and contract metadata
- publication surfaces can distinguish local harness, official submission,
  zero-prep, and bootstrapped runs without ambiguity

## Migration/Compatibility
- no consumer migration required
- existing Odylith product-repo benchmark lanes remain canonical for the
  current product claim
- external benchmark support is additive and should not mutate existing local
  benchmark artifacts

## Test Strategy
- add unit tests for manifest serialization, prediction serialization, and
  fairness-guard enforcement
- add an integration smoke test for materializing one external repo and
  emitting a harness-valid prediction artifact
- keep local external evaluation behind targeted slices until reproducibility
  is established

## Open Questions
- whether Odylith should own a thin local cache of external benchmark repos and
  container images or rely entirely on the upstream harness layout
- whether a remote x86_64 execution service is required for trustworthy local
  maintainership on Apple Silicon machines
