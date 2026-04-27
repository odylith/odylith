Status: Done

Created: 2026-04-12

Updated: 2026-04-12

Backlog: B-082

Goal: Add one structured turn-intake contract that preserves visible-text
anchors, lane-fenced writable targets, and task-first presentation policy
across consumer and maintainer lanes.

Assumptions:
- Consumer and maintainer lanes need the same intake pipeline with different
  write boundaries.
- Visible-text anchors and semantic intent should not collapse into one field.

Constraints:
- Consumer turns must never emit Odylith-owned writable targets.
- Maintainer mode in the product repo must remain targetable when lane policy
  authorizes it.

Related Bugs:
- No related bug found.

## Learnings
- [x] Structured turn context is the difference between useful grounding and
      accidental control-plane mutation pressure.
- [x] Presentation policy belongs in the same shared packet contract as target
      resolution and turn intent.

## Must-Ship
- [x] Add structured `turn_context`, `target_resolution`, and
      `presentation_policy` fields through CLI, packet session runtime, and
      packet summaries.
- [x] Keep consumer write fences hard while allowing maintainer-authorized
      Odylith targetability in the product repo.
- [x] Carry task-first presentation policy through orchestration and chatter
      surfaces.

## Success Criteria
- [x] The same turn-intake path works across consumer and maintainer lanes
      without leaking writable Odylith targets into consumer turns.
- [x] Structured turn context and presentation policy survive into execution
      governance and operator-facing summaries.

## Impacted Areas
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/context_engine/turn_context_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/turn_context_runtime.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_packet_session_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_packet_session_runtime.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_surface_governance.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_surface_governance.py)
- [x] [/Users/freedom/code/odylith/src/odylith/cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py tests/unit/runtime/test_turn_context_runtime.py tests/unit/runtime/test_odylith_context_engine_turn_cli.py tests/integration/runtime/test_context_engine_turn_intake.py`
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`

## Current Outcome
- [x] The execution engine now carries structured turn intake, lane-fenced
      targeting, and task-first presentation policy through the shared packet
      and runtime summary path.
