Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-020

Goal: Make Odylith's published benchmark proof more conservative, robust, and
harder to overstate by default, promote Benchmark into first-class Registry and
Atlas source truth, then refresh the README and maintained graphs from that
stronger benchmark contract.

Assumptions:
- The current benchmark runner can already execute multiple cache profiles, so
  the strongest short-term integrity gain is to publish a conservative
  multi-profile view instead of adding a totally new eval system first.
- The README and graph assets should reflect the strongest honest local Codex
  proof lane, even if the resulting numbers are less flattering than a warm-only
  snapshot.
- Benchmark should be promoted into explicit Registry and Atlas source truth so
  future benchmark work is governed like the rest of the product.

Constraints:
- Do not weaken correctness, recall, or validation requirements to make the new
  conservative benchmark pass.
- Keep the benchmark graph filenames and README graph order unchanged.
- Preserve backward-compatible report fields where practical so existing local
  consumers of the report do not break.
- Keep bundle mirrors aligned with the product-owned benchmark component and
  Atlas catalog truth.

Reversibility: Reverting this slice restores the prior warm-primary benchmark
publication contract, removes the first-class benchmark component and diagram,
and restores the previous README benchmark snapshot.

Boundary Conditions:
- Scope includes benchmark runner defaults, published-summary logic, benchmark
  component/Atlas source truth, graph rendering inputs, README benchmark
  wording, and focused regression tests.
- Scope excludes major corpus redesign, hosted evaluation infrastructure, and
  Claude-native benchmark lanes.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] The published report was still centered on a single primary cache
  profile.
- [x] README wording did not make the benchmark methodology conservative enough
  or explicit enough.
- [x] The benchmark graphs rendered from the easier profile-specific view
  rather than a stronger published summary.
- [x] Benchmark was still implicit repo truth instead of a first-class Registry
  component and Atlas diagram.

## Success Criteria
- [x] `odylith benchmark` defaults to a stronger warm-plus-cold proof lane.
- [x] The report exposes a conservative published comparison and summary that is
  derived across the selected cache profiles.
- [x] Benchmark is tracked as a first-class Registry component with a current
  spec and forensic sidecar.
- [x] Atlas carries a benchmark proof-and-publication diagram linked to B-020.
- [x] README numbers and graph assets are regenerated from the conservative
  published view.
- [x] Focused runner/graph/CLI and Registry or Atlas validation pass.
- [x] `git diff --check` passes after source truth is updated.

## Non-Goals
- [ ] Benchmark corpus redesign.
- [ ] Hosted evaluation orchestration.
- [ ] Any claim that Claude Code shares the same native subagent benchmark lane.

## Impacted Areas
- [x] [odylith_benchmark_runner.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)
- [x] [odylith_benchmark_graphs.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_graphs.py)
- [x] [README.md](/Users/freedom/code/odylith/README.md)
- [x] [component_registry.v1.json](/Users/freedom/code/odylith/odylith/registry/source/component_registry.v1.json)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/benchmark/CURRENT_SPEC.md)
- [x] [FORENSICS.v1.json](/Users/freedom/code/odylith/odylith/registry/source/components/benchmark/FORENSICS.v1.json)
- [x] [diagrams.v1.json](/Users/freedom/code/odylith/odylith/atlas/source/catalog/diagrams.v1.json)
- [x] [odylith-benchmark-proof-and-publication-lane.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd)
- [x] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)
- [x] [test_odylith_benchmark_graphs.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_graphs.py)
- [x] [test_validate_component_registry_contract.py](/Users/freedom/code/odylith/tests/unit/runtime/test_validate_component_registry_contract.py)
- [x] [test_render_mermaid_catalog.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_mermaid_catalog.py)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)

## Risks & Mitigations

- [x] Risk: the stronger publication contract makes the public benchmark look
  - [ ] Mitigation: TODO (add explicit mitigation).
  worse.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: treat that as a product-truth correction, not a regression,
    and explain the methodology clearly in README.
- [x] Risk: a multi-profile default makes local benchmark runs slower.
  - [x] Mitigation: keep the corpus fixed and the aggregation logic compact; if
    needed, preserve `--cache-profile warm` as the explicit faster local-only
    override.
- [x] Risk: new report fields drift from the graph and README readers.
  - [x] Mitigation: add focused regression tests for conservative published
    summary selection and graph rendering.
- [x] Risk: benchmark remains powerful but still under-governed in source truth.
  - [x] Mitigation: promote Benchmark into Registry and Atlas so future slices
    update the same governed component and diagram instead of loose docs.

## Validation/Test Plan
- [x] `odylith benchmark --repo-root .`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_graphs.py tests/unit/test_cli.py`
- [x] `PYTHONPATH=src .venv/bin/python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks`
- [x] `odylith validate component-registry --repo-root .`
- [x] `odylith atlas render --repo-root . --check-only`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_validate_component_registry_contract.py tests/unit/runtime/test_render_mermaid_catalog.py`
- [x] `git diff --check`

## Rollout/Communication
- [x] README explains that the published Codex snapshot is now conservative
  across warm and cold cache profiles by default.
- [x] Maintainer-facing release guidance is updated if the publication contract
  changes materially.
- [x] Registry and Atlas now expose benchmark as governed source truth instead
  of leaving the benchmark lane implicit.

## Current Outcome
- [x] Bound to `B-020`; implementation completed.
- [x] Benchmark publication is now conservative across warm and cold cache
  profiles and drives README or graph proof from the harder published view.
- [x] Benchmark is now captured as a first-class Registry component and Atlas
  diagram, with backlog, plan, and bundle mirrors reconciled.
