Status: Done

Created: 2026-04-12

Updated: 2026-04-12

Backlog: B-079

Goal: Give coding agents a thin, fail-closed program/wave authoring CLI over
the existing execution-wave contract without creating a second planning system.

Assumptions:
- Program/wave ergonomics is a sidecar over the main execution-governance
  engine.
- CLI-first authoring is mandatory once the command surface exists.

Constraints:
- Keep authoring contract-preserving and fail closed.
- Make status and next-command output truthful enough that agents stop
  hand-editing wave JSON.

Related Bugs:
- No related bug found.

## Learnings
- [x] The sidecar only works when it preserves the canonical execution-wave
      contract instead of hiding it.
- [x] Ergonomics regress quickly when status and next-command advice stop
      reflecting real gate posture.

## Must-Ship
- [x] Add `odylith program ...` and `odylith wave ...` command families.
- [x] Keep selector resolution fail closed and gate-add/status flows grounded
      in real wave membership.
- [x] Expose program/wave posture into shell, Compass, and related read-model
      surfaces.

## Success Criteria
- [x] Coding agents can inspect and mutate wave programs through CLI commands
      instead of hand-editing JSON.
- [x] Program/wave status survives into the operator surfaces from the same
      governed source truth.

## Impacted Areas
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/governance/program_wave_authoring.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/program_wave_authoring.py)
- [x] [/Users/freedom/code/odylith/src/odylith/runtime/governance/execution_wave_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/execution_wave_contract.py)
- [x] [/Users/freedom/code/odylith/src/odylith/cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_program_wave_authoring.py tests/unit/runtime/test_execution_wave_contract.py tests/unit/runtime/test_execution_wave_view_model.py tests/unit/test_cli.py -k 'program or wave or release'`
- [x] `PYTHONPATH=src python3 -m odylith.cli validate backlog-contract --repo-root .`

## Current Outcome
- [x] Program/wave authoring is now a real CLI surface for agents and stays
      thin over the canonical execution-wave program contract.
