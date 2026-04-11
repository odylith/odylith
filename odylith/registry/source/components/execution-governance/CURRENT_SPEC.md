# Execution Governance
Last updated: 2026-04-11


Last updated (UTC): 2026-04-11

## Purpose
Execution Governance is Odylith's constraint-aware execution runtime. It
materializes one task contract, screens intended actions for admissibility,
keeps one truthful frontier, computes scope closure, normalizes receipts and
wait states, and records contradictions and validation obligations before
execution proceeds.

The shared contract is host-general across Codex and Claude Code. Host and
model-family nuance is additive and capability-gated through an explicit
runtime profile; it must not redefine the shared execution policy surface.

## Scope And Non-Goals
### Execution Governance owns
- machine-readable execution contracts for substantive sessions
- hard-constraint promotion from user corrections
- append-only execution event shaping
- admissibility decisions and re-anchor triggers
- frontier derivation and execution-mode posture
- resource closure and destructive-subset classification
- external dependency state normalization, semantic receipts, and resume handles
- contradiction records and validation-matrix synthesis
- thin program/wave authoring hooks that work directly against the canonical
  execution-wave contract

### Execution Governance does not own
- repo grounding or packet compilation from source truth; that belongs to
  [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md)
- scope synthesis or operator-readout posture by itself; that belongs to
  [Delivery Intelligence](../delivery-intelligence/CURRENT_SPEC.md)
- live blocker identity or proof-tier resolution; that belongs to
  [Proof State](../proof-state/CURRENT_SPEC.md)
- diagnosis of why the current posture exists; that belongs to
  [Tribunal](../tribunal/CURRENT_SPEC.md)
- free-form execution or host transport by itself; callers still own actual
  tool invocation

## Developer Mental Model
- Context Engine answers "what is true and relevant?"
- Execution Governance answers "given that truth, what is the next admissible
  move?"
- Delivery Intelligence, Proof State, and Tribunal are evidence inputs to the
  execution-governance layer, not substitutes for it.
- Router, Orchestrator, and Remediator may still shape delegated work, but
  they should route through execution-governance policy instead of bypassing
  admissibility.
- Host and model detection is explicit. Execution Governance can adapt hints,
  budgets, and affordances after it detects Codex, Claude, or another host,
  but it must keep the base contract portable and truthful first.

## Runtime Contract
### Owning modules
- `src/odylith/runtime/execution_engine/contract.py`
  Core execution-governance dataclasses and canonical payload shapes.
- `src/odylith/runtime/execution_engine/policy.py`
  Admissibility decisions, constraint promotion, and re-anchor helpers.
- `src/odylith/runtime/execution_engine/frontier.py`
  Frontier derivation and execution-mode shaping.
- `src/odylith/runtime/execution_engine/resource_closure.py`
  Safe/incomplete/destructive scope classification helpers.
- `src/odylith/runtime/execution_engine/receipts.py`
  Semantic receipt, external dependency, and resumability helpers.
- `src/odylith/runtime/execution_engine/validation.py`
  Validation-matrix synthesis.
- `src/odylith/runtime/execution_engine/contradictions.py`
  Contradiction detection across contract, evidence, and intended action.
- `src/odylith/runtime/execution_engine/runtime_surface_governance.py`
  Shared summary extraction so packet, shell, Compass, and router-consumable
  read models all carry the same compact execution-governance posture,
  including lane-fenced `target_resolution`, `turn_context`, and
  `presentation_policy` carry-through.
- `src/odylith/runtime/execution_engine/runtime_lane_policy.py`
  Local or serial follow-through guards for delegation and parallel fan-out
  when the active governed frontier says the next move is re-anchor, wait,
  critical-path verification, unsafe closure, or host-serial execution.

### Core types
- `ExecutionHostProfile`
- `ExecutionContract`
- `HardConstraint`
- `ExecutionEvent`
- `AdmissibilityDecision`
- `ExecutionFrontier`
- `ExecutionMode`
- `ResourceClosure`
- `ExternalDependencyState`
- `SemanticReceipt`
- `ResumeHandle`
- `ValidationMatrix`
- `ContradictionRecord`
- `TurnContext`
- `TargetResolution`
- `TurnPresentationPolicy`

## Contract Highlights
### `ExecutionHostProfile`
The detected execution-runtime profile. Important fields include:
- `host_family`
- `host_display_name`
- `model_family`
- `model_name`
- `delegation_style`
- `supports_native_spawn`
- `supports_local_structured_reasoning`
- `supports_explicit_model_selection`
- `execution_hints`

Both validated host families (Codex and Claude Code) declare
`supports_explicit_model_selection=True` and `supports_native_spawn=True`.
Codex resolves the execution profile ladder onto its Codex model tuples;
Claude resolves the same semantic ladder onto haiku, sonnet, or opus
through the per-host-family axis described in the runtime profile ladder
section below. Unknown hosts continue to fail closed without a delegation
style.

### Runtime Profile Ladder
The canonical execution profiles in
`src/odylith/runtime/common/agent_runtime_contract.py` are semantic
(`analysis_medium`, `analysis_high`, `fast_worker`, `write_medium`,
`write_high`, `frontier_high`, `frontier_xhigh`). The profile-to-model
table carries a host-family axis so each validated host returns a real
model. Codex column tuples are canonical and must not drift; the Claude
column maps each profile onto haiku (analysis/fast), sonnet (write), or
opus (frontier). `execution_profile_runtime_fields(profile, *,
host_runtime)` returns `(model, reasoning_effort)` for the resolved
host-family row, and never returns an empty model for a validated host.

### `ExecutionContract`
The active machine-readable task contract. Important fields include:
- `objective`
- `authoritative_lane`
- `target_scope`
- `environment`
- `resource_set`
- `success_criteria`
- `validation_plan`
- `allowed_moves`
- `forbidden_moves`
- `external_dependencies`
- `critical_path`
- `hard_constraints`
- `host_profile`
- `turn_context`
- `target_resolution`
- `presentation_policy`

### `AdmissibilityDecision`
Every screened action resolves to one of:
- `admit`
- `deny`
- `defer`

The decision may also carry:
- violated preconditions
- nearest admissible alternative
- re-anchor requirement
- host-aware hints that stay additive to the shared decision

### `ExecutionFrontier`
The current truth record for governed execution. Important fields include:
- `current_phase`
- `last_successful_phase`
- `active_blocker`
- `in_flight_external_ids`
- `resume_handles`
- `truthful_next_move`
- `execution_mode`

### `ResourceClosure`
Subset classification for destructive-risk analysis:
- `safe`
- `incomplete`
- `destructive`

### `SemanticReceipt`
Typed mutation or handoff receipt carrying:
- scope fingerprint
- causal parent
- resume token
- expected next states

## Program/Wave Authoring Sidecar
Execution Governance does not replace the existing umbrella-wave source
contract. The sidecar authoring surface must stay thin and write directly to:
- `odylith/radar/source/programs/<umbrella-id>.execution-waves.v1.json`

The ergonomic goal is direct CLI authoring for coding agents, not a parallel
program schema.

## Composition
- [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md) supplies
  grounded evidence, bounded packets, and resolved entity context, including
  the compact execution-governance snapshot exported through packet summaries
  with structured turn intake, lane-fenced target resolution, and
  presentation policy.
- [Delivery Intelligence](../delivery-intelligence/CURRENT_SPEC.md) supplies
  shared posture and scope signals.
- [Proof State](../proof-state/CURRENT_SPEC.md) supplies blocker frontier and
  claim-tier truth.
- [Tribunal](../tribunal/CURRENT_SPEC.md) supplies diagnosis when the problem
  is why the posture exists.
- [Subagent Router](../subagent-router/CURRENT_SPEC.md) and
  [Subagent Orchestrator](../subagent-orchestrator/CURRENT_SPEC.md) consume
  execution-governance policy instead of acting as the first policy boundary;
  active re-anchor, wait-state, contradiction, unsafe-closure, and host-serial
  posture must keep delegation or parallel fan-out local or serial.
- [Remediator](../remediator/CURRENT_SPEC.md) compiles bounded correction
  packets, but those packets should still carry execution-governance posture
  and refuse deterministic execution when admissibility is not `admit`.

## What To Change Together
- If execution-contract fields change, update contract types, policy helpers,
  validation synthesis, and affected surfaces together.
- If turn-intake or lane-fenced target-resolution fields change, update the
  context-engine packet/session compaction and the compact surface summaries
  together so consumer fencing and maintainer targeting stay truthful.
- If host-profile fields change, keep them aligned with the host-neutral
  contract established by cross-host runtime work; never smuggle Codex-only
  assumptions into the shared shape.
- If program/wave authoring semantics change, update the CLI sidecar and the
  canonical execution-wave contract together rather than forking behavior.

## Validation Playbook
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_execution_governance.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_program_wave_authoring.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_execution_wave_contract.py tests/unit/runtime/test_execution_wave_view_model.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-04-09: Promoted execution governance into a first-class Registry component so Odylith can turn grounded truth into admissible next-action control, preserve hard user constraints, and keep the shared execution contract host-general across Codex and Claude Code. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072))
- 2026-04-09: Added shared runtime-lane policy and compact surface summaries so packet reads, router or orchestrator guards, shell or Compass posture, and deterministic remediation all consume the same execution-governance snapshot instead of re-deriving local policy. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072))
- 2026-04-10: Expanded the runtime contract so packet summaries can carry structured `turn_context`, lane-fenced `target_resolution`, and `presentation_policy` through the shared execution-governance snapshot. (Plan: [B-082](odylith/radar/radar.html?view=plan&workstream=B-082))
- 2026-04-11: Grew the execution profile ladder to a `(host_family, profile) -> (model, reasoning_effort)` map so Claude delegation resolves to haiku, sonnet, or opus while Codex tuples stay byte-identical, and flipped the host-capability contract to declare `supports_explicit_model_selection=True` for both validated host families. (Plan: [B-084](odylith/radar/radar.html?view=plan&workstream=B-084), Bug: [CB-103](odylith/casebook/casebook.html?view=bug&bug=CB-103))
