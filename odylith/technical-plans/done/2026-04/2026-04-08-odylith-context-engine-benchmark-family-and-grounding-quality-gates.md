Status: Done

Created: 2026-04-08

Updated: 2026-04-09

Backlog: B-068

Goal: Add a dedicated Context Engine benchmark family and quality gates before
the next Context Engine architecture wave lands.

Assumptions:
- The Context Engine is central enough now that broad benchmark aggregates are
  no longer sufficient to catch its regressions early.
- The benchmark runner already has the right additive extension points for a
  family-specific metric module.
- The right first slice measures current shipped behavior rather than
  redesigning the Context Engine to satisfy a speculative benchmark.

Constraints:
- Keep the first landing additive to the benchmark contract.
- Do not soften existing families to make the new Context Engine family easier.
- Keep the corpus and bundle mirrors byte-aligned.

Reversibility: The family and its metrics can be removed cleanly if they prove
redundant, but this plan assumes the Context Engine now deserves first-class
benchmark coverage.

Boundary Conditions:
- Scope includes benchmark-family scenarios, family metrics, acceptance checks,
  packet-summary fields needed to score those scenarios, and aligned benchmark
  docs or component truth.
- Scope excludes deeper collaboration-memory architecture work and broader
  Context Engine feature changes beyond any direct bug fixes the new family
  exposes immediately.

Related Bugs:
- CB-087

## Learnings
- [x] The Context Engine split hardening wave needs a benchmark family of its
      own, not just broader regression suites.
- [x] Adaptive packet selection and fail-closed ambiguity are product
      behaviors that should be measured explicitly.

## Must-Ship
- [x] Add the `context_engine_grounding` family to the tracked benchmark
      corpus with representative packet scenarios.
- [x] Add family metrics for packet-source accuracy, selection-state
      accuracy, workstream accuracy, ambiguity fail-closed behavior, and
      runtime-backed session namespacing.
- [x] Extend packet summaries and expectation matching only as needed to score
      those metrics honestly.
- [x] Wire the new metrics into runner summaries, comparisons, and acceptance.
- [x] Update benchmark docs and benchmark component truth to describe the new
      family and its metrics.

## Should-Ship
- [x] Add a Context Engine architecture dossier scenario to the benchmark
      corpus through the architecture benchmark surface so Context Engine
      dossier grounding is measured without duplicating the same contract in
      two families.
- [x] Keep a current-repo probe test for the adaptive split and fail-closed
      broad-scope cases so the family is grounded in real repo truth.

## Defer
- [ ] Collaboration-memory benchmark scenarios that require a later runtime
      feature wave.
- [ ] New Context Engine CLI or packet contracts unrelated to the benchmark
      family.

## Success Criteria
- [x] Benchmark runs publish a first-class Context Engine family summary.
- [x] Context Engine grounding regressions can fail or weaken the family on
      their own merits.
- [x] Focused and broad regression suites stay green with the new family in
      place.

## Non-Goals
- [ ] Reworking the benchmark taxonomy beyond adding the new family.
- [ ] Live benchmark infrastructure changes.
- [ ] General Context Engine architecture improvements beyond direct bug fixes
      exposed by the new evals.

## Open Questions
- [x] Whether future collaboration-memory work should extend this family or
      spawn a second Context Engine runtime-memory family remains deferred to
      a later runtime-memory slice rather than blocking this grounding family.

## Impacted Areas
- [x] [2026-04-08-odylith-context-engine-benchmark-family-and-grounding-quality-gates.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-08-odylith-context-engine-benchmark-family-and-grounding-quality-gates.md)
- [x] [2026-04-08-odylith-context-engine-benchmark-family-and-grounding-quality-gates.md](/Users/freedom/code/odylith/odylith/technical-plans/done/2026-04/2026-04-08-odylith-context-engine-benchmark-family-and-grounding-quality-gates.md)
- [x] [optimization-evaluation-corpus.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/optimization-evaluation-corpus.v1.json)
- [x] [odylith_benchmark_runner.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)
- [x] [odylith_benchmark_context_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_context_engine.py)
- [x] [odylith_context_engine_packet_summary_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_packet_summary_runtime.py)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/benchmark/CURRENT_SPEC.md)
- [x] [FAMILIES_AND_EVALS.md](/Users/freedom/code/odylith/docs/benchmarks/FAMILIES_AND_EVALS.md)
- [x] [METRICS_AND_PRIORITIES.md](/Users/freedom/code/odylith/docs/benchmarks/METRICS_AND_PRIORITIES.md)
- [x] [BENCHMARK_TABLES.md](/Users/freedom/code/odylith/docs/benchmarks/BENCHMARK_TABLES.md)
- [x] [test_odylith_benchmark_context_engine.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_context_engine.py)
- [x] [test_odylith_benchmark_corpus.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_corpus.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_context_engine.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_context_engine_split_hardening.py tests/unit/runtime/test_context_engine_release_resolution.py tests/unit/runtime/test_context_engine_topology_contract.py tests/unit/runtime/test_context_engine_proof_packet_runtime.py tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_plan_progress.py tests/unit/runtime/test_workstream_progress.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_render_compass_dashboard.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_deep.py::test_compass_reconciles_release_targets_from_live_traceability_when_runtime_snapshot_is_stale tests/integration/runtime/test_surface_browser_deep.py::test_compass_release_targets_show_checklist_label_instead_of_fake_zero_progress`
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- [x] `git diff --check`

## Current Outcome
- [x] `B-068` is closed for `v0.1.11`.
- [x] The benchmark corpus now has a first-class `context_engine_grounding`
      family with packet-lane, selection-state, workstream, ambiguity, and
      session-namespace quality gates.
- [x] Context Engine architecture dossier coverage is now explicit in the
      benchmark corpus through the architecture scenario lane, keeping the
      architecture contract measured without duplicating the same scenario in
      the grounding family.
- [x] Context Engine grounding regressions can now fail benchmark acceptance
      directly, and the surrounding release-target progress surfaces report
      the workstream against real execution progress instead of checklist-only
      zeroes.
