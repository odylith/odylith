Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-013

Goal: Reduce duplicated runtime-contract logic across Odylith surfaces and
orchestration without changing product behavior or regressing the benchmark.

Assumptions:
- The product behavior is already correct; the main issue is duplicated
  correctness-sensitive code.
- Shared helpers are safer than parallel local variants when their contracts
  are covered directly by tests.
- Browser-level smoke plus benchmark proof is sufficient to catch accidental
  renderer or runtime regressions for this slice.

Constraints:
- Do not change the public CLI or surface contract.
- Do not regress prompt-token, recall, validation, or browser behavior.
- Keep the refactor bounded to obvious duplicated seams.

Reversibility: Reverting this slice restores the previous duplicated helpers
without needing data or contract migration.

Boundary Conditions:
- Scope includes execution-profile helper reuse, surface bundle spec reuse,
  focused tests, and governance closeout.
- Scope excludes broader architectural reshaping or product-surface redesign.

Related Bugs:
- none; this was a proactive maintainability and regression-risk reduction
  slice rather than a user-reported defect

## Context/Problem Statement
- [x] Execution-profile parsing and compact encoding existed in multiple
  runtime readers and writers.
- [x] Surface bundle bootstrap specs were repeated across multiple renderers.
- [x] The duplicated seams were correctness-sensitive and easy to drift.
- [x] Odylith needed a bounded reuse pass that improved maintainability
  without changing behavior.

## Success Criteria
- [x] One shared execution-profile helper boundary exists for runtime readers.
- [x] One shared surface bundle spec helper exists for renderers.
- [x] The affected runtime and surface callsites now use the shared helpers.
- [x] Focused helper tests exist.
- [x] Headless browser smoke stays green.
- [x] Benchmark proof remains green with no regression in recall or validation.

## Non-Goals
- [x] User-facing behavior changes.
- [x] Surface redesign or payload-schema redesign.
- [x] Refactoring every small utility seam in the repo.

## Impacted Areas
- [x] [tooling_memory_contracts.py](/Users/freedom/code/odylith/src/odylith/runtime/memory/tooling_memory_contracts.py)
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [subagent_router.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_router.py)
- [x] [subagent_orchestrator.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_orchestrator.py)
- [x] [dashboard_surface_bundle.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/dashboard_surface_bundle.py)
- [x] [render_tooling_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_tooling_dashboard.py)
- [x] [render_backlog_ui.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui.py)
- [x] [render_registry_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_registry_dashboard.py)
- [x] [render_casebook_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_casebook_dashboard.py)
- [x] [render_mermaid_catalog.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_mermaid_catalog.py)
- [x] [render_compass_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_compass_dashboard.py)
- [x] [test_dashboard_surface_bundle.py](/Users/freedom/code/odylith/tests/unit/runtime/test_dashboard_surface_bundle.py)
- [x] [test_tooling_memory_contracts.py](/Users/freedom/code/odylith/tests/unit/runtime/test_tooling_memory_contracts.py)

## Traceability
### Shared Runtime Contracts
- [x] [tooling_memory_contracts.py](/Users/freedom/code/odylith/src/odylith/runtime/memory/tooling_memory_contracts.py)
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [subagent_router.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_router.py)
- [x] [subagent_orchestrator.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_orchestrator.py)

### Shared Surface Contracts
- [x] [dashboard_surface_bundle.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/dashboard_surface_bundle.py)
- [x] [render_tooling_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_tooling_dashboard.py)
- [x] [render_backlog_ui.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui.py)
- [x] [render_registry_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_registry_dashboard.py)
- [x] [render_casebook_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_casebook_dashboard.py)
- [x] [render_mermaid_catalog.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_mermaid_catalog.py)
- [x] [render_compass_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_compass_dashboard.py)

### Tests And Proof
- [x] [test_dashboard_surface_bundle.py](/Users/freedom/code/odylith/tests/unit/runtime/test_dashboard_surface_bundle.py)
- [x] [test_tooling_memory_contracts.py](/Users/freedom/code/odylith/tests/unit/runtime/test_tooling_memory_contracts.py)
- [x] [test_surface_browser_smoke.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_smoke.py)
- [x] [latest.v1.json](/Users/freedom/code/odylith/.odylith/runtime/odylith-benchmarks/latest.v1.json)

## Risks & Mitigations

- [x] Risk: one renderer loses a small bootstrap option during helper
  - [ ] Mitigation: TODO (add explicit mitigation).
  centralization.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: keep helper inputs explicit and cover both shell and
    non-shell bundle variants in unit tests.
- [x] Risk: execution-profile normalization changes route behavior.
  - [x] Mitigation: centralize the existing field set only and validate through
    subagent-surface and benchmark proof.

## Validation/Test Plan
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_dashboard_surface_bundle.py tests/unit/runtime/test_tooling_memory_contracts.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_subagent_surface_validation.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/integration/runtime/test_surface_browser_smoke.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py`
- [x] `odylith benchmark --repo-root .`
- [x] `git diff --check`

## Rollout/Communication
- [x] Ship as an internal refactor with no user-facing migration.
- [x] Record the slice in Odylith backlog and done-plan truth.
- [x] Keep bundle index mirrors aligned with the public product tree.

## Dependencies/Preconditions
- [x] Existing renderers already shared a common bundle-contract shape.
- [x] Existing route readers already shared a common execution-profile field
  set.

## Edge Cases
- [x] Shell-embedded surfaces still preserve their tab/frame wiring.
- [x] Standalone bundle specs still work without shell-embed metadata.
- [x] Compact execution-profile tokens still decode correctly when fields are
  omitted or trailing values are empty.

## Open Questions/Decisions
- [x] Decision: centralize only the already-proven shared contract, not larger
  runtime abstractions, to keep regression risk low.
- [x] Decision: prove the refactor with browser smoke and benchmark validation,
  not just unit coverage, because the affected paths cross runtime, shell, and
  orchestration boundaries.

## Current Outcome
- Shared execution-profile parsing, compaction, and token encoding now live in
  one runtime-contract module and are reused by the Context Engine, Router, and
  Orchestrator.
- Shared surface bundle bootstrap and shell-embed wiring now live in one
  helper and are reused across Dashboard, Radar, Registry, Casebook, Atlas,
  and Compass renderers.
- Odylith kept the benchmark green and the browser smoke suite passing while
  materially reducing duplicated correctness-sensitive code.
