Status: Done

Created: 2026-03-28

Updated: 2026-03-29

Backlog: B-010

Goal: Give Odylith durable judgment memory that remembers the governed shape of
the repo through compact local memory, not raw chat, while preserving or
improving the benchmark proof against the Codex/full-scan baseline.

Assumptions:
- Repo truth remains authoritative over any local memory artifact.
- The new memory model should surface higher-signal judgment without leaking
  verbose telemetry into the hot-path prompt payload.
- The local memory backend is mature enough to be promoted into a first-class
  Registry component.

Constraints:
- Do not retain raw thread transcripts as the source of truth.
- Do not make hosted memory authoritative or required.
- Keep the benchmark priorities explicit: recall/accuracy/speed first, prompt
  tokens second, total token budgets third.

Reversibility: Reverting this slice removes the durable judgment-memory
contract, the new persisted runtime artifact, the shell/CLI readouts, and the
memory-backend component boundary without touching tracked repo truth.

Boundary Conditions:
- Scope includes judgment memory, workspace/actor memory posture,
  contradiction/negative/outcome/onboarding/provenance memory, shell/CLI
  exposure, memory-backend componentization, and benchmark revalidation.
- Scope excludes raw chat storage, hosted collaboration rollout, and unrelated
  release/install fixes already in flight on this branch.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] Odylith already exposes retrieval, guidance, session, and outcome
  posture, but durable judgment memory is still missing.
- [x] Decision, contradiction, workspace/actor, and onboarding memory should
  survive across sessions as compact runtime truth.
- [x] The product needs a first-class memory-backend boundary instead of
  burying that subsystem inside the Context Engine spec.
- [x] The new memory model must preserve or improve the benchmark proof against
  the Codex/full-scan baseline.

## Success Criteria
- [x] `memory_snapshot.v1` includes a first-class `judgment_memory` contract.
- [x] Odylith persists compact judgment memory under
  `.odylith/runtime/odylith-memory/odylith-judgment-memory.v1.json`.
- [x] Decision, workspace/actor, contradiction, freshness, negative, outcome,
  onboarding, and provenance memory each surface as explicit durable areas.
- [x] CLI/runtime shell readouts expose the new memory model clearly and
  compactly.
- [x] `odylith-memory-backend` is a first-class Registry component with synced
  source and bundle specs.
- [x] A fresh benchmark run remains at least `provisional_pass` and does not
  regress Odylith on the ordered baseline priorities.

## Non-Goals
- [x] Storing raw chat history as durable memory.
- [x] Making remote or hosted memory authoritative.
- [x] Expanding the hot-path prompt contract with verbose shell-oriented memory
  data.

## Impacted Areas
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [odylith_context_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine.py)
- [x] [odylith_runtime_surface_summary.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_runtime_surface_summary.py)
- [x] [tooling_dashboard_shell_presenter.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py)
- [x] [odylith_benchmark_runner.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)
- [x] [component_registry.v1.json](/Users/freedom/code/odylith/odylith/registry/source/component_registry.v1.json)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md)
- [x] [test_odylith_memory_areas.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_memory_areas.py)
- [x] [test_odylith_runtime_surface_summary.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_runtime_surface_summary.py)
- [x] [test_render_tooling_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_tooling_dashboard.py)
- [x] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)

## Traceability
### Runtime Contracts
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [odylith_context_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine.py)
- [x] [odylith_runtime_surface_summary.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_runtime_surface_summary.py)
- [x] [tooling_dashboard_shell_presenter.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py)

### Registry Truth
- [x] [component_registry.v1.json](/Users/freedom/code/odylith/odylith/registry/source/component_registry.v1.json)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md)

### Benchmark Proof
- [x] [odylith_benchmark_runner.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)
- [x] [latest.v1.json](/Users/freedom/code/odylith/.odylith/runtime/odylith-benchmarks/latest.v1.json)

### Tests
- [x] [test_odylith_memory_areas.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_memory_areas.py)
- [x] [test_odylith_runtime_surface_summary.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_runtime_surface_summary.py)
- [x] [test_render_tooling_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_tooling_dashboard.py)
- [x] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)

## Risks & Mitigations

- [x] Risk: durable memory becomes verbose and noisy instead of judgment-dense.
  - [x] Mitigation: persist only compact summaries, contradictions, and proof outcomes with explicit provenance.
- [x] Risk: workspace and actor memory becomes unstable across local environments.
  - [x] Mitigation: derive actor identity conservatively from local git/runtime evidence and label provenance clearly.
- [x] Risk: the new contract regresses benchmark token or latency posture.
  - [x] Mitigation: keep judgment memory off the hot path, honor explicit workstream hints earlier, and rerun the benchmark before closeout.

## Validation/Test Plan
- [x] `pytest -q tests/unit/runtime/test_odylith_memory_areas.py tests/unit/runtime/test_odylith_runtime_surface_summary.py tests/unit/runtime/test_render_tooling_dashboard.py`
- [x] `pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py`
- [x] `pytest -q tests/unit/test_cli.py`
- [x] `odylith benchmark --repo-root .`

## Rollout/Communication
- [x] Ship durable judgment memory as an additive runtime contract.
- [x] Call out whether the benchmark remained flat or improved after the new memory model landed.

## Dependencies/Preconditions
- [x] The current Context Engine runtime snapshot and shell drawer contracts remain available.
- [x] The benchmark harness still reflects the current product baseline and can be rerun locally.

## Edge Cases
- [x] If Odylith is disabled, judgment memory must render as suppressed instead of pretending to be live.
- [x] If the repo has no benchmark report, no active sessions, or no onboarding activity yet, those areas must fall back to honest cold or partial posture.
- [x] If local git identity is missing, actor memory must degrade gracefully instead of inventing certainty.

## Open Questions/Decisions
- [x] Decision: mark workspace and actor memory as durable but still provenance-limited until the larger B-002 collaboration contract lands.

## Current Outcome
- Durable `judgment_memory.v1` is now persisted locally and exposed through the
  Context Engine runtime summary, CLI status output, and shell drawer.
- Decision, workspace/actor, contradiction, freshness, negative, outcome,
  onboarding, and provenance memory areas are all rendered as first-class
  memory posture instead of implicit backend behavior.
- `odylith-memory-backend` is now a first-class Registry component with synced
  source and bundle specs.
- Hot-path packet construction now reuses durable judgment memory, reuses
  compact workstream selection, and honors explicit workstream hints earlier
  instead of paying to rediscover the same slice.
- The refreshed benchmark now clears as `provisional_pass` with better recall,
  better validation success, lower median prompt tokens, and lower median
  latency than the full-scan baseline (`median_latency_delta_ms = -13.780`,
  `median_prompt_token_delta = -15.000`,
  `required_path_recall_delta = +0.964`,
  `validation_success_delta = +0.714`).
