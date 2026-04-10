Status: In progress

Created: 2026-04-09

Updated: 2026-04-10

Backlog: B-072

Goal: Turn Odylith from a context-first grounding system into a
constraint-aware execution runtime that materializes one task contract,
screens actions for admissibility, preserves a truthful frontier, and keeps
execution behavior host-general across Codex and Claude Code while still
using each detected host/model family's real capabilities carefully.

Assumptions:
- The first slice is a foundational v1, not the full end-state execution OS
  across every external provider.
- The shared execution contract must stay host-general across Codex and Claude
  Code; host and model-family nuance belongs behind explicit runtime
  detection, capability fields, and policy hints.
- Release planning remains separate from execution sequencing. `B-063`
  continues to answer what ships, while `B-072` answers how the umbrella
  executes.
- Child plans should not open until their wave is actually promoted into
  active implementation; the umbrella plan carries the authoring slice.

Constraints:
- Keep execution-governance as the main critical path; program/wave ergonomics
  is a sidecar and must not displace the core execution-engine work.
- Do not invent a new Radar schema for programs or waves; use the existing
  `*.execution-waves.v1.json` contract.
- Keep the package boundary as one new `src/odylith/runtime/execution_engine/`
  sibling package rather than a governance subpackage or top-level Python
  package.
- Do not let Codex-only transport or model assumptions re-enter the shared
  execution contract after the `B-069` host-neutral work.
- Keep the program/wave authoring CLI thin and fail closed so it stays a
  source-of-truth preserving layer over the execution-wave contract.

Reversibility: The execution-governance package, Registry component, and
program/wave authoring commands are additive. If a policy or authoring surface
proves too strict, the rollback path is to relax or remove the additive layer
without rewriting existing Radar, Registry, or release-planning truth.

Boundary Conditions:
- Scope includes the new execution-governance package, typed contracts,
  admissibility helpers, frontier/closure/receipt primitives, the umbrella and
  child workstream source records including `B-082`, the `B-072` program file,
  Registry component truth, Atlas diagrams `D-030` and `D-031`, the `D-002`
  refresh, and direct program/wave authoring commands, plus initial
  packet-summary, shell, and Compass read-model exposure for
  execution-governance posture.
- Scope excludes field-complete UX for every possible execution-governance
  artifact, release-targeting changes, and any claim of provider-complete
  external dependency support.

Related Bugs:
- CB-093 - Compass runtime reuse can ignore live release and program source changes
- CB-094 - Compass current-workstream ranking can hide active release and wave lanes

## Learnings
- [ ] Odylith's dominant failure mode is not missing one more document; it is
      allowing a non-admissible next action after enough context already
      exists.
- [ ] Host-neutral shared contracts and host-specific execution affordances are
      separate concerns. The execution-governance layer must preserve that
      distinction instead of backsliding to Codex-default behavior.
- [ ] Program/wave ergonomics matters, but it should remain an authoring thin
      layer over the existing execution-wave contract rather than becoming a
      second planning system.

## Must-Ship
- [x] Add umbrella workstream `B-072`, child workstreams `B-073` through
      `B-079` and `B-082`, and companion program file
      `odylith/radar/source/programs/B-072.execution-waves.v1.json`.
- [x] Bind this new in-progress technical plan to `B-072` only; child plans
      remain unopened until their waves go active.
- [x] Add one new Registry component `execution-governance` and the new
      `src/odylith/runtime/execution_engine/` package with first-class contracts for
      task execution governance.
- [x] Add core execution-governance types for task contract, hard constraints,
      admissibility decisions, frontier, closure, external dependency state,
      receipts, resume handles, validation matrix, contradiction records, and
      host-profile aware execution hints.
- [x] Add one dedicated Atlas diagram `D-030` for the execution-governance
      stack and refresh `D-002` so Context Engine clearly feeds execution
      governance instead of implicitly owning action control.
- [x] Land a thin `odylith program ...` and `odylith wave ...` authoring sidecar
      that works directly against the existing execution-wave contract.
- [x] Keep the execution-governance system explicitly general across Codex and
      Claude Code while detecting the active host/model profile and using those
      nuances only where the capability contract says they are valid.

## Should-Ship
- [x] Add `D-031` to show program/wave authoring and coding-agent command flow
      without implying it is the main execution engine.
- [x] Update the affected component specs so Context Engine stays grounding
      only, Delivery Intelligence and Proof State become evidence inputs, and
      Router/Orchestrator/Remediator execute through execution governance.
- [x] Add focused tests for the program/wave authoring sidecar and the initial
      execution-governance contract helpers.
- [x] Surface execution-governance outcome, frontier, closure, validation, wait
      state, resume posture, and detected host-family posture in packet
      summaries plus the shared shell/Compass runtime summary.

## Defer
- [ ] Full-fidelity Shell, Compass, and packet UX for every
      execution-governance artifact can continue in later waves after the base
      summary and posture fields are proven stable.
- [ ] Rich external dependency adapters beyond local long-running commands,
      Compass/agent-stream state, and GitHub Actions are not required in this
      first slice.
- [ ] Full policy middleware insertion in front of every existing execution
      surface can be phased after the base package and CLI are present.

## Success Criteria
- [x] `B-072` and its child program are valid governed source truth and render
      through the existing execution-wave contract.
- [x] `execution-governance` exists as a first-class Registry component with a
      living spec and explicit boundaries against Context Engine, Delivery
      Intelligence, Proof State, Router, Orchestrator, Tribunal, and
      Remediator.
- [x] `src/odylith/runtime/execution_engine/` exists and exports typed execution
      governance contracts plus initial policy helpers.
- [x] Coding agents can create, inspect, and modify umbrella execution-wave
      programs through `odylith program ...` and `odylith wave ...` commands.
- [x] The execution-governance base contract records host/model-family posture
      explicitly while keeping shared policy host-general.
- [x] Packet summaries and shell/Compass runtime surfaces show one governed next
      move, closure posture, wait or resume state, validation archetype, and
      re-anchor pressure from the same execution-governance snapshot.

## Non-Goals
- [ ] Replacing release planning with execution waves.
- [ ] Treating larger memory or retrieval breadth as the primary solution to
      execution failure.
- [ ] Claiming Claude-native delegation parity or other host capabilities
      without explicit runtime detection and proof.

## Impacted Areas
- [ ] `odylith/radar/source/ideas/2026-04/2026-04-09-execution-governance-engines-admissibility-control-and-constraint-aware-action-runtime.md`
- [ ] `odylith/radar/source/programs/B-072.execution-waves.v1.json`
- [ ] `odylith/technical-plans/in-progress/2026-04/2026-04-09-execution-governance-engines-admissibility-control-and-constraint-aware-action-runtime.md`
- [ ] `odylith/registry/source/component_registry.v1.json`
- [ ] `odylith/registry/source/components/execution-governance/CURRENT_SPEC.md`
- [ ] `odylith/atlas/source/catalog/diagrams.v1.json`
- [ ] `odylith/atlas/source/odylith-context-and-agent-execution-stack.mmd`
- [ ] `odylith/atlas/source/odylith-execution-governance-engine-stack.mmd`
- [ ] `odylith/atlas/source/odylith-program-wave-authoring-and-agent-command-flow.mmd`
- [ ] `src/odylith/runtime/execution_engine/`
- [ ] `src/odylith/runtime/governance/`
- [ ] `src/odylith/cli.py`
- [ ] `tests/unit/runtime/test_execution_governance.py`
- [ ] `tests/unit/runtime/test_program_wave_authoring.py`

## Rollout
1. Author the umbrella/child workstream truth, program file, and umbrella
   plan.
2. Add the execution-governance component boundary and Atlas topology changes.
3. Land the runtime execution package and its host-profile aware contract
   helpers.
4. Add the thin program/wave authoring commands on top of the existing
   execution-wave contract.
5. Expose the base execution-governance snapshot through packet summaries and
   shared shell/Compass runtime surfaces.
6. Run focused backlog, Registry, CLI, and execution-governance validation.

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_wave_contract.py tests/unit/runtime/test_execution_wave_view_model.py tests/unit/runtime/test_execution_governance.py tests/unit/runtime/test_program_wave_authoring.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_context_engine_proof_packet_runtime.py tests/unit/runtime/test_odylith_runtime_surface_summary.py tests/unit/runtime/test_render_tooling_dashboard.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py`
- [x] `PYTHONPATH=src python3 -m odylith.cli validate backlog-contract --repo-root .`
- [x] `PYTHONPATH=src python3 -m odylith.cli validate component-registry --repo-root .`
- [x] `git diff --check`

## Outcome Snapshot
- [x] Execution-governance is authored and implemented as a new product
      boundary rather than living as prompt-only guidance.
- [x] The core contract stays general across Codex and Claude Code, with
      detected host/model-family nuance isolated behind explicit capability
      fields.
- [x] Program and wave authoring becomes a real command surface for coding
      agents without displacing the execution-engine critical path.
- [x] Packet summaries and shared runtime surfaces now carry execution-governance
      posture instead of forcing operators to infer frontier or admissibility
      from unrelated packet metadata.
