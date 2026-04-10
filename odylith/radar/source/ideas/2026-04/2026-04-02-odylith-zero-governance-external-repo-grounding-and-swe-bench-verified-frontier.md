---
status: queued
idea_id: B-042
title: Zero-Governance External-Repo Grounding and SWE-bench Verified Frontier
date: 2026-04-02
priority: P0
commercial_value: 5
product_impact: 5
market_value: 5
impacted_parts: external repo grounding, issue-to-code localization, targeted validation ladders, external benchmark solve rate, patch quality, and zero-governance control-plane efficiency
sizing: L
complexity: VeryHigh
ordering_score: 100
ordering_rationale: If Odylith cannot outperform a raw coding agent on a vanilla external repo with no preexisting governance truth, then the system still lacks a strong answer to the most skeptical external benchmark question, even if its governed-repo story is already strong.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-022
workstream_children:
workstream_depends_on: B-022,B-041
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
On vanilla SWE-bench and SWE-bench Verified repos there is no local `odylith/`
tree carrying backlog, specs, topology, or case memory. That means Odylith
cannot rely on its strongest governed-repo advantage. It can only win through
better operating policy: better retrieval, narrower localization, stronger test
selection, better patch iteration, and more disciplined recovery under hidden
tests.

Today Odylith is optimized primarily for governed repos where repo-native truth
already exists or can be refreshed. On external benchmark repos without that
substrate, Odylith risks paying extra control-plane cost without gaining enough
search, validation, or recovery advantage to beat `odylith_off`.

## Customer
- Primary: Odylith benchmark maintainers who need an honest answer to whether
  Odylith has intrinsic execution value on plain repos.
- Secondary: engineering leaders who will discount governed-repo wins unless
  Odylith can also show strength on benchmark repos with no native Odylith
  truth.

## Opportunity
If Odylith learns to perform strongly in the zero-governance external lane, it
proves that the product adds value even before governance truth exists. That
also increases the return on future governance layers because the control plane
itself becomes stronger instead of merely more informed.

## Proposed Solution
Add a zero-governance external-repo mode tuned for issue-driven repair on
unfamiliar Python repositories:

- derive a narrow working slice from the problem statement, stack traces, file
  references, symbol names, import graph neighborhoods, test naming patterns,
  and package layout
- maintain transient memory only inside the isolated benchmark workspace or
  temp home, not in the target repo, so the run stays faithful to a
  no-local-truth contract
- build a validation ladder that starts from reproducing the reported failure,
  then runs the smallest likely `FAIL_TO_PASS`-relevant check, and only then
  widens toward broader regression coverage to protect `PASS_TO_PASS`
- add repo-shape heuristics for common SWE-bench Python topologies including
  `pyproject.toml`, `setup.py`, `setup.cfg`, `tox.ini`, package test mirrors,
  docs-driven issue reports, and namespace-package layouts
- improve recovery posture for long dependency installs, partially failing test
  environments, missing extras, and over-broad first patches
- classify failures so Odylith can distinguish localization misses from
  environment/setup failures and validation mistakes

The lane should stay strict about allowed information:

- issue text is allowed
- repo contents at the benchmark commit are allowed
- hidden tests, merged PR diffs, and later maintainer discussion are not
  allowed

## Scope
- external-repo retrieval and localization heuristics
- transient memory and context-packet shaping for no-governance runs
- targeted validation ladder design for hidden-test evals
- timeout and retry policy tuned for long-running benchmark environments
- cost controls so Odylith does not lose by over-searching or over-validating
- per-instance failure classification needed to improve this lane honestly

## Non-Goals
- generating repo-local governance truth inside the target repo
- using hidden tests or solution metadata to shortcut localization
- claiming that a zero-governance external benchmark win proves governance
  value
- over-optimizing to one benchmark repo by hardcoding repo-specific behaviors

## Risks
- external repo heuristics can become a brittle benchmark-specialized policy
  instead of a general repo-grounding improvement
- validation ladders may still miss the true hidden-test contract if the issue
  statement is underspecified
- the agent can spend too much budget on environment triage and too little on
  patch quality if recovery policy is not tightly bounded
- improvements tuned for Python issue-fix benchmarks may not transfer cleanly
  to Odylith's broader multi-surface governed-repo work

## Dependencies
- `B-041` must provide the official-compatible harness and prediction contract
- `B-022` still governs fairness and no-gaming requirements
- official SWE-bench Verified evaluation remains hidden-test based, so local
  validation must remain a proxy rather than a leaked oracle

## Success Metrics
- `odylith_on` beats `odylith_off` on the zero-prep external lane over the same
  instance set with the same model and budget contract
- no-patch, wrong-localization, and under-validation failure classes decline
  materially after the runtime wave lands
- Odylith's solve-rate gains do not come from broader or looser prompts that
  simply spend much more budget than the matched baseline
- the external lane produces actionable failure classes instead of a single
  undifferentiated pass/fail number

## Validation
- paired local-harness runs on a targeted public development slice with fixed
  time and token budgets
- failure-taxonomy review on every miss to confirm whether the loss came from
  repo grounding, issue interpretation, validation, environment setup, or patch
  quality
- regression checks ensuring zero-governance external mode does not leak
  repo-local truth generation into the target workspace
- `git diff --check`

## Rollout
Stand up the adapter first, then use a small public slice to harden
localization and validation behavior, and only after the zero-governance lane
shows real paired gains should Odylith scale to larger public runs.

## Why Now
The strongest skeptical question is not whether Odylith helps when it gets more
truth. It is whether Odylith still helps when the repo gives it almost none.

## Product View
If Odylith cannot win without governance truth, then governance truth is doing
all the work. The product should be able to improve the operating policy even
before the repo becomes governed.

## Impacted Components
- `benchmark`
- `odylith-context-engine`
- `subagent-orchestrator`
- `tribunal`

## Interface Changes
- Odylith gains a bounded external-repo mode tuned for issue-driven repair on
  repos with no local Odylith substrate
- benchmark reports can distinguish zero-governance external results from
  governed-repo and bootstrapped-consumer results
- maintainers get explicit failure classes for external misses instead of only
  raw unresolved counts

## Migration/Compatibility
- no consumer migration required
- zero-governance external mode should remain an additive benchmark capability,
  not a change to Odylith's default governed-repo behavior
- existing product-repo benchmark metrics remain the primary published product
  claim

## Test Strategy
- add targeted unit tests for external repo localization and validation-ladder
  policy helpers
- add integration tests that verify zero-governance mode does not write
  governance truth into the target repo
- use paired smoke slices to compare token spend, localization accuracy, and
  resolved-rate deltas against `odylith_off`

## Open Questions
- whether Odylith should expose a dedicated external-mode selector or infer
  this posture solely from benchmark runner context
- how far repo-topology heuristics can go before they become benchmark-tuned
  rather than generally useful
