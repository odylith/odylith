Status: In progress

Created: 2026-04-12

Updated: 2026-04-12

Backlog: B-092

Goal: Add a first-class execution-governance benchmark family that proves
whether Odylith's execution engine improves truthful next-move quality,
closure discipline, resumability, and host-aware focus under the benchmark's
honest `full_product_assistance_vs_raw_agent` contract without regressing
governed sync or benchmark integrity.

Assumptions:
- The benchmark harness already has the right additive extension points for a
  family-specific metric module.
- The current packet benchmark contract already carries enough execution-
  governance fields to seed an honest first family, with only small contract
  extensions needed for missing scalar fields.
- The benchmark's honest primary comparison remains `odylith_on` versus
  `odylith_off`, but that pair now explicitly means full-product assistance
  versus raw agent rather than grounding-only scaffold.
- `B-093` will carry the broader contract, fairness, and corpus-hardening
  work; this plan must stay aligned to that contract instead of closing under
  the older grounding-only story.
- `B-091` sync invariants are non-negotiable. Any benchmark-family addition
  that reopens shared-nothing sync behavior or noisy no-op writes is a failed
  implementation.

Constraints:
- Keep the first landing additive to the benchmark contract.
- Do not soften generic benchmark families or validators to flatter the new
  execution-governance family.
- Preserve current governed-sync reuse, content-addressed writes, and
  fail-closed standalone check-only behavior.
- Keep benchmark source and bundle mirrors byte-aligned.

Reversibility: The family, its metrics, and its docs can be removed cleanly if
they prove redundant, but this plan assumes execution governance now deserves a
first-class benchmark slice.

Boundary Conditions:
- Scope includes benchmark-family scenarios, family metrics, acceptance checks,
  packet expectation fields needed to score those metrics honestly, and aligned
  benchmark docs or component truth.
- Scope excludes live benchmark publication redesign, hosted evaluation
  infrastructure, and execution-engine feature work unrelated to making the
  existing engine benchmarkable.

Related Bugs:
- [CB-106](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-12-benchmark-live-preflight-evidence-is-only-injected-for-odylith-on-without-a-declared-comparison-contract.md)
- [CB-107](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-12-benchmark-live-observed-path-scoring-credits-odylith-prompt-surfaces-but-not-equivalent-raw-prompt-anchors.md)

## Learnings
- [ ] Benchmark value claims for execution governance are still anecdotal until
      the harness can isolate those signals directly.
- [ ] The right first family should measure the current shipped execution
      contract, not a speculative future engine.

## Must-Ship
- [ ] Add the `execution_governance` family to the tracked benchmark corpus
      with representative current-repo packet scenarios.
- [ ] Add family metrics for admissibility outcome, execution mode, truthful
      next move, closure posture, validation archetype, re-anchor accuracy,
      host carry-through, resume-token presence, and benchmark-facing contract
      labeling aligned to `B-093`.
- [ ] Extend packet expectation matching only where current scalar execution-
      governance fields are not yet benchmarkable.
- [ ] Wire the family metrics into runner summaries, comparisons, and hard
      acceptance checks.
- [ ] Update benchmark docs, taxonomy, and benchmark component truth to
      describe the family, its benchmark role, and its place inside the
      full-product benchmark contract.

## Should-Ship
- [ ] Add current-repo packet probe tests that assert the new family is backed
      by real execution-governance packet truth.
- [ ] Add family-aware support-doc ranking and hot-path shaping so the new
      family stays bounded in live benchmark runs.

## Defer
- [ ] Deeper live wait-state benchmark scenarios that require more stable
      product wait adapters.
- [ ] External-provider-specific execution-governance benchmark families.

## Success Criteria
- [ ] Benchmark reports publish a first-class execution-governance family
      summary under the honest full-product comparison contract.
- [ ] Execution-governance regressions can fail benchmark acceptance directly.
- [ ] Focused, broader benchmark, and governed-sync proof stay green with the
      new family in place.

## Non-Goals
- [ ] Reworking the benchmark publication contract beyond adding the new family.
- [ ] Creating a benchmark-only execution-governance contract that diverges
      from the shipped runtime.
- [ ] Weakening the raw baseline or repo-scan lane to make the new family read
      better.

## Impacted Areas
- [ ] [2026-04-12-execution-governance-benchmark-family-and-honest-ablation-proof.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-12-execution-governance-benchmark-family-and-honest-ablation-proof.md)
- [ ] [2026-04-12-odylith-execution-governance-benchmark-family-and-honest-ablation-proof.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-12-odylith-execution-governance-benchmark-family-and-honest-ablation-proof.md)
- [ ] [optimization-evaluation-corpus.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/optimization-evaluation-corpus.v1.json)
- [ ] [odylith_benchmark_runner.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)
- [ ] [odylith_benchmark_execution_governance.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_execution_governance.py)
- [ ] [odylith_benchmark_prompt_family_rules.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_prompt_family_rules.py)
- [ ] [odylith_benchmark_taxonomy.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_taxonomy.py)
- [ ] [odylith_context_engine_runtime_learning_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_runtime_learning_runtime.py)
- [ ] [odylith_context_engine_hot_path_delivery_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_hot_path_delivery_runtime.py)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/benchmark/CURRENT_SPEC.md)
- [ ] [FAMILIES_AND_EVALS.md](/Users/freedom/code/odylith/docs/benchmarks/FAMILIES_AND_EVALS.md)
- [ ] [METRICS_AND_PRIORITIES.md](/Users/freedom/code/odylith/docs/benchmarks/METRICS_AND_PRIORITIES.md)
- [ ] [test_odylith_benchmark_execution_governance.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_execution_governance.py)
- [ ] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)
- [ ] [test_odylith_benchmark_corpus.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_corpus.py)

## Validation
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_execution_governance.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_corpus.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_governance.py tests/unit/runtime/test_odylith_runtime_surface_summary.py tests/unit/runtime/test_subagent_reasoning_ladder.py`
- [ ] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- [ ] `PYTHONPATH=src python3 -m odylith.cli validate backlog-contract --repo-root .`
- [ ] `PYTHONPATH=src python3 -m odylith.cli validate component-registry --repo-root .`
- [ ] `git diff --check`
