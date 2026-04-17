Status: In progress
Created: 2026-04-16
Updated: 2026-04-16
Backlog: B-101

# Context Execution Handshake Snapshot Normalization

## Goal
Make Context Engine packets and Execution Engine snapshots meet through one stable handshake shape. Context Engine owns canonical evidence, target, presentation, validation, and route-readiness context; Execution Engine consumes that shape once and emits one compact snapshot reused by packet summaries and downstream runtime surfaces.

## Assumptions
- `execution-engine` is the only canonical component id.
- No historical execution identifier is translated or preserved as an alias.
- Existing summary consumers should read `execution_engine_*` fields from the shared compact snapshot instead of deriving policy locally.
- New handshake code must live outside the red-zone Context Engine store and benchmark runner.

## Constraints
- Do not grow `odylith_context_engine_store.py` or the benchmark runner with execution policy business logic.
- Keep the packet handshake additive, compact, and serializable.
- Fail closed when canonical identity is missing or noncanonical.
- Preserve route readiness truth from the Context Engine instead of recomputing it in presentation layers.

## Reversibility
The helper can be removed by returning packet builders to direct snapshot construction, but doing so would reintroduce repeated local derivation and should require a new proof plan.

## Related Bugs
No related Casebook bug found.

## Must-Ship
- [x] Add a focused `execution_engine_handshake` helper for canonical packet identity, packet kind, packet quality, turn context, target resolution, presentation policy, recommended validation, and route readiness.
- [x] Attach the handshake to bootstrap and finalized hot-path packets.
- [x] Build the compact Execution Engine snapshot through the helper instead of direct per-surface construction.
- [x] Reuse an already built compact snapshot when packet summaries see one.
- [x] Add tests proving canonical identity, noncanonical fail-closed identity, shared snapshot reuse, and cost metadata.

## Should-Ship
- [x] Keep the helper independent of benchmark-runner business logic.
- [x] Expose stable summary fields for snapshot reuse status and handshake version.
- [x] Cover packet-summary consumption through the focused execution test suite.

## Deferred
- Any compatibility alias lane.
- A future schema version beyond handshake `v1`.

## Success Criteria
- Context packets carry one stable `execution_engine_handshake` object.
- Execution snapshots are built once per packet path or explicitly reused from an existing packet summary.
- Local summary consumers read from the shared compact snapshot.
- Focused execution tests pass.

## Impacted Areas
- `src/odylith/runtime/context_engine/execution_engine_handshake.py`
- `src/odylith/runtime/context_engine/odylith_context_engine_hot_path_packet_bootstrap_runtime.py`
- `src/odylith/runtime/context_engine/odylith_context_engine_hot_path_packet_finalize_runtime.py`
- `src/odylith/runtime/context_engine/odylith_context_engine_packet_summary_runtime.py`
- `src/odylith/runtime/execution_engine/runtime_surface_governance.py`
- `tests/unit/runtime/test_execution_engine.py`

## Validation Plan
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_execution_engine.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_execution_engine.py`
- `PYTHONPATH=src python -m odylith.cli validate backlog-contract --repo-root .`
- `git diff --check`
