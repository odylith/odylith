Status: In progress
Created: 2026-04-16
Updated: 2026-04-16
Backlog: B-102

# Codex Claude Execution Contract Parity

## Goal
Keep the base Execution Engine contract host-general while proving Codex and Claude Code produce the same policy semantics for the same packet and differ only through explicit host capability, model, and delegation fields.

## Assumptions
- Codex and Claude Code are both valid Odylith execution hosts.
- `ExecutionHostProfile` is the only place host differences should enter the Execution Engine contract.
- Semantic policy fields must remain identical across hosts for the same route-ready packet.
- Claude Code defaults may influence presentation policy, not admissibility semantics.

## Constraints
- Do not fork policy semantics by host family.
- Do not introduce host-specific Context Engine packet shapes.
- Keep host-specific behavior behind capability fields such as delegation style, interrupt support, and artifact-path support.
- Keep benchmark scenarios host-explicit through `host_candidates` rather than ambient environment assumptions.

## Reversibility
Host parity assertions can be narrowed if a future host exposes a real semantic capability difference, but that would require a new component contract and paired tests.

## Related Bugs
No related Casebook bug found.

## Must-Ship
- [x] Add paired Codex/Claude snapshot tests proving identical outcome, mode, next move, closure, validation archetype, authoritative lane, and re-anchor semantics.
- [x] Assert host capability differences remain isolated to host family, delegation style, interrupt support, and artifact-path support.
- [x] Add Claude benchmark scenarios for route-ready policy parity and external wait/resume.
- [x] Keep host detection behind `ExecutionHostProfile` and existing semantic runtime profiles.

## Should-Ship
- [x] Keep Claude presentation defaults tested as presentation-only behavior.
- [x] Preserve delegation and parallelism guard coverage for host capability differences.

## Deferred
- Any host-specific full policy fork.
- Any compatibility layer for old execution component ids.

## Success Criteria
- Codex and Claude packets agree on base policy semantics.
- Claude Code packets carry Claude host-family fields in benchmark summaries.
- Guard tests still block unsafe delegation and parallelism when host capability fields require it.

## Impacted Areas
- `src/odylith/runtime/execution_engine/runtime_surface_governance.py`
- `tests/unit/runtime/test_execution_engine.py`
- `odylith/runtime/source/optimization-evaluation-corpus.v1.json`
- `src/odylith/bundle/assets/odylith/runtime/source/optimization-evaluation-corpus.v1.json`

## Validation Plan
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_execution_engine.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_odylith_benchmark_execution_engine.py`
- `git diff --check`
