Status: Done

Created: 2026-04-12

Updated: 2026-04-12

Backlog: B-073

Goal: Land the typed execution contract, event stream, hard-constraint
promotion, and host-profile envelope that every later execution-governance
decision depends on.

Assumptions:
- The shared contract must stay host-general across Codex and Claude Code.
- Execution events are append-only and additive; they should not force older
  packet or surface readers to rewrite history.

Constraints:
- Keep task contract, hard constraints, and host-profile detection as one
  shared runtime substrate instead of per-surface heuristics.
- Preserve governed sync invariants by keeping new summary fields compact,
  content-addressed, and derivation-safe.

Related Bugs:
- No related bug found.

## Learnings
- [x] The engine needs one typed state contract before `admit|deny|defer`
      decisions can be trustworthy.
- [x] User corrections only become durable guardrails once they are promoted
      into explicit hard constraints instead of narrative memory.

## Must-Ship
- [x] Add `ExecutionContract`, `HardConstraint`, `ExecutionEvent`,
      `ExecutionHostProfile`, and the base execution-governance runtime types.
- [x] Add append-only event shaping so policy, frontier, contradiction,
      closure, and receipt state can replay from one stream.
- [x] Detect host and model-family posture explicitly without leaking
      host-specific behavior into the shared contract.

## Success Criteria
- [x] Hard constraints and host-profile posture are first-class fields in the
      shared execution contract.
- [x] Later waves can derive frontier, admissibility, wait state, and history
      pressure from one additive event stream.

## Impacted Areas
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/contract.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/contract.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/event_stream.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/event_stream.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_surface_governance.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_surface_governance.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_governance.py tests/unit/runtime/test_execution_wave_contract.py tests/unit/runtime/test_execution_wave_view_model.py`
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`

## Current Outcome
- [x] The execution engine now has one typed, host-general task contract and
      event stream that later policy, frontier, and surface layers reuse.
