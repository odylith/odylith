Status: Done

Created: 2026-04-15

Updated: 2026-04-15

Backlog: B-098

Goal: Make Radar backlog detail fail closed with real workstream content and
prevent `odylith backlog create` from ever publishing another generic
core-detail workstream record. The concrete user-visible failure is `B-073`
rendering as if it lacks details even though its idea spec and generated detail
shards are populated. The broader governance failure is that recent workstreams
such as `B-086`, `B-089`, `B-090`, and `B-098` still carry the title-derived
boilerplate in the sections Radar uses to explain a slice.

Assumptions:
- The source markdown under `odylith/radar/source/ideas/` remains the
  authoritative workstream truth; Radar is a projection and must not invent or
  discard intent.
- The runtime backlog-detail endpoint is allowed to return a richer
  renderer-facing contract than the current raw `{metadata, sections}` shape if
  that is what the Radar UI actually consumes.
- The minimum authored contract that makes a workstream legible is the core
  detail set surfaced in Radar: Problem, Customer, Opportunity, Product View,
  and Success Metrics.
- The static snapshot path and runtime-backed path should converge on one
  truthful detail contract instead of each making separate assumptions about the
  workstream payload shape.

Constraints:
- Do not widen this slice into a Radar redesign; the issue is detail honesty,
  not layout.
- Do not reintroduce a permissive title-only backlog-create fast path behind a
  silent fallback or hidden flag.
- Keep the authoring hardening CLI-first: new workstreams should still be
  created through `odylith backlog create`, just with grounded inputs.
- Do not break grounding-light backlog detail loads used by the context engine
  for non-UI routing work.
- Treat existing unrelated dirty-worktree changes as out of scope.

Reversibility: The slice is structurally reversible. The runtime-detail
normalization, backlog-create argument contract, validator checks, and guidance
updates can all be reverted without rewriting workstream ids or plan bindings.
Retrofilled workstream prose should not be reverted because it repairs governed
truth rather than introducing speculative content.

Boundary Conditions:
- Scope includes
  `src/odylith/runtime/context_engine/odylith_context_engine_projection_backlog_runtime.py`,
  `src/odylith/runtime/governance/backlog_authoring.py`,
  `src/odylith/runtime/governance/validate_backlog_contract.py`,
  `src/odylith/runtime/surfaces/render_backlog_ui.py`,
  shared backlog-create guidance under `odylith/skills/` and
  `odylith/agents-guidelines/`, and the offending workstream markdown files in
  `odylith/radar/source/ideas/`.
- Scope excludes a new Casebook bug unless the investigation uncovers a second
  product failure beyond the current Radar/backlog authoring slice.
- Scope excludes a new general-purpose backlog editor CLI; this slice only
  hardens creation and validation plus retrofills the current records by hand.

Related Bugs:
- No dedicated Casebook bug yet. The active user-visible failure is Radar
  showing hollow detail for populated workstream `B-073`, and the active
  governance failure is generic core-detail boilerplate surviving in recent
  backlog records.

## Learnings
- [x] Radar detail honesty depends on one shared contract between the static
      snapshot and runtime-backed detail lane; raw section payloads are not a
      usable UI contract by themselves.
- [x] Backlog validation cannot stop at structural completeness. A workstream
      with every required heading can still be hollow if the core sections are
      only the title-derived boilerplate.
- [x] `odylith backlog create` must gather real narrative inputs up front or it
      becomes a generic workstream factory that poisons the product's own
      planning memory.
- [x] Test fixtures are part of the contract surface: synthetic backlog records
      must model grounded core detail unless the test is explicitly asserting
      placeholder rejection.

## Must-Ship
- [x] Bind `B-098` to this active plan and keep the Radar/plan indexes
      consistent.
- [x] Normalize runtime backlog detail so the Radar UI receives renderer-ready
      core fields from `load_backlog_detail(...)`.
- [x] Keep the Radar summary/detail contract honest for traceability and
      impacted-parts fields even when a heavy detail fetch is not used.
- [x] Extend `odylith backlog create` to require grounded Problem, Customer,
      Opportunity, Product View, and Success Metrics inputs.
- [x] Make backlog validation reject generic or placeholder core-detail
      sections rather than only missing headings.
- [x] Update the shared backlog-create skill, CLI-first guidance, and Radar
      authoring guidance to match the new grounded-input contract.
- [x] Retrofill the current offending workstreams: `B-086`, `B-088`, `B-089`,
      `B-090`, `B-097`, and `B-098`.
- [x] Replace legacy placeholder-backed backlog test fixtures so future tests do
      not normalize the old `Details.` authoring pattern.
- [x] Refresh Radar and rerun focused validation.

## Should-Ship
- [x] Keep the runtime detail payload rich enough that future runtime-backed
      Radar consumers do not need a second normalization path.
- [x] Add one focused regression assertion that the generated Radar payload
      still carries the fields needed for an honest detail panel.

## Defer
- [ ] A broader backlog-schema redesign or full editor workflow for existing
      workstreams.
- [ ] Escalating boilerplate rejection from core sections to every optional
      authoring section unless the first hardening pass proves that is needed.
- [ ] Reworking the runtime list endpoint to become the primary Radar list
      source; today it is not the user-facing blocker.

## Success Criteria
- [x] `B-073` renders real Problem/Customer/Opportunity/Product View/Success
      Metrics content in Radar without manual fallback surgery.
- [x] `odylith backlog create` fails closed when those core fields are missing.
- [x] `odylith validate backlog-contract --repo-root .` fails on generic
      core-detail boilerplate.
- [x] No current product-repo backlog record still matches the generic
      core-detail template.
- [x] Focused tests are green on the touched runtime, authoring, and validator
      surfaces.

## Impacted Areas
- [ ] [2026-04-15-radar-backlog-detail-fail-closed-completeness-and-authoring-hardening.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-15-radar-backlog-detail-fail-closed-completeness-and-authoring-hardening.md)
- [ ] [2026-04-15-radar-backlog-detail-fail-closed-completeness-and-authoring-hardening.md](/Users/freedom/code/odylith/odylith/technical-plans/done/2026-04/2026-04-15-radar-backlog-detail-fail-closed-completeness-and-authoring-hardening.md)
- [ ] [src/odylith/runtime/context_engine/odylith_context_engine_projection_backlog_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_projection_backlog_runtime.py)
- [ ] [src/odylith/runtime/context_engine/odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [ ] [src/odylith/runtime/governance/backlog_authoring.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/backlog_authoring.py)
- [ ] [src/odylith/runtime/governance/validate_backlog_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/validate_backlog_contract.py)
- [ ] [src/odylith/runtime/intervention_engine/apply.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/apply.py)
- [ ] [src/odylith/runtime/intervention_engine/engine.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/engine.py)
- [ ] [src/odylith/runtime/analysis_engine/show_capabilities.py](/Users/freedom/code/odylith/src/odylith/runtime/analysis_engine/show_capabilities.py)
- [ ] [src/odylith/runtime/surfaces/render_backlog_ui.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui.py)
- [ ] [AGENTS.md](/Users/freedom/code/odylith/AGENTS.md)
- [ ] [odylith/AGENTS.md](/Users/freedom/code/odylith/odylith/AGENTS.md)
- [ ] [src/odylith/install/agents.py](/Users/freedom/code/odylith/src/odylith/install/agents.py)
- [ ] [src/odylith/install/manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [ ] [odylith/skills/odylith-backlog-create/SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-backlog-create/SKILL.md)
- [ ] [odylith/skills/odylith-backlog-validate/SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-backlog-validate/SKILL.md)
- [ ] [odylith/agents-guidelines/CLI_FIRST_POLICY.md](/Users/freedom/code/odylith/odylith/agents-guidelines/CLI_FIRST_POLICY.md)
- [ ] [odylith/radar/source/AGENTS.md](/Users/freedom/code/odylith/odylith/radar/source/AGENTS.md)
- [ ] [odylith/registry/source/components/radar/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/radar/CURRENT_SPEC.md)
- [ ] [tests/unit/runtime/test_backlog_authoring.py](/Users/freedom/code/odylith/tests/unit/runtime/test_backlog_authoring.py)
- [ ] [tests/unit/runtime/test_validate_backlog_contract.py](/Users/freedom/code/odylith/tests/unit/runtime/test_validate_backlog_contract.py)
- [ ] [tests/unit/runtime/test_odylith_context_engine_store.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_context_engine_store.py)
- [ ] [tests/unit/runtime/test_render_backlog_ui.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_backlog_ui.py)
- [ ] [tests/unit/runtime/test_intervention_engine.py](/Users/freedom/code/odylith/tests/unit/runtime/test_intervention_engine.py)
- [ ] [tests/unit/runtime/test_intervention_engine_apply.py](/Users/freedom/code/odylith/tests/unit/runtime/test_intervention_engine_apply.py)
- [ ] [tests/unit/test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [ ] [tests/unit/runtime/test_sync_cli_compat.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_cli_compat.py)
- [ ] [tests/unit/runtime/test_auto_promote_workstream_phase.py](/Users/freedom/code/odylith/tests/unit/runtime/test_auto_promote_workstream_phase.py)
- [ ] [tests/unit/runtime/test_reconcile_plan_workstream_binding.py](/Users/freedom/code/odylith/tests/unit/runtime/test_reconcile_plan_workstream_binding.py)
- [ ] [tests/unit/runtime/test_context_engine_release_resolution.py](/Users/freedom/code/odylith/tests/unit/runtime/test_context_engine_release_resolution.py)
- [ ] [tests/unit/runtime/test_legacy_backlog_normalization.py](/Users/freedom/code/odylith/tests/unit/runtime/test_legacy_backlog_normalization.py)
- [ ] [tests/unit/runtime/test_validate_plan_workstream_binding.py](/Users/freedom/code/odylith/tests/unit/runtime/test_validate_plan_workstream_binding.py)
- [ ] [tests/unit/runtime/test_release_planning.py](/Users/freedom/code/odylith/tests/unit/runtime/test_release_planning.py)
- [ ] [tests/unit/runtime/test_execution_wave_contract.py](/Users/freedom/code/odylith/tests/unit/runtime/test_execution_wave_contract.py)
- [ ] [tests/unit/runtime/test_release_truth_runtime.py](/Users/freedom/code/odylith/tests/unit/runtime/test_release_truth_runtime.py)
- [ ] [tests/unit/runtime/test_tooling_dashboard_surface_status.py](/Users/freedom/code/odylith/tests/unit/runtime/test_tooling_dashboard_surface_status.py)
- [ ] [tests/unit/runtime/test_compass_governance_source_runtime.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_governance_source_runtime.py)
- [ ] [tests/unit/runtime/test_program_wave_authoring.py](/Users/freedom/code/odylith/tests/unit/runtime/test_program_wave_authoring.py)

## Validation
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_backlog_authoring.py tests/unit/runtime/test_validate_backlog_contract.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_context_engine_store.py tests/unit/runtime/test_render_backlog_ui.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_intervention_engine.py tests/unit/runtime/test_intervention_engine_apply.py tests/unit/test_cli.py -k 'backlog_create or intervention or radar'`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_auto_promote_workstream_phase.py tests/unit/runtime/test_reconcile_plan_workstream_binding.py tests/unit/runtime/test_context_engine_release_resolution.py tests/unit/runtime/test_legacy_backlog_normalization.py tests/unit/runtime/test_validate_plan_workstream_binding.py tests/unit/runtime/test_release_planning.py tests/unit/runtime/test_execution_wave_contract.py tests/unit/runtime/test_release_truth_runtime.py tests/unit/runtime/test_tooling_dashboard_surface_status.py tests/unit/runtime/test_compass_governance_source_runtime.py tests/unit/runtime/test_program_wave_authoring.py`
- [x] `PYTHONPATH=src python -m odylith.cli validate backlog-contract --repo-root .`
- [x] `PYTHONPATH=src python -m odylith.cli radar refresh --repo-root .`
- [x] `PYTHONPATH=src python -m odylith.cli registry refresh --repo-root .`
- [x] `PYTHONPATH=src python -m compileall -q src/odylith/runtime/governance src/odylith/runtime/context_engine src/odylith/runtime/surfaces src/odylith/runtime/intervention_engine src/odylith/runtime/analysis_engine`
- [x] `git diff --check`

## Current Outcome
- [x] Runtime and static Radar detail paths now preserve populated core
      workstream detail for `B-073`, while `odylith backlog create`,
      intervention-driven Radar proposals, show-capabilities apply-all, shared
      guidance, bundled skills, and backlog validation all fail closed on
      missing, placeholder, or boilerplate core detail.
