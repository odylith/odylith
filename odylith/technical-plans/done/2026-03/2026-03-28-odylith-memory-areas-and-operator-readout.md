Status: Done

Created: 2026-03-28

Updated: 2026-03-28

Backlog: B-008

Goal: Make Odylith expose its real memory areas and gaps through the runtime
memory snapshot, context-engine status output, and operator
readouts.

Assumptions:
- Odylith remains local-first and repo-truth-first.
- This slice explains current memory posture; it does not implement the larger
  future collaboration-memory architecture.
- Existing memory snapshot consumers tolerate additive fields.

Constraints:
- Keep the contract honest about what is still missing.
- Do not change backend providers or require remote retrieval.
- Keep the new readout concise enough to help first-run operators.

Reversibility: Reverting this slice removes the new `memory_areas` contract,
the status output lines, and the shell drawer readout without affecting stored
repo truth or runtime backends.

Boundary Conditions:
- Scope includes `memory_snapshot.v1`, runtime status output,
  diagnostic readouts, and Context Engine source-spec updates.
- Scope excludes durable decision memory, workspace/actor identity memory,
  contradiction persistence, and hosted augmentation.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] Odylith already had real local memory posture, but operators still had to infer it from backend details.
- [x] First-run and shell UX needed a plain explanation of what memory exists now versus what is still planned.
- [x] The product needed one honest memory-area contract before deeper memory architecture work expands.

## Success Criteria
- [x] `memory_snapshot.v1` includes named memory areas with state, summary, counts, and gaps.
- [x] `odylith context-engine status` prints memory-area counts and headline.
- [x] Runtime and diagnostic readouts expose a dedicated memory-area section
      without requiring dashboard shell status UI.
- [x] Tests cover snapshot, status, and shell rendering for the new contract.

## Non-Goals
- [x] Implementing durable decision memory.
- [x] Implementing workspace, actor, or shared-ownership memory.
- [x] Persisting contradiction memory as a first-class runtime contract.
- [x] Changing LanceDB, Tantivy, or optional remote retrieval provider behavior.

## Impacted Areas
- [x] [src/odylith/runtime/context_engine/odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [src/odylith/runtime/context_engine/odylith_context_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine.py)
- [x] [src/odylith/runtime/context_engine/odylith_runtime_surface_summary.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_runtime_surface_summary.py)
- [x] [src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py)
- [x] [src/odylith/install/__init__.py](/Users/freedom/code/odylith/src/odylith/install/__init__.py)
- [x] [odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [x] [src/odylith/bundle/assets/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [x] [odylith/radar/source/INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [odylith/technical-plans/INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)
- [x] [tests/unit/runtime/test_odylith_runtime_surface_summary.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_runtime_surface_summary.py)
- [x] [tests/unit/runtime/test_odylith_memory_areas.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_memory_areas.py)
- [x] [tests/unit/runtime/test_render_tooling_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_tooling_dashboard.py)

## Traceability
### Specs
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)

### Runtime And Shell
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [odylith_context_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine.py)
- [x] [odylith_runtime_surface_summary.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_runtime_surface_summary.py)
- [x] [tooling_dashboard_shell_presenter.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py)
- [x] [__init__.py](/Users/freedom/code/odylith/src/odylith/install/__init__.py)

### Tests
- [x] [test_odylith_runtime_surface_summary.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_runtime_surface_summary.py)
- [x] [test_odylith_memory_areas.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_memory_areas.py)
- [x] [test_render_tooling_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_tooling_dashboard.py)

## Risks & Mitigations

- [x] Risk: The readout could overclaim memory areas that are still only aspirational.
  - [x] Mitigation: mark future decision, collaboration, and contradiction memory explicitly as `planned`.
- [x] Risk: The shell could repeat low-level backend detail instead of clarifying memory posture.
  - [x] Mitigation: summarize live areas and gaps in plain operator-facing language.
- [x] Risk: Runtime-memory tests could stay fragile because the install package eagerly imports the whole install stack into a circular path.
  - [x] Mitigation: lazy-load `odylith.install` exports so runtime-memory modules can import cleanly during verification.

## Validation/Test Plan
- [x] `pytest -q tests/unit/runtime/test_odylith_runtime_surface_summary.py tests/unit/runtime/test_odylith_memory_areas.py tests/unit/runtime/test_render_tooling_dashboard.py`

## Rollout/Communication
- [x] Ship the readout as an additive contract on top of existing runtime diagnostics.
- [x] Keep deeper collaboration-memory work deferred to later governed slices.

## Dependencies/Preconditions
- [x] Existing Context Engine memory snapshot contracts already exist.
- [x] No bug remediation or release workflow change is required for this slice.

## Edge Cases
- [x] If Odylith is disabled, memory areas render as suppressed instead of pretending to be live.
- [x] If the repo has no active sessions or evaluation samples yet, session and outcome memory render as cold instead of missing silently.

## Open Questions/Decisions
- [x] Decision: expose future memory areas honestly as `planned` instead of hiding them.
- [x] Decision: keep the new readout additive so older memory snapshot consumers keep working.

## Current Outcome
- Odylith now exposes named memory areas, not just backend implementation detail.
- Runtime status tells operators what memory is strong, cold, or still planned.
- Memory posture remains available through runtime/diagnostic readouts; dashboard
  product surfaces must not render it as shell status chrome.
- The install package no longer forces the whole install stack to import eagerly during runtime-memory test collection.
