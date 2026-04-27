Status: Done

Created: 2026-04-12

Updated: 2026-04-12

Backlog: B-078

Goal: Synthesize validation from the active contract, detect contradictions
before execution, and turn repeated failure classes into executable preflight
blockers.

Assumptions:
- Validation posture must stay minimal and contract-derived, not checklist
  folklore.
- History-based blocking must remain evidence-backed instead of speculative.

Constraints:
- Contradictions, validation derivation, and history-rule hits must survive the
  shared summary layer without collapsing to coarse counts only.
- Casebook-backed pressure must remain low-latency and sync-safe.

Related Bugs:
- No related bug found.

## Learnings
- [x] Validation and contradiction posture are only useful when the reasons
      survive into runtime consumers.
- [x] Known failure classes add the most value when they block execution
      preflight instead of becoming another searchable note.

## Must-Ship
- [x] Add `ValidationMatrix` synthesis from contract and closure posture.
- [x] Add contradiction detection and history-rule blocking in the shared core.
- [x] Export validation derivation, contradiction counts, pressure signals, and
      history-rule hits through one shared summary path.

## Success Criteria
- [x] The engine surfaces minimal validation posture and contradiction counts
      from one shared source.
- [x] Known failure classes can deny the next move before execution rather than
      being rediscovered from live failure.

## Impacted Areas
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/validation.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/validation.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/contradictions.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/contradictions.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/history_rules.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/history_rules.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_governance.py tests/unit/runtime/test_odylith_runtime_surface_summary.py tests/unit/runtime/test_subagent_reasoning_ladder.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_compass_browser_regression_matrix.py tests/integration/runtime/test_surface_browser_smoke.py`

## Current Outcome
- [x] The shared execution engine now derives validation, contradictions, and
      history-rule pressure before execution and exports the reasons intact.
