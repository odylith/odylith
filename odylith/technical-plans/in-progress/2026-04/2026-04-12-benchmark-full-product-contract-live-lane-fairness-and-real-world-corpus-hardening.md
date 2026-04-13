Status: In progress

Created: 2026-04-12

Updated: 2026-04-12

Backlog: B-093

Goal: Make the primary live benchmark contract honest about measuring the full
Odylith assistance stack versus the raw host agent, harden the live fairness
boundaries so scoring is technically defensible, and raise the corpus to a
serious real-world coding-agent bar without regressing governed sync.

Assumptions:
- The primary publication comparison for `0.1.11` should remain
  `odylith_on` versus `odylith_off`, but its meaning needs to be redefined
  explicitly as full-product assistance versus raw agent.
- Pre-run focused-check evidence is acceptable only when it is declared as an
  Odylith affordance, executed in the stripped disposable workspace, counted in
  timing, and surfaced in the report contract.
- Live observed-path scoring must remain symmetric for prompt-visible repo
  anchors even when the Odylith lane has richer prompt payload structure.
- The benchmark claim is not release-safe until the implementation corpus
  reaches a more serious, validator-backed mix and the latest proof covers the
  full tracked corpus.
- `B-091` sync invariants are non-negotiable. Benchmark hardening that
  reopens shared-nothing sync behavior, extra projection passes, or noisy
  no-op writes fails this plan.

Constraints:
- Keep the benchmark contract honest without adding a second public benchmark
  mode in `0.1.11`.
- Do not weaken the raw baseline or repo-scan lanes to flatter Odylith.
- Preserve content-addressed writes and byte-aligned source versus bundle
  mirrors for benchmark artifacts.
- Keep the benchmark scoped to Codex-host proof; do not imply Claude-host proof
  where none exists.

Reversibility: The added report fields, corpus thresholds, and fairness gates
are additive and can be revised in later releases, but the honest full-product
comparison framing is treated as the new release-safe default.

Boundary Conditions:
- Scope includes benchmark governance truth, runner and live execution
  contract, report payloads, corpus source truth, docs, graphs, Registry
  component truth, release proof, and relevant fairness-related Casebook bugs.
- Scope excludes hosted evaluation infrastructure, new public benchmark CLI
  modes, and product changes unrelated to making the current benchmark claim
  honest and serious.

Related Bugs:
- [CB-106](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-12-benchmark-live-preflight-evidence-is-only-injected-for-odylith-on-without-a-declared-comparison-contract.md)
- [CB-107](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-12-benchmark-live-observed-path-scoring-credits-odylith-prompt-surfaces-but-not-equivalent-raw-prompt-anchors.md)

## Learnings
- [ ] A benchmark can be technically isolated and still tell the wrong story if
      the contract language lags behind the real lane affordances.
- [ ] Corpus size alone does not make a benchmark serious; the task mix needs
      enough real write-plus-validator, recovery, and scope-control work to
      support a strong claim.

## Must-Ship
- [ ] Redefine the primary benchmark contract and report language as
      `full_product_assistance_vs_raw_agent`.
- [ ] Enumerate declared `odylith_on` affordances and expose them in the report
      contract together with fairness findings and observed-path sources.
- [ ] Fix live observed-path scoring so raw prompt-visible anchors are credited
      symmetrically without creating hidden truth.
- [ ] Harden preflight evidence logging and focused no-op proxy handling so any
      Odylith-only preflight basis is explicit, bounded, and inspectable.
- [ ] Keep packet-only diagnostic `benchmark.packet_fixture` usage explicit,
      whitelisted, and confined to declared packet/runtime-summary seams.
- [ ] Expand the implementation corpus to at least `60` implementation
      scenarios with at least `35` write-plus-validator scenarios and at least
      `12` correctness-critical scenarios.
- [ ] Refresh benchmark docs, graphs, component truth, Atlas, and release proof
      from the validated full-corpus report selected for `0.1.11`.
- [ ] Support release-safe full-corpus proof by merging shard history reports
      back into one canonical report when operational shard splits are used.

## Should-Ship
- [ ] Add cross-layer tests that packet, live runner, report summaries, docs,
      and graphs agree on the new contract and fairness fields.
- [ ] Surface `validator_status_basis` so focused no-op proxy passes are
      inspectable in both machine-readable reports and reviewer-facing docs.
- [ ] Add corpus-composition guards that fail when mechanism-heavy control
      families exceed the seriousness floor.
- [ ] Keep benchmark publication artifacts aligned to the strongest validated
      proof without stale-subset drift.

## Defer
- [ ] A narrower public grounding-only ablation lane.
- [ ] Claude-host publication proof.
- [ ] Hosted benchmark infrastructure or remote orchestration changes.

## Success Criteria
- [ ] The published benchmark contract no longer pretends the primary live pair
      isolates grounding-only differences.
- [ ] Fairness warnings are empty for the selected published report.
- [ ] The latest proof covers the full tracked corpus and meets the seriousness
      thresholds.
- [ ] Benchmark docs, graphs, Registry truth, Radar truth, Atlas, and bundle
      mirrors all agree on the same validated report.
- [ ] Full sync and standalone check-only both pass on the same tree.

## Non-Goals
- [ ] Adding a second public benchmark CLI profile for grounding-only proof.
- [ ] Optimizing benchmark results by hiding or removing legitimate Odylith
      affordances.
- [ ] Padding the corpus with more governance-only slices just to hit counts.

## Impacted Areas
- [ ] [2026-04-12-benchmark-full-product-contract-live-lane-fairness-and-real-world-corpus-hardening.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-12-benchmark-full-product-contract-live-lane-fairness-and-real-world-corpus-hardening.md)
- [ ] [2026-04-12-execution-governance-benchmark-family-and-honest-ablation-proof.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-12-execution-governance-benchmark-family-and-honest-ablation-proof.md)
- [ ] [2026-04-12-odylith-execution-governance-benchmark-family-and-honest-ablation-proof.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-12-odylith-execution-governance-benchmark-family-and-honest-ablation-proof.md)
- [ ] [optimization-evaluation-corpus.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/optimization-evaluation-corpus.v1.json)
- [ ] [odylith_benchmark_live_execution.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py)
- [ ] [odylith_benchmark_live_prompt.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py)
- [ ] [odylith_benchmark_runner.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/benchmark/CURRENT_SPEC.md)
- [ ] [FAMILIES_AND_EVALS.md](/Users/freedom/code/odylith/docs/benchmarks/FAMILIES_AND_EVALS.md)
- [ ] [METRICS_AND_PRIORITIES.md](/Users/freedom/code/odylith/docs/benchmarks/METRICS_AND_PRIORITIES.md)
- [ ] [README.md](/Users/freedom/code/odylith/README.md)
- [ ] [test_odylith_benchmark_live_execution.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_live_execution.py)
- [ ] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)
- [ ] [test_odylith_benchmark_corpus.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_corpus.py)

## Validation
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_live_execution.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_corpus.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_execution_governance.py tests/unit/runtime/test_execution_governance.py tests/unit/runtime/test_odylith_runtime_surface_summary.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
- [ ] `PYTHONPATH=src python3 -m odylith.cli benchmark --repo-root . --profile diagnostic`
- [ ] `PYTHONPATH=src python3 -m odylith.cli benchmark --repo-root . --profile proof`
- [ ] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --force --impact-mode full`
- [ ] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- [ ] `PYTHONPATH=src python3 -m odylith.cli validate backlog-contract --repo-root .`
- [ ] `PYTHONPATH=src python3 -m odylith.cli validate component-registry --repo-root .`
- [ ] `PYTHONPATH=src python3 -m odylith.cli atlas render --repo-root . --diagram-id D-024`
- [ ] `git diff --check`
