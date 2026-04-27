Status: Done

Created: 2026-04-12

Updated: 2026-04-12

Backlog: B-075

Goal: Derive one truthful execution frontier and explicit execution modes so
verify/recover lanes stop branching, user corrections stay invariant, and the
next move remains grounded.

Assumptions:
- The frontier must come from the shared execution event stream, not local
  surface memory.
- Verify and recover modes are allowed to be stricter than implement.

Constraints:
- Preserve frontier and mode posture through packet summaries, router,
  orchestrator, remediator, shell, and Compass.
- Keep natural-language operator corrections promotable into hard constraints.

Related Bugs:
- No related bug found.

## Learnings
- [x] One frontier record is more reliable than per-surface remembered state.
- [x] Critical-path mode only works if verify/recover actively deny scratch
      rediscovery and side exploration.

## Must-Ship
- [x] Add frontier derivation with current phase, last success, blocker,
      external ids, resume handles, and truthful next move.
- [x] Promote natural-language corrections into hard constraints at the shared
      contract layer.
- [x] Carry mode budgets into router/orchestrator/remediator and shared
      surface summaries.

## Success Criteria
- [x] Packet, shell, Compass, and runtime consumers all see the same frontier
      and mode posture.
- [x] Verify and recover lanes deny exploration when frontier truth has not
      materially changed.

## Impacted Areas
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/frontier.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/frontier.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_surface_governance.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_surface_governance.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_runtime_surface_summary.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_runtime_surface_summary.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_governance.py tests/unit/runtime/test_odylith_runtime_surface_summary.py tests/unit/runtime/test_context_engine_proof_packet_runtime.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py tests/unit/runtime/test_remediator.py`

## Current Outcome
- [x] The execution engine now exports one truthful frontier and mode posture
      that later surfaces consume instead of rebuilding locally.
