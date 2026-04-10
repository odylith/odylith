Status: In progress

Created: 2026-04-09

Updated: 2026-04-09

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
  child workstream source records, the `B-072` program file, Registry component
  truth, Atlas diagrams `D-030` and `D-031`, the `D-002` refresh, and direct
  program/wave authoring commands.
- Scope excludes full downstream packet/shell/Compass UX completion for every
  execution-governance contract field in this first slice, release-targeting
  changes, and any claim of provider-complete external dependency support.

Related Bugs:
- no related bug found

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
- [ ] Add umbrella workstream `B-072`, child workstreams `B-073` through
      `B-079`, and companion program file
      `odylith/radar/source/programs/B-072.execution-waves.v1.json`.
- [ ] Bind this new in-progress technical plan to `B-072` only; child plans
      remain unopened until their waves go active.
- [ ] Add one new Registry component `execution-governance` and the new
      `src/odylith/runtime/execution_engine/` package with first-class contracts for
      task execution governance.
- [ ] Add core execution-governance types for task contract, hard constraints,
      admissibility decisions, frontier, closure, external dependency state,
      receipts, resume handles, validation matrix, contradiction records, and
      host-profile aware execution hints.
- [ ] Add one dedicated Atlas diagram `D-030` for the execution-governance
      stack and refresh `D-002` so Context Engine clearly feeds execution
      governance instead of implicitly owning action control.
- [ ] Land a thin `odylith program ...` and `odylith wave ...` authoring sidecar
      that works directly against the existing execution-wave contract.
- [ ] Keep the execution-governance system explicitly general across Codex and
      Claude Code while detecting the active host/model profile and using those
      nuances only where the capability contract says they are valid.

## Should-Ship
- [ ] Add `D-031` to show program/wave authoring and coding-agent command flow
      without implying it is the main execution engine.
- [ ] Update the affected component specs so Context Engine stays grounding
      only, Delivery Intelligence and Proof State become evidence inputs, and
      Router/Orchestrator/Remediator execute through execution governance.
- [ ] Add focused tests for the program/wave authoring sidecar and the initial
      execution-governance contract helpers.

## Defer
- [ ] Full Shell, Compass, and packet UX integration for every
      execution-governance contract field can continue in later waves.
- [ ] Rich external dependency adapters beyond local long-running commands,
      Compass/agent-stream state, and GitHub Actions are not required in this
      first slice.
- [ ] Full policy middleware insertion in front of every existing execution
      surface can be phased after the base package and CLI are present.

## Success Criteria
- [ ] `B-072` and its child program are valid governed source truth and render
      through the existing execution-wave contract.
- [ ] `execution-governance` exists as a first-class Registry component with a
      living spec and explicit boundaries against Context Engine, Delivery
      Intelligence, Proof State, Router, Orchestrator, Tribunal, and
      Remediator.
- [ ] `src/odylith/runtime/execution_engine/` exists and exports typed execution
      governance contracts plus initial policy helpers.
- [ ] Coding agents can create, inspect, and modify umbrella execution-wave
      programs through `odylith program ...` and `odylith wave ...` commands.
- [ ] The execution-governance base contract records host/model-family posture
      explicitly while keeping shared policy host-general.

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
5. Run focused backlog, Registry, CLI, and execution-governance validation.

## Validation
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_wave_contract.py tests/unit/runtime/test_execution_wave_view_model.py tests/unit/runtime/test_execution_governance.py tests/unit/runtime/test_program_wave_authoring.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py`
- [ ] `PYTHONPATH=src python3 -m odylith.cli validate backlog-contract --repo-root .`
- [ ] `PYTHONPATH=src python3 -m odylith.cli validate component-registry --repo-root .`
- [ ] `git diff --check`

## Outcome Snapshot
- [ ] Execution-governance is authored and implemented as a new product
      boundary rather than living as prompt-only guidance.
- [ ] The core contract stays general across Codex and Claude Code, with
      detected host/model-family nuance isolated behind explicit capability
      fields.
- [ ] Program and wave authoring becomes a real command surface for coding
      agents without displacing the execution-engine critical path.
