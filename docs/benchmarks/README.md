# How To Read Odylith's Codex Benchmarks

This folder explains the benchmark graphs published in the root
[README](../../README.md).

> [!IMPORTANT]
> **FIRST PUBLIC EVAL RUNS. THIS IS NOT ODYLITH'S FINAL BENCHMARK POSTURE.**
>
> These reports are Odylith's first public eval runs. Read them as a live
> measurement baseline, not as a claim that the product is done or that the
> current benchmark posture is its final form.
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
- [Reviewer Guide And Prompt](REVIEWER_GUIDE.md)

## What Is Being Compared

The canonical public proof compares two Codex-facing lanes on the same task:

- `odylith_on`
  Codex runs with Odylith grounding, narrowed evidence, repo-local memory,
  governance surfaces, and runtime guidance.
- `odylith_off`
  is the public name for the raw Codex CLI lane. Internally the report may
  still store this as `raw_agent_baseline`, but the lane itself is the same
  live Codex CLI with no Odylith packet and no auto-consumed repo guidance
  entrypoints in the disposable benchmark workspace.

The public headline comparison is:

- `odylith_on` versus `odylith_off`

Secondary lanes still exist for diagnosis:

- `odylith_on_no_fanout`
  shows what bounded fanout adds on top of the same Odylith packet
- `odylith_repo_scan_baseline`
  shows what a repo-scan scaffold adds compared with truly turning Odylith off

Those secondary lanes are not the public headline claim.

The profiles answer different questions:

- `proof`
  Does Odylith beat raw Codex CLI on the same live end-to-end task contract?
- `diagnostic`
  Does Odylith build a better grounded packet or prompt than `odylith_off`
  before the live run starts?

`proof` governs the product claim. `diagnostic` only matters when it preserves
or improves `proof`.

The current published measured proof is Codex-specific. Claude Code may still
benefit from the same grounding and governance surfaces, but that is not yet
Claude-native benchmark proof.

## Closeout Framing

Benchmark summaries should lead with measured proof, not product narration.
If Odylith is named directly beyond lane labels, keep it to one final-only
`Odylith assist:` line backed by measured proof or a measured report, and
follow
[Odylith Chatter](../../odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md)
for the detailed closeout wording contract.

## Run Profiles

Odylith exposes three benchmark profiles:

- `quick`
  local developer signal on the honest public pair
- `proof`
  full publication proof on the live `odylith_on` versus `odylith_off` pair
- `diagnostic`
  packet-and-prompt tuning without the live end-to-end Codex pair

Canonical commands:

- `./.odylith/bin/odylith benchmark --repo-root .`
- `./.odylith/bin/odylith benchmark --repo-root . --profile proof`
- `./.odylith/bin/odylith benchmark --repo-root . --profile diagnostic`

The main machine-readable artifacts are:

- `.odylith/runtime/odylith-benchmarks/latest.v1.json`
  latest full-corpus proof artifact
- `.odylith/runtime/odylith-benchmarks/latest-proof.v1.json`
  proof alias
- `.odylith/runtime/odylith-benchmarks/latest-diagnostic.v1.json`
  diagnostic alias
- `docs/benchmarks/release-baselines.v1.json`
  versioned passing proof baselines

## Current Published Snapshot

Current local published artifacts:

- Grounding Benchmark (`diagnostic`):
  report `74cbe36427f2c375`, status `hold`, `37` scenarios
- Live Benchmark (`proof`):
  report `52aa3f76538cf12f`, status `provisional_pass`, `37` scenarios

Current diagnostic movement versus `odylith_off`:

- `+0.320` required-path recall
- `+0.084` required-path precision
- `+0.690` validation success
- `+1.000` expectation success
- `+47` median prompt-bundle tokens
- `+57` median total-payload tokens
- `+7.045 ms` median packet latency

Current live-proof movement versus `odylith_off`:

- `+0.227` required-path recall
- `+0.168` required-path precision
- `-0.141` hallucinated-surface rate
- `+0.069` validation success
- `+0.124` write-surface precision
- `+0.330` critical required-path recall
- `+0.167` critical validation success
- `+0.393` expectation success
- `-52,561` median live-session input tokens
- `-53,774` median total model tokens
- `-12,426.968 ms` median time to valid outcome

Current live-proof hard-gate blockers:

- none on the current full proof

Current live-proof secondary guardrails:

- both cache profiles clear the hard quality gate
- `within_budget_rate` is back above the `0.80` floor

Current proof attention families:

- `architecture`
- `browser_surface_reliability`
- `component_governance`
- `cross_surface_governance_sync`
- `governed_surface_sync`
- `orchestration_feedback`

Current diagnostic weak families:

- `browser_surface_reliability`
- `install_upgrade_runtime`
- `runtime_state_integrity`

Current product-repo baseline note:

- the current full proof pass is the detached `source-local` benchmark posture
- `benchmark_compare` still reports `warn` until a shipped release baseline is
  recorded in `docs/benchmarks/release-baselines.v1.json`

The published proof view is conservative:

- it uses both `warm` and `cold` cache profiles
- it publishes the less favorable same-profile result per scenario
- it keeps the public headline on the primary pair instead of the prettier
  secondary controls

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

- the same Codex CLI binary
- the same temporary Codex home with copied auth and pinned model or reasoning
- no personal Codex instructions, plugins, or MCP config in that temporary
  home
- no auto-consumed `AGENTS.md`, `CLAUDE.md`, `.cursor/`, `.windsurf/`, or
  `.codex/` surfaces in the disposable benchmark workspace
- truth-bearing repo docs remain available for explicit reads

Important reading rule:

- live proof timing is matched-pair benchmark wall clock to a valid outcome,
  not solo-user interactive latency
- live proof token cost is full multi-turn Codex session spend, not just the
  first prompt
- prompt-bundle efficiency belongs to `diagnostic`, not to the live proof lane

## How Status Is Gated

Odylith does not use raw latency or raw token parity as the primary gate.

Status is decided in three layers:

1. `Hard quality gate`
   correctness and non-regression, grounding recall and precision, validation
   success and execution fit, robustness and consistency
2. `Secondary guardrails`
   tighter-budget behavior on the live proof lane
3. `Advisory mechanism checks`
   packet coverage, widening frequency, route posture, and similar
   explanatory signals

Current live-proof secondary guardrail:

- `within_budget_rate >= 0.80`

See [Metrics And Priorities](METRICS_AND_PRIORITIES.md) for the full ordering.

## How To Read The Graphs

### Family Heatmap

The family heatmap groups scenarios by task family and shows median deltas.

- rows are ordered by developer-first archetype, not by alphabetical family
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
- `.odylith/runtime/odylith-benchmarks/latest-diagnostic.v1.json`
- `docs/benchmarks/release-baselines.v1.json`

The generated graphs in this folder are derived from those active proof and
diagnostic artifacts.
