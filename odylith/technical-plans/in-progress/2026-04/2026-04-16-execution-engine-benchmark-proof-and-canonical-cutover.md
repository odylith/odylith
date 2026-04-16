Status: In progress
Created: 2026-04-16
Updated: 2026-04-16
Backlog: B-100

# Execution Engine Benchmark Proof and Canonical Cutover

## Goal
Prove the Context Engine to Execution Engine handshake before broadening the alignment program. The first shippable outcome is that `execution-engine` is the only accepted component id and benchmark family identity for this slice; stale identifiers fail closed before route readiness, and `execution_engine_*` is the active machine namespace.

## Assumptions
- Canonical component id remains `execution-engine`.
- No historical component alias is supported for new lookup, benchmark, or Registry behavior.
- Benchmark proof is Wave 1 for umbrella workstream `B-099`.
- Machine fields use the `execution_engine_*` namespace.
- New benchmark logic must not increase red-zone runner or context-store files; execution-specific aggregation stays in the execution benchmark metrics module.

## Constraints
- Do not preserve legacy metric or component aliases.
- Do not add business logic to the oversized benchmark runner or Context Engine store.
- Keep the Execution Engine contract host-general; Codex and Claude parity belongs to a later wave except where existing tests already cover it.
- Keep route readiness fail-closed when canonical component identity is missing or ambiguous.

## Reversibility
The cutover is intentionally strict. Reverting would require reintroducing an alias map and metric compatibility layer, which this slice explicitly removes.

## Boundary Conditions
- Require direct `execution-engine` component lookup before registry detail lookup, route readiness, and benchmark expectation evaluation.
- Require direct `execution_engine` benchmark family identity.
- Include focused tests proving stale component ids fail closed instead of resolving.
- Exclude full Wave 2-5 implementation beyond governance scaffolding and documented contract framing.

## Related Bugs
No related Casebook bug found. The current failing focused benchmark proof is captured directly in this plan as implementation evidence.

## Learnings
- [x] Stale component identifiers still reach benchmark packet construction and correctly degrade the governance-slice packet to `recover` with `unknown_component`.
- [x] Canonical `execution-engine` resolves to `verify` with `verify.selected_matrix` for the same benchmark scenario.

## Must-Ship
- [x] Remove component alias resolution from registry detail lookup and governance-slice route readiness.
- [x] Accept only the canonical `execution_engine` benchmark family token.
- [x] Add tests proving canonical `execution-engine` resolves and stale component ids fail closed.
- [x] Keep docs, specs, and report language centered on Execution Engine with no compatibility-key promise.
- [x] Create umbrella program `B-099` with Waves 1-5 and bind this plan as the Wave 1 gate.

## Should-Ship
- [x] Update benchmark docs to state that Execution Engine owns the active `execution_engine_*` metric namespace.
- [x] Refresh generated governance and bundled mirrors through the governed sync path.
- [x] Log the implementation posture to Compass after validation.

## Deferred
- Downstream historical report cleanup that is not part of the active runtime, Registry, or benchmark contract.
- Wave 2 stable packet-shape normalization across every runtime surface.
- Wave 3 paired Codex and Claude semantic parity expansion beyond existing host-profile tests.
- Wave 4 snapshot reuse and token/latency optimization.
- Wave 5 Atlas diagram refresh and release-proof closure.

## Success Criteria
- `execution-engine` resolves to the expected packet posture in the benchmark governance-slice path.
- Stale component ids fail closed before route readiness.
- Focused execution benchmark tests pass.
- Registry and backlog validators pass.
- The execution-wave program exists under `B-099` with Wave 1 active and later waves planned.
- `git diff --check` passes.

## Impacted Areas
- Context Engine registry detail projection runtime.
- Execution benchmark family metrics and prompt-family rules.
- Benchmark taxonomy and focused execution benchmark tests.
- Execution Engine and Context Engine specs.
- Benchmark docs.
- Radar workstreams and technical-plan binding for `B-099`/`B-100`.

## Validation Plan
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_execution_engine.py tests/unit/runtime/test_execution_engine.py`
- `PYTHONPATH=src python -m odylith.cli validate component-registry --repo-root .`
- `PYTHONPATH=src python -m odylith.cli validate backlog-contract --repo-root .`
- `PYTHONPATH=src python -m odylith.cli sync --repo-root . --impact-mode selective --check-only <changed paths>`
- `git diff --check`
