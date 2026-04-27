Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-015

Goal: Improve Odylith's delegated reasoning ladder and grounded spawn defaults
so Codex gets more accurate, faster, and more reliable routed execution without
regressing benchmark proof.

Assumptions:
- Odylith's current routed delegation stack is already safe enough to tighten
  rather than replace.
- The right improvement is a shared earned-depth and delegation-readiness
  contract across runtime hints, router selection, and orchestration posture.
- Native spawn remains Codex-only; Claude Code should stay local-only until the
  runtime contract is explicitly validated there.

Constraints:
- Do not regress required-path recall or validation success in the benchmark.
- Do not make bounded support or mechanical slices materially more expensive.
- Keep consumer guidance aligned with the real routed runtime contract.

Reversibility: Reverting this slice restores the previous routing ladder,
orchestrator posture, and guidance wording without data migration.

Boundary Conditions:
- Scope includes Router scoring/backstops, Orchestrator posture, hot-path
  execution-profile alignment, consumer guidance/skills, and benchmark proof.
- Scope excludes Claude Code native spawn enablement and benchmark-corpus
  redesign.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] Router depth promotion is still too additive instead of clearly earned.
- [x] Runtime execution-profile hints do not fully align with Router promotion
  paths.
- [x] Grounded delegation posture is still more conservative than necessary on
  some bounded Codex slices.
- [x] Consumer guidance does not yet make "ground then delegate with Odylith"
  feel like the default Codex path.

## Success Criteria
- [x] Task assessment carries explicit earned-depth and delegation-readiness
  posture.
- [x] Router selection and backstops use that posture to climb or cap reasoning
  tiers more judiciously.
- [x] Orchestrator fan-out posture uses the same signals to prefer bounded
  delegation when grounded and to stay conservative when guarded.
- [x] Hot-path execution-profile synthesis aligns with the stronger routing
  ladder.
- [x] Consumer guidance and skills default Codex users to Odylith-backed
  delegation for most grounded substantive prompts.
- [x] Benchmark proof stays green and improves at least one measured benchmark
  signal without regressing recall or validation.

## Non-Goals
- [x] Claude Code native spawn support.
- [x] Large benchmark-corpus redesign.
- [x] New public spawn APIs.

## Impacted Areas
- [x] [subagent_router.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_router.py)
- [x] [subagent_orchestrator.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_orchestrator.py)
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [SUBAGENT_ROUTING_AND_ORCHESTRATION.md](/Users/freedom/code/odylith/odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-subagent-router/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-subagent-orchestrator/SKILL.md)
- [x] [test_odylith_evaluation_ledger.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_evaluation_ledger.py)
- [x] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)

## Risks & Mitigations

- [x] Risk: heavier profiles get promoted too often and hurt benchmark spend.
  - [x] Mitigation: keep earned-depth and guarded-history backstops explicit,
    then rerun the benchmark before closeout.
- [x] Risk: orchestration becomes too eager on merge-heavy slices.
  - [x] Mitigation: keep merge-burden and guarded parallelism checks in the
    main-thread and serial gates.
- [x] Risk: consumer guidance promises behavior the runtime does not emit.
  - [x] Mitigation: update guidance only after the runtime contract and tests
    are in place.

## Validation/Test Plan
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_evaluation_ledger.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_subagent_surface_validation.py`
- [x] `odylith benchmark --repo-root .`
- [ ] `git diff --check`

## Rollout/Communication
- [x] Keep native spawn explicitly Codex-only in the consumer contract.
- [x] Sync bundle mirrors after the product guidance changes land.
- [x] Update backlog and plan indexes when the slice closes.

## Current Outcome
- Odylith now classifies product skills, consumer guidance, runtime contract
  docs, and shell surfaces as delegateable contract or implementation work
  instead of collapsing them into host-local governance follow-up.
- The proof lane now delegates grounded Codex slices much more often without
  weakening the conservative local posture for governance closeout and
  architecture dossiers.
- Latest benchmark report `091cdd60b1795fc8` stayed green and improved to:
  `latency_delta_ms=-15.015`, `prompt_token_delta=-631.5`,
  `total_payload_token_delta=-631.5`, `required_path_recall_delta=+0.964`,
  `validation_success_delta=+0.714`, and `grounded_delegate_rate=0.800`.
