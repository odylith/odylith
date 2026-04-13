---
status: implementation
idea_id: B-021
title: Complex-Repo Benchmark Corpus Expansion and Frontier Improvement
date: 2026-03-29
priority: P0
commercial_value: 5
product_impact: 5
market_value: 5
impacted_parts: benchmark corpus realism, developer-first family ordering, benchmark frontier, guidance-memory recovery, warm/cold proof determinism, weak-family boundedness, benchmark graphs, README and benchmark docs narrative, and benchmark trust hardening
sizing: L
complexity: High
ordering_score: 100
ordering_rationale: Odylith's benchmark lane is now trustworthy enough that the next missing piece is breadth, realism, and developer legibility. The corpus still underrepresents the most normal coding-agent shapes: CLI regressions, config compatibility bugs, runtime state integrity, browser-backed onboarding fixes, and managed runtime repair. Expanding the corpus around those workloads while improving the weak live families will make the benchmark harder to dismiss as Odylith-product-maintainer theater.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-complex-repo-benchmark-corpus-expansion-and-frontier-improvement.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children: B-068,B-092,B-093
workstream_depends_on: B-009, B-019, B-020
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
---

## Problem
Odylith's benchmark story is credible and stronger than `odylith_off`, but the
current published diagnostic report `74cbe36427f2c375` and live proof report
`926bfeab4e887ade` are both still on `hold`. The remaining blockers are
unnecessary write-surface widening, selected cache-profile gate misses,
tighter-budget behavior under the `0.80` floor, and weak families such as
`architecture`, `compass_brief_freshness`, `component_governance`,
`consumer_profile_compatibility`, `cross_file_feature`, and
`daemon_security`. The corpus also still underweights the most normal
developer-facing coding shapes: CLI regressions, config compatibility, runtime
state integrity, browser-backed onboarding fixes, and managed runtime repair
under real tests.

## Customer
- Primary: Odylith evaluators and maintainers who need the benchmark to reflect
  the real work a serious coding agent performs in a complex governed repo.
- Secondary: Odylith consumers deciding whether Odylith-on is genuinely
  smarter, faster, cheaper, more reliable, and more accurate than Codex alone
  on work that actually matters.

## Opportunity
If Odylith expands the corpus around these higher-signal developer shapes,
restores benchmark guidance memory as a first-class retrieval input, keeps the
governance and architecture truth as secondary coverage, and then improves the
weak live families against that harder mix, the benchmark becomes both harder
and far easier for normal developers to read as a coding-agent benchmark.

## Proposed Solution
Add a broader developer-first set of benchmark scenarios covering CLI contract
regressions, config compatibility, runtime state integrity, browser-backed
onboarding reliability, managed runtime repair, and install or activation
recovery, while keeping the existing release, governance, and architecture
truth families. Add corpus-hardening tests so those scenarios remain present.
Then tune Odylith's live handoff and prompt support-doc selection against the
current weak families before refreshing proof once the benchmark genuinely
improves. Speed or token wins that regress recall, accuracy, precision, fit,
or validator-backed completion still do not count as success.

Treat the current proof report `926bfeab4e887ade` as the protected floor and
the current diagnostic report `74cbe36427f2c375` as the grounding floor:

- restore guidance memory through the canonical manifest at
  `odylith/agents-guidelines/indexable-guidance-chunks.v1.json` and its bundle
  mirror, with family-tagged guidance that benchmark slices can actually
  retrieve
- make benchmark warm preflight fail closed when the guidance catalog is empty
  or lacks family coverage
- move boundedness upstream into candidate selection and packet assembly so
  `required_paths` stay authoritative on already-grounded proof slices
- make warm and cold choose the same truthful slice through deterministic
  candidate tie-breaking and parity tests
- focus the next weak-family recovery wave on `component_governance`,
  `compass_brief_freshness`, `consumer_profile_compatibility`,
  `daemon_security`, `cross_file_feature`, and remaining budget misses
- keep the first pass local-memory-first on LanceDB plus Tantivy; Vespa stays
  optional and hybrid rerank remains an off-by-default weak-family experiment

Codify the benchmark decision ladder explicitly so Odylith is optimized in the
right order:
1. correctness and non-regression
2. grounding recall and precision
3. validation success and execution fit
4. robustness across cache states, retries, and recovery
5. latency to a valid outcome
6. prompt and payload efficiency
7. bounded behavior under tighter token budgets

## Scope
- expand the benchmark corpus with more representative developer-first and
  SWE-bench-like local scenarios
- make the metric-priority order explicit in benchmark source truth and
  maintainer guidance
- include more correctness-sensitive scenarios with required paths and explicit
  validation commands
- ensure the corpus spans small, medium, and large or complex repo work across
  single-file, cross-file, and cross-surface tasks
- reorder README and graph storytelling around the developer-first archetypes
- add corpus-hardening tests so the new scenario families do not silently
  disappear
- improve Odylith's benchmark frontier against the harder corpus
- restore benchmark guidance memory and make family-aware guidance retrieval
  visible on benchmark slices
- make warm/cold packet selection deterministic across narrow proof slices
- keep benchmark docs, Radar, Registry component specs, Atlas, and bundled
  guidance mirrors aligned to the same `2026-04-05` hold posture and pass
  recovery plan
- rerun the Codex benchmark harness and refresh README plus graph assets from
  the new strongest validated report

## Non-Goals
- introducing hosted eval infrastructure
- creating a Claude-native benchmark lane
- weakening the benchmark to preserve flattering numbers

## Risks
- a tougher corpus could initially reduce Odylith's published benchmark
  advantage
- adding many scenarios could increase local benchmark time
- if the new scenarios are not carefully grounded, the corpus could become
  noisy instead of honest
- fail-closed weak-family ceilings could accidentally drop required evidence if
  family tags or deterministic tie-breaks are wrong

## Dependencies
- `B-009` established the benchmark corpus truth and parity gate
- `B-019` improved the benchmark frontier
- `B-020` made benchmark publication conservative and first-class in Registry
  plus Atlas

## Success Metrics
- the benchmark corpus includes materially broader developer-core coding-agent
  scenarios than the current Odylith-maintainer-shaped set
- Odylith still clears the benchmark gate on the tougher corpus
- Odylith improves the benchmark in the right order:
  correctness, recall, precision, validation, and robustness first; latency
  and token cost second
- no claimed benchmark improvement is accepted if recall, accuracy, or
  precision regresses in exchange for speed or budget wins
- the next proof clears both cache profiles, keeps `within_budget_rate >= 0.80`,
  and does not regress the current `926bfeab4e887ade` proof floor
- the next diagnostic rerun preserves or improves the `74cbe36427f2c375`
  grounding gains while removing the observed-surface drift and cache-coverage
  blocker
- the published corpus clearly covers normal developer bug-fix or feature
  shapes, not just Odylith governance shapes
- README, benchmark docs, Registry truth, Atlas proof lane, and Compass digest
  all reflect the same developer-first ordering and current report posture

## Validation
- `odylith benchmark --repo-root .`
- `odylith benchmark --repo-root . --profile diagnostic`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_tooling_guidance_catalog.py tests/unit/runtime/test_tooling_context_retrieval_guidance.py tests/unit/runtime/test_odylith_benchmark_prompt_regressions.py tests/unit/runtime/test_odylith_benchmark_preflight.py tests/unit/runtime/test_odylith_benchmark_runner.py`
- `PYTHONPATH=src python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks`
- `PYTHONPATH=src python -m odylith.runtime.evaluation.odylith_benchmark_graphs --repo-root . --out-dir docs/benchmarks --profiles diagnostic proof`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_graphs.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/test_cli.py`
- `git diff --check`

## Rollout
Land the guidance-memory recovery and fail-closed packet-boundedness wave
first, refresh the governed benchmark surfaces, expand the developer-core
corpus, then rerun targeted weak-family shards followed by the full proof
before moving the public headline again.

## Why Now
Odylith has already proven a compact benchmark lane. The next credibility jump
comes from making that lane read like the work developers actually expect a
coding agent benchmark to solve.

## Product View
If Odylith is supposed to change the outcome on serious repo work, the
benchmark should prove that on slices that feel like real coding work first,
not only on Odylith's own governance-maintainer truth.

## Impacted Components
- `benchmark`
- `odylith-context-engine`
- `odylith`
- `subagent-orchestrator`
- `release`
- `dashboard`
- `compass`
- `odylith-memory-backend`

## Interface Changes
- `odylith benchmark` runs against a broader, more developer-legible corpus
- README and graph ordering become archetype-first instead of token-cost-first
- the public benchmark story separates current published proof from next-wave
  corpus additions cleanly
- the canonical benchmark guidance-manifest path becomes
  `odylith/agents-guidelines/indexable-guidance-chunks.v1.json`, with bundle
  mirrors and family-affinity metadata treated as benchmark inputs

## Migration/Compatibility
- no consumer migration required
- benchmark history remains readable
- corpus expansion is additive and backward compatible with the current report
  contract

## Test Strategy
- add corpus-hardening tests for scenario count and required developer-core
  family coverage
- rerun the full benchmark harness
- refresh graphs only after the stronger report is validated

## Open Questions
- how far should the local product-repo developer slice go before Odylith
  should split out a separate external SWE-bench-like benchmark lane

## Current Status
- Guidance-memory recovery, weak-family packet shaping, and truthful packet
  diagnostics are already landed.
- `daemon_security` is no longer a weak live family; warm proof
  `f610654ed299d4f0` and cold proof `21d2c37e284693e4` both clear with
  validator-backed no-op, full recall, full precision, zero hallucinated
  surfaces, and zero widening against `odylith_off`.
- The remaining active runtime blockers for this workstream are now the live
  proof completions on `component_governance`,
  `compass_brief_freshness`, `consumer_profile_compatibility`, and
  `cross_file_feature`, plus the next developer-core corpus growth wave.
- README headline movement stays frozen until those remaining proof blockers
  clear and a stronger full proof exists.
