Status: Done

Created: 2026-04-12

Updated: 2026-04-12

Backlog: B-074

Goal: Put one shared admissibility gate in front of governed mutations,
delegation, and execution surfaces so Odylith blocks the wrong next move
before it executes.

Assumptions:
- The policy contract must stay `admit|deny|defer` everywhere.
- Re-anchor pressure should come from shared state, not local surface-only
  counters.

Constraints:
- Keep nearest-admissible-alternative output and violated preconditions
  explicit.
- Preserve sync-safe summary export so policy posture can flow into shell,
  Compass, router, and packet summaries without reopening derivation loops.

Related Bugs:
- No related bug found.

## Learnings
- [x] The important regression boundary is the shared policy layer, not any one
      surface renderer.
- [x] Re-anchor only becomes durable when denials, off-contract actions, and
      contradiction pressure survive across surfaces.

## Must-Ship
- [x] Add the shared admissibility policy helpers and hard-constraint mutation
      logic.
- [x] Route program/wave authoring, release authoring, router, orchestrator,
      and remediator through the same execution-governance posture.
- [x] Carry denial pressure, contradiction pressure, and nearby denied actions
      through the shared runtime summary path.

## Success Criteria
- [x] Governed authoring and execution surfaces return structured
      `admit|deny|defer` decisions with explicit violated preconditions.
- [x] Re-anchor pressure survives into packet, shell, Compass, and router
      consumers from the same shared summary.

## Impacted Areas
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/policy.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/policy.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_lane_policy.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_lane_policy.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/governance/authoring_execution_policy.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/authoring_execution_policy.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/governance/program_wave_execution_governance.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/program_wave_execution_governance.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_governance.py tests/unit/runtime/test_program_wave_authoring.py tests/unit/runtime/test_subagent_reasoning_ladder.py tests/unit/runtime/test_remediator.py`
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --force --impact-mode full`

## Current Outcome
- [x] Execution-governance middleware now blocks or defers off-contract actions
      across authoring and execution paths from one shared decision model.
