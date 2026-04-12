Status: Done

Created: 2026-04-12

Updated: 2026-04-12

Backlog: B-076

Goal: Compute safe, incomplete, and destructive scope before execution so the
engine can block partial-scope mistakes instead of diagnosing them after the
fact.

Assumptions:
- Closure posture must be computed from governed scope and packet truth, not
  operator intuition.
- The first domains are repo-local and governance-local, not provider-complete.

Constraints:
- Closure posture must stay cheap enough for sync-safe summary export.
- History-rule blocking should reuse the same closure result instead of
  recomputing destructive risk per surface.

Related Bugs:
- No related bug found.

## Learnings
- [x] Closure only matters if it is enforced before writes, delegation, and
      subset execution.
- [x] Destructive subset blocking gets stronger when closure posture and known
      failure rules share one core path.

## Must-Ship
- [x] Add the `ResourceClosure` contract and first-domain closure classifiers.
- [x] Feed closure posture into admissibility, history-rule blocking, packet
      summaries, shell, and Compass.
- [x] Use closure pressure inside runtime lane policy so destructive subsets
      are blocked before execution.

## Success Criteria
- [x] The engine distinguishes safe, incomplete, and destructive scope from
      one shared classifier.
- [x] Destructive subset posture is visible and actionable across runtime
      consumers.

## Impacted Areas
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/resource_closure.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/resource_closure.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/history_rules.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/history_rules.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_lane_policy.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/runtime_lane_policy.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_governance.py tests/unit/runtime/test_subagent_reasoning_ladder.py`
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`

## Current Outcome
- [x] The execution engine now carries computed closure posture all the way
      from the core classifier into operator and routing decisions.
