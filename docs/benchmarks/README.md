# How To Read Odylith's Benchmark Proof

This folder explains the benchmark graphs published in the root
[README](../../README.md).

> [!IMPORTANT]
> **FIRST PUBLIC EVAL RUNS.**
>
> These reports are Odylith's first public eval runs and the live measurement
> baseline for the benchmark program.
>
> Odylith will keep using these runs to measure itself, expand the corpus,
> rerun the proof, and improve grounding, orchestration, diagnosis, recovery,
> and closeout quality from here.
>
> More archetypes and benchmark families will be added as Odylith expands the
> corpus and pressure-tests more of the real operating surface.

Related docs:

- [Current Grounding Benchmark Snapshot](GROUNDING_BENCHMARK_SNAPSHOT.md)
- [Benchmark Tables](BENCHMARK_TABLES.md)
- [Current Live Benchmark Snapshot](LIVE_BENCHMARK_SNAPSHOT.md)
- [Benchmark Families And Eval Catalog](FAMILIES_AND_EVALS.md)
- [Metrics And Priorities](METRICS_AND_PRIORITIES.md)
- [Benchmark Formal Model](../research/BENCHMARK_FORMAL_MODEL.md)
- [Reviewer Guide And Prompt](REVIEWER_GUIDE.md)

## What Is Being Compared

The canonical public proof compares two host-matched lanes on the same benchmark
contract:

- `odylith_on`
  the proof host runs with the full Odylith assistance stack: grounding,
  narrowed evidence, repo-local memory, governance surfaces,
  execution-engine posture, truthful next-move guidance, and bounded
  orchestration or recovery policy.
- `odylith_off`
  is the public name for the raw host CLI lane. Internally the report may still
  store this as `raw_agent_baseline`, but the lane itself is the same live CLI
  with no Odylith packet and no auto-consumed repo guidance entrypoints in the
  disposable benchmark workspace.

The public headline comparison is:

- `odylith_on` versus `odylith_off`

Secondary lanes still exist for diagnosis:

- `odylith_on_no_fanout`
  shows what bounded fanout adds on top of the same Odylith packet
- `odylith_repo_scan_baseline`
  shows what a repo-scan scaffold adds compared with truly turning Odylith off

The public headline claim stays on the matched `odylith_on` versus
`odylith_off` pair.

The published benchmark views answer different questions:

- `Live Benchmark`
  Does the report-visible Odylith operating policy make the same host reach a more
  validated, better-grounded, and less needlessly mutating outcome than the raw
  host CLI?
- `Grounding Benchmark`
  Does Odylith build a better grounded packet or prompt than `odylith_off`
  before the live run starts? This is the mechanism-evidence view that supports
  the product comparison.

The Live Benchmark governs the operating-policy product comparison. It includes
report-visible validator-backed closure and write admission, so focused
non-mutating closure rows are valid non-mutation and write-admission evidence.
The Grounding Benchmark matters when it preserves or improves the Live
Benchmark.

The generic interpretation rule is: every benchmark row is evidence about a
policy decision under a declared contract. The row may prove grounding quality,
validation quality, fail-closed behavior, write admission, recovery posture, or
time and token efficiency. The visible scenario state, validator, and report
basis define the estimand for that row.

The current full live proof was executed on Codex. Codex and Claude quick
smokes provide bounded host-agnostic coverage, and a full Claude-host proof
would be a separate published benchmark run.

Tracked source truth now carries a more serious benchmark corpus than the last
published reports: `82` tracked scenarios (`77` operating-policy plus `5`
architecture), including explicit API evolution, stateful recovery,
external-dependency recovery, destructive-scope control, Context Engine,
Execution Engine, Guidance Behavior, and Discipline families. Publication
claims must be refreshed from a rerun before they can speak for that expanded
corpus.

## Closeout Framing

Benchmark summaries should lead with measured proof and evidence-backed product
interpretation.
If Odylith is named directly beyond lane labels, keep it to one evidence-backed
`Odylith Assist:` line at closeout or for explicit visibility-feedback
fallback, backed by measured proof or a measured report, and follow
[Odylith Chatter](../../odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md)
for the detailed closeout wording contract, including the rule that any
supplemental line must render before the final Assist line. Keep the benchmark
lane metadata-only: do not widen required paths, hot-path docs, or validation commands just
to narrate Odylith.

## Run Views

Odylith publishes three benchmark views:

- `quick`
  local developer signal on the honest public pair
- `Live Benchmark`
  full publication proof on the live `odylith_on` versus `odylith_off` pair
- `Grounding Benchmark`
  packet-and-prompt tuning without the live end-to-end host pair

Canonical commands:

- `./.odylith/bin/odylith benchmark --repo-root .`
- `./.odylith/bin/odylith benchmark --repo-root . --profile proof`

The main machine-readable artifacts are:

- `.odylith/runtime/odylith-benchmarks/latest.v1.json`
  latest full-corpus proof artifact
- `.odylith/runtime/odylith-benchmarks/latest-proof.v1.json`
  proof alias
- versioned raw-source bundle
  archived Grounding Benchmark source JSON and logs
- `docs/benchmarks/release-baselines.v1.json`
  versioned passing proof baselines

## Current Published Snapshot

Current published artifacts should be read from the generated snapshot files,
not copied into this overview by hand:

- [Current Grounding Benchmark Snapshot](GROUNDING_BENCHMARK_SNAPSHOT.md)
- [Current Live Benchmark Snapshot](LIVE_BENCHMARK_SNAPSHOT.md)
- [Benchmark Tables](BENCHMARK_TABLES.md)
- `docs/benchmarks/latest-summary.v1.json`
- `docs/benchmarks/proof/*.svg`
- `docs/benchmarks/grounding/*.svg`
- `docs/benchmarks/v0.1.11/`
  versioned GitHub artifact bundle for the current proof, including compressed
  raw source truth, provenance, rendered docs, and graphs
- `docs/benchmarks/v0.1.10/`
  previous README-backed benchmark archive

Do not infer release-safe benchmark posture from stale report ids outside the
current snapshot or versioned artifact folders. The serious claim only
refreshes when the selected proof report, generated snapshot docs,
README-linked profile graph artifacts, and registry or governance truth all
move together on the same validated tree.

## Fair Comparison Protocol

To compare Odylith fairly, hold these constant on both sides:

- the same base model and model version
- the same reasoning-effort setting
- the same repo commits and task corpus
- the same prompt shape, task wording, and success criteria
- the same cache policy, retry budget, timeout policy, and stop rules
- the same validation harness and scoring rules
- the same token and latency accounting
- the same public validator-command contract

For the public `odylith_on` versus `odylith_off` pair, the live runner also
holds these constant explicitly:

- the same host CLI binary
- the same temporary host home with copied auth and pinned model or reasoning
- no personal host instructions, plugins, or MCP config in that temporary
  home
- no auto-consumed `AGENTS.md`, `CLAUDE.md`, `.cursor/`, `.windsurf/`, or
  `.codex/` surfaces in the disposable benchmark workspace
- truth-bearing repo docs remain available for explicit reads

The declared lane difference is explicit, not hidden:

- `odylith_on` may use report-visible Odylith affordances such as selected docs,
  execution-engine posture, product Turn Gate receipts, and validator-backed
  closure evidence
- any Turn Gate early-exit proof in the Odylith lane must come from evidence
  executed inside the disposable benchmark workspace and be surfaced in the
  report
- the report must expose those affordances explicitly through the comparison
  contract, observed-path sources, Turn Gate fields, compatibility
  preflight-evidence fields, and fairness findings

Important reading rule:

- live proof timing is matched-pair benchmark wall clock to a valid outcome,
  not solo-user interactive latency
- live proof token cost is full multi-turn host session spend, not just the
  first prompt
- prompt-bundle efficiency belongs to the Grounding Benchmark, not to the live
  proof lane

## How Status Is Gated

Odylith does not use raw latency or raw token parity as the primary gate.

Status is decided in three layers:

1. `Hard quality gate`
   correctness and non-regression, grounding recall and precision, validation
   success and execution fit, robustness and consistency
2. `Secondary guardrails`
   tighter-budget behavior on packet-backed live proof slices
3. `Advisory mechanism checks`
   packet coverage, widening frequency, route posture, and similar
   explanatory signals

Current live-proof secondary guardrail:

- `within_budget_rate >= 0.80` on packet-backed sampled slices

See [Metrics And Priorities](METRICS_AND_PRIORITIES.md) for the full ordering.
See [Benchmark Formal Model](../research/BENCHMARK_FORMAL_MODEL.md) for the mathematical
interpretation of policy value, write-admission risk, and non-mutating closure
dominance.

## How To Read The Graphs

### Family Heatmap

The family heatmap groups scenarios by task family and shows median deltas.

- rows are ordered by developer-first archetype
  name or raw token delta
- `Recall` means how much better Odylith is at surfacing the repo paths the
  task truly depends on
- `Validation` means how much more often the lane reaches a valid answer path
- `Fit` means how often the lane matches the expected execution posture
- green means Odylith is better on that metric
- red means the baseline is better

### Frontier Graph

The frontier graph shows the same scenario twice:

- red circle: `odylith_off`
- teal diamond: `odylith_on`

Left is fewer live session input tokens. Down is lower time to valid outcome.
The ideal move is down and left, but higher-tier quality still matters more
than cheaper or faster runs.

### Operating Posture Graph

This graph explains whether Odylith actually operated the way the product
claims it should:

- produced a grounded packet
- narrowed the slice
- reached route-ready posture
- enabled native delegation where appropriate
- stayed on the governed runtime path instead of degrading into broad scans

A good score without the intended Odylith operating posture is not a
trustworthy product win.

## How To Compare Odylith Against Another Stack

Use this order:

1. State Odylith's claimed outcome in one sentence.
2. Evaluate `odylith_on` versus `odylith_off` first.
3. Judge results in the benchmark priority order, not feature-count order.
4. Use structural comparison only as secondary explanation.
5. Separate measured proof, plausible benefit, and missing product pieces.

Structural overlap by itself does not answer the benchmark question. Memory,
Registry, Atlas, Compass, orchestration, and similar surfaces only matter here
when they explain an execution consequence.

## What Makes This A Good Eval

A good Odylith eval:

- covers small, medium, and large or complex repo work
- covers single-file, cross-file, and cross-surface scenarios
- includes correctness-sensitive and recovery-sensitive tasks
- tests warm and cold cache posture where the live lane supports it
- gets harder and more realistic over time, not easier

A good Odylith win usually looks like this:

- recall goes up
- validation success goes up
- expectation fit goes up
- hallucinated-surface rate drops
- session cost stays bounded or drops
- time to valid outcome stays flat or improves enough to justify the quality
  gain

## Source Of Truth

The machine-readable sources are:

- `.odylith/runtime/odylith-benchmarks/latest.v1.json`
- `.odylith/runtime/odylith-benchmarks/latest-proof.v1.json`
- versioned raw-source bundle with the Grounding Benchmark source JSON
- `docs/benchmarks/release-baselines.v1.json`

The generated graphs in this folder are derived from those active proof and
Grounding Benchmark artifacts.
