# Execution Engine
Last updated: 2026-04-17

Last updated (UTC): 2026-04-17

## Registry Identity

- Component id: `execution-engine`
- Canonical product name: Execution Engine
- Accepted id: `execution-engine`
- Primary source root: `src/odylith/runtime/execution_engine/`
- Public overview: `docs/EXECUTION_ENGINE.md`
- Core diagrams:
  - `D-002` Context And Agent Execution Stack
  - `D-030` Execution Engine Stack
  - `D-031` Runtime Profile Ladder

The Registry uses `execution-engine` as the only component id. Prior naming
lanes are not supported component aliases for new runtime, benchmark, or
Registry lookup behavior; callers must use `execution-engine` and fail closed
when they cannot resolve that identity.

## Purpose

The Execution Engine is Odylith's constraint-aware execution-control runtime.
It converts a grounded context packet into one machine-readable execution
contract, screens the next intended action for admissibility, derives a single
truthful execution frontier, classifies resource closure, normalizes external
wait state, emits resumable semantic receipts, carries history-rule pressure,
and synthesizes validation obligations before an agent proceeds.

It answers exactly one question:

**Given what the Context Engine says is true and relevant, what is the next
admissible move?**

The answer is not prose advice. The answer is a structured payload made of:

- `ExecutionContract`
- `AdmissibilityDecision`
- `ExecutionFrontier`
- `ResourceClosure`
- `ExternalDependencyState`
- `SemanticReceipt`
- `ValidationMatrix`
- `ContradictionRecord`
- compact summary fields consumed by packets, shell surfaces, router guards,
  orchestrator guards, deterministic remediation, and intervention timing
- compact summary fields consumed by the visible intervention value engine as
  timing, actionability, validation, closure, recover, and visibility-need
  evidence

The runtime is intentionally policy-first. It does not call tools. It does not
mutate files. It does not own the host's transport. It gives the caller a
portable decision surface that can be honored by Codex, Claude Code, shell
commands, governance surfaces, and future host adapters.

## True Role In Odylith

The Execution Engine is the boundary between "we found the right evidence" and
"we are allowed to act." Its true role is to make execution state explicit
enough that an agent cannot honestly skip over ambiguity, user corrections,
active waits, destructive partial scopes, stale proof, or unsupported host
capabilities.

The Context Engine narrows the evidence cone. The Execution Engine governs
motion inside that cone. If the context packet is weak, the Execution Engine
does not pretend the task is ready; it moves the frontier to `explore` or
`recover`, emits re-anchor posture, and denies or defers implementation and
delegation actions until the caller narrows the slice.

The Execution Engine is also the contract-sharing layer. Router,
Orchestrator, Remediator, Compass, shell readouts, and packet summaries should
not each invent their own local rules for whether a slice is safe to delegate,
verify, recover, or resume. They should consume the same compact execution
snapshot and explain the same denial, defer, closure, wait, and validation
state.

## Context Engine Handshake

The Context Engine to Execution Engine handoff is a versioned packet
handshake, currently `v1`. The handoff is built by
`src/odylith/runtime/context_engine/execution_engine_handshake.py` and carried
inside Context Engine packets as `execution_engine_handshake`.

The handshake carries canonical component identity, identity status, packet
kind and state, expanded packet quality, `turn_context`,
`target_resolution`, `presentation_policy`, recommended validation, and route
readiness. Only `execution-engine` is canonical. Missing or noncanonical
component identity remains explicit and must fail closed before route
readiness or benchmark expectation evaluation. There is no alias source and
no compatibility translation for historical execution component ids.

The Execution Engine consumes the packet plus handshake once, emits one
compact snapshot, and allows packet summaries or surface summaries to reuse
that snapshot instead of rebuilding policy state. Reuse status, handshake
version, snapshot duration, runtime-contract token estimate, handshake token
estimate, snapshot token estimate, and total payload token estimate travel in
the compact summary as diagnostic fields.

## Scope

### The Execution Engine Owns

- host-general execution contracts for substantive Odylith sessions
- host profile detection and host-capability shaping
- hard-constraint promotion from user corrections and inline instructions
- allowed and forbidden move sets for the active contract
- admissibility decisions with `admit`, `deny`, and `defer` outcomes
- nearest admissible alternatives for denied or deferred actions
- re-anchor triggers when the evidence cone is no longer trustworthy
- execution-mode posture: `explore`, `implement`, `verify`, `recover`
- append-only execution event streams
- frontier derivation from event streams
- active blocker and truthful next-move carry-through
- resource-closure classification across path, workstream, release, test, and
  generated-surface scopes
- destructive-subset blocking for coupled resources
- external dependency normalization for CI, deploy, callback, token refresh,
  approval, and other wait states
- semantic receipts and resume handles
- contradiction records across contract, evidence, instructions, docs, and
  live state
- history-rule normalization from Casebook, packet failure classes, and proof
  memory
- validation-matrix synthesis
- compact execution-engine summaries for runtime surfaces
- runtime reuse metadata for governed sync sessions
- local and serial lane guards for delegation and parallel fan-out
- thin execution-wave authoring hooks that write the canonical wave contract

### The Execution Engine Does Not Own

- repo truth retrieval or packet compilation; that is
  [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md)
- authoritative markdown or JSON truth; those live in Radar, technical plans,
  Casebook, Registry, Atlas, and source files
- scope synthesis and operator readout posture by itself; that belongs to
  [Delivery Intelligence](../delivery-intelligence/CURRENT_SPEC.md)
- live blocker identity and claim-tier proof by itself; that belongs to
  [Proof State](../proof-state/CURRENT_SPEC.md)
- diagnosis of why the current posture exists; that belongs to
  [Tribunal](../tribunal/CURRENT_SPEC.md)
- friendly observation/proposal rendering; that belongs to
  [Governance Intervention Engine](../governance-intervention-engine/CURRENT_SPEC.md)
- visible signal selection. Execution Engine snapshots can influence
  materiality, actionability, timing relevance, and recover posture, but the
  proposition value engine owns relevance scoring and chat-visible selection.
- delegated-worker transport; that belongs to
  [Subagent Router](../subagent-router/CURRENT_SPEC.md), host adapters, and
  [Subagent Orchestrator](../subagent-orchestrator/CURRENT_SPEC.md)
- deterministic correction-packet compilation; that belongs to
  [Remediator](../remediator/CURRENT_SPEC.md)
- actual tool invocation, command execution, edits, staging, commits, pushes,
  or PR creation

## Execution Boundary

The Execution Engine is a policy engine, not an operating-system sandbox and
not a mandatory tool firewall. It can only govern an action when the caller
routes the planned action through its contract or consumes an execution
snapshot produced from a packet.

Current enforcement is therefore strongest at these integration points:

- Context Engine packet summaries and context dossiers
- bootstrap and session packets
- governance-slice packets
- shell, Compass, and dashboard compact summaries
- Subagent Router and Orchestrator delegation guards
- Remediator deterministic-execution checks
- program and execution-wave authoring helpers
- tests that exercise policy, lane guards, runtime snapshots, and packet
  carry-through

It is not currently a universal interceptor for every raw host tool call. A
human or host agent can still bypass it by directly running a shell command or
editing a file without first consuming the execution snapshot. Product work
that claims "every action is screened" must either stay within the integrated
call paths above or add a host adapter that makes this policy layer mandatory
for that action class.

## Runtime Architecture

### `contract.py`

Defines the canonical dataclasses and payload shapes. This file is the schema
center of the component and should stay small, deterministic, and
serialization-friendly.

Important types:

- `ExecutionHostProfile`
- `ExecutionContract`
- `HardConstraint`
- `ExecutionEvent`
- `AdmissibilityDecision`
- `ExecutionFrontier`
- `ResourceClosure`
- `ExternalDependencyState`
- `SemanticReceipt`
- `ResumeHandle`
- `ValidationMatrix`
- `ContradictionRecord`
- `TurnContext`
- `TargetResolution`
- `TurnPresentationPolicy`

### `policy.py`

Evaluates whether a proposed action is admissible under the active contract.
It promotes user corrections into `HardConstraint` records, denies forbidden
moves, defers mutation while contradictions or waits are live, blocks
delegation on unsupported hosts, blocks side exploration during verify or
recover mode, and emits pressure signals such as contradiction pressure,
closure pressure, wait pressure, repeated rediscovery, repeated denial, and
off-contract pressure.

The policy layer must return a nearest admissible alternative whenever a
caller can reasonably recover without guessing. Examples include `re_anchor`,
`reduce_scope_to_contract`, `resume.external_dependency`,
`verify_current_frontier`, and `main_thread_followup`.

### `frontier.py`

Derives one `ExecutionFrontier` from an append-only event stream. It keeps:

- current phase
- last successful phase
- active blocker
- in-flight external ids
- resume handles
- truthful next move
- execution mode

If no event supplies a next move, frontier derivation falls back safely:
recover active blocker, continue current phase, or re-anchor.

### `event_stream.py`

Builds the normalized event stream. Contradictions, history-rule pressure,
unsafe resource closure, active external waits, context pressure, and the
admissibility decision all become typed `ExecutionEvent` rows. This prevents
surface-local heuristics from inventing inconsistent explanations.

Context-pressure events must precede the final admissibility event so high or
critical context pressure can influence frontier interpretation before the
decision is summarized.

### `history_rules.py`

Canonicalizes carried failure classes into executable preflight blockers. This
turns Casebook memory, known packet failures, and proof history into current
execution pressure instead of leaving them as passive notes.

Examples of normalized rules include:

- `contradiction_blocked_preflight`
- `user_correction_requires_promotion`
- `lane_drift_preflight`
- `repeated_rediscovery_detected`
- `destructive_subset_blocked`

### `resource_closure.py`

Classifies requested scope as:

- `safe`
- `incomplete`
- `destructive`

The closure engine uses dependency graphs, requested resources, missing
dependencies, destructive overlap, closure domains, and closure members so the
caller can explain why a partial edit, partial release, partial generated
surface update, or partial test matrix is unsafe.

### `receipts.py`

Normalizes external dependency state and emits semantic receipts. A receipt
records:

- action
- scope fingerprint
- causal parent
- external dependency state
- resume token
- resume strategy
- expected next states

Receipts default to resume-by-default when a dependency is live. The engine
should reattach to an in-flight CI, deploy, callback, approval, or token
refresh instead of starting a parallel branch that loses state.

### `validation.py`

Synthesizes the minimum validation matrix from the execution contract,
resource closure, and external dependency state. Validation is not a free-form
afterthought; it is part of the governed next-action contract.

Validation archetypes include ordinary status checks, test or command plans,
verification-first posture, recovery-first posture, and external-wait resume
posture. The matrix also records what the requirement was derived from:
contract, closure, wait state, strict gate commands, governed-surface sync,
or proof pressure.

### `contradictions.py`

Detects contradictions across the contract, intended action, user
instructions, docs, and live state. Blocking contradictions must force
re-anchor or defer before mutation or delegation.

Contradiction detection should favor explicit blocking records over buried
warnings. A future caller should be able to inspect the snapshot and identify
which claim blocked execution.

### `sync_runtime_contract.py`

Adds runtime provenance for governed sync. Execution Engine snapshots
built inside an active sync session must carry reuse scope and sync
generation so surfaces can say whether they reused active governed state or
built a standalone packet snapshot.

### `runtime_surface_governance.py`

Builds the compact execution-engine snapshot from a Context Engine packet.
It is the main integration adapter between packet truth and execution policy.
It:

- extracts `turn_context`, `target_resolution`, and `presentation_policy`
- normalizes proof state and external dependency state
- detects the host profile
- infers execution mode
- builds the execution contract
- promotes inline user instructions
- detects contradictions
- classifies closure
- synthesizes validation
- emits receipts
- evaluates primary and nearby action admissibility
- derives the frontier
- emits compact summary fields for surfaces and guards

This adapter is intentionally deterministic and no-op quiet. Adding a field to
the snapshot means updating compact summaries and affected surface tests
together.

### Context Engine handshake helper

`src/odylith/runtime/context_engine/execution_engine_handshake.py` is the
Context Engine-owned adapter that normalizes the handshake, attaches it to
packets, builds the compact Execution Engine snapshot, and reuses an existing
compact snapshot when the packet already carries one.

The helper is deliberately outside the oversized Context Engine store and the
oversized benchmark runner. Runtime surfaces should call the helper or consume
the compact snapshot it produced; they should not rebuild local execution
posture from packet fragments.

### `runtime_lane_policy.py`

Provides local guards for delegation and parallel fan-out. The guards consume
compact execution-engine summaries and block delegation or parallelism
when the slice needs re-anchor, has contradictions, is waiting on an external
dependency, is on a verify or recover critical path, lacks writable consumer
targets, has destructive or incomplete closure, or is running on a host that
cannot support the requested coordination safely.

## Execution Pipeline

1. Receive a grounded packet and `execution_engine_handshake` from the Context Engine.
2. Treat `component_id=execution-engine` as the canonical engine identity and
   keep target component identity in `target_component_*` fields.
3. Fail closed before stale snapshot reuse or expensive runtime expansion when
   a target component explicitly uses a historical execution id such as
   `execution-governance`.
4. Extract packet kind, route readiness, full-scan posture, selected paths,
   workstream, proof state, recommended tests, recommended commands, and
   routing handoff.
5. Preserve structured turn intake as `TurnContext`.
6. Preserve lane-fenced writable and diagnostic target state as
   `TargetResolution`.
7. Preserve presentation hints as `TurnPresentationPolicy`.
8. Detect the host as an `ExecutionHostProfile`.
9. Infer execution mode: `explore`, `implement`, `verify`, or `recover`.
10. Build the `ExecutionContract`.
11. Promote inline user instructions into hard constraints.
12. Detect contradictions.
13. Infer the resource dependency graph and classify closure.
14. Normalize external dependency state.
15. Synthesize validation obligations.
16. Emit a semantic receipt and resume handle.
17. Evaluate admissibility for the primary next action.
18. Collect history-rule pressure.
19. Build the append-only event stream.
20. Derive the execution frontier.
21. Re-evaluate admissibility with the derived frontier.
22. Evaluate nearby denial actions so surfaces can explain alternatives.
23. Build sync-runtime provenance.
24. Emit the full snapshot and compact summary fields.

## Execution Modes

### `explore`

The current packet is not ready for implementation. The caller should narrow
scope, inspect the current frontier, or re-anchor. Implementation and
delegation are denied when route readiness is false or full scan is
recommended.

### `implement`

The packet is route-ready and the closure posture is safe enough to make
bounded changes. Implementation is admissible only inside the target scope and
subject to all hard constraints, contradictions, waits, and host capability
checks.

### `verify`

The critical path is validation. Side exploration and delegated fan-out are
blocked by default because they risk hiding the actual frontier. The caller
should run the selected validation matrix or inspect the current frontier.

### `recover`

The critical path is blocker recovery. Mutation, broad rediscovery, and
delegated fan-out are blocked until the active blocker advances. External
waits should be resumed through the existing receipt when possible.

## Admissibility Semantics

Every screened action returns one of:

- `admit`: the action satisfies the contract and current frontier
- `deny`: the action violates contract, hard constraint, mode, closure, or
  host capability state
- `defer`: the action may be valid later, but the active blocker, wait,
  contradiction, or history rule must be handled first

Denied and deferred actions should carry:

- violated preconditions
- rationale
- nearest admissible alternative
- re-anchor requirement when needed
- host hints
- pressure signals

The caller must treat `deny` and `defer` as execution blockers, not as
decorative warnings.

## Host Profile Contract

The base execution policy is host-general. Codex, Claude Code, and future
hosts should share the same contract, admissibility outcomes, closure
classification, frontier derivation, and validation synthesis.

Host-specific behavior is additive and capability-gated through
`ExecutionHostProfile`.

Important fields:

- `host_family`
- `host_display_name`
- `model_family`
- `model_name`
- `delegation_style`
- `supports_native_spawn`
- `supports_local_structured_reasoning`
- `supports_explicit_model_selection`
- `supports_interrupt`
- `supports_artifact_paths`
- `execution_hints`

Validated host families:

- Codex uses `routed_spawn` and supports native spawn, interrupt, artifact
  paths, structured local reasoning, and explicit model selection.
- Claude Code uses `task_tool_subagents`, supports native spawn and explicit
  model selection, and does not currently advertise interrupt or artifact-path
  support through this contract.
- Unknown hosts fail closed with `delegation_style="none"` and
  `unknown_host_fail_closed` hints.

## Runtime Profile Ladder

The semantic profile ladder lives in
`src/odylith/runtime/common/agent_runtime_contract.py`.

Profiles are semantic:

- `analysis_medium`
- `analysis_high`
- `fast_worker`
- `write_medium`
- `write_high`
- `frontier_high`
- `frontier_xhigh`

The profile-to-model table carries a host-family axis. Codex and Claude can
resolve the same semantic profile to different concrete model and reasoning
tuples without redefining the execution contract. A validated host must never
return an empty model for a supported profile.

## Consumer And Maintainer Lane Fencing

The Execution Engine consumes `TargetResolution` from the Context Engine so it
can distinguish diagnostic anchors from writable targets.

Consumer lane packets may contain useful diagnostic anchors that point into
Odylith-owned files, screenshots, surface evidence, or installed runtime
state. Those anchors are not automatically writable targets. If a consumer
lane has no writable consumer targets and requires more consumer context,
delegation and parallel fan-out must remain blocked until the slice narrows to
admissible repo-owned paths or produces maintainer-ready feedback.

Maintainer mode in the Odylith product repo can keep the same packet and
execution pipeline while allowing Odylith-owned targets to become writable
when lane policy permits mutations.

## Sync And Surface Contract

Compact packet, shell, Compass, Registry, router, orchestrator, and
remediator summaries must read the same execution-engine snapshot instead
of deriving local policy state independently.

Summary fields include:

- `execution_engine_present`
- `execution_engine_objective`
- `execution_engine_authoritative_lane`
- `execution_engine_outcome`
- `execution_engine_requires_reanchor`
- `execution_engine_mode`
- `execution_engine_next_move`
- `execution_engine_blocker`
- `execution_engine_closure`
- `execution_engine_wait_status`
- `execution_engine_resume_token`
- `execution_engine_validation_archetype`
- `execution_engine_validation_derived_from`
- `execution_engine_contradiction_count`
- `execution_engine_history_rule_count`
- `execution_engine_pressure_signals`
- `execution_engine_nearby_denial_actions`
- `execution_engine_host_family`
- `execution_engine_host_delegation_style`
- `execution_engine_host_supports_native_spawn`
- `execution_engine_host_supports_interrupt`
- `execution_engine_host_supports_artifact_paths`
- `execution_engine_component_id`
- `execution_engine_canonical_component_id`
- `execution_engine_identity_status`
- `execution_engine_target_component_id`
- `execution_engine_target_component_ids`
- `execution_engine_target_component_status`
- `execution_engine_target_lane`
- `execution_engine_has_writable_targets`
- `execution_engine_requires_more_consumer_context`
- `execution_engine_commentary_mode`
- `execution_engine_runtime_reuse_scope`
- `execution_engine_runtime_invalidated_by_step`
- `execution_engine_context_pressure`
- `execution_engine_snapshot_reuse_status`
- `execution_engine_handshake_version`
- `execution_engine_snapshot_duration_ms`
- `execution_engine_snapshot_estimated_tokens`
- `execution_engine_runtime_contract_estimated_tokens`
- `execution_engine_handshake_estimated_tokens`
- `execution_engine_total_payload_estimated_tokens`

New fields must be compact, deterministic, and no-op quiet. Surface refreshes
must not churn when the logical execution snapshot has not changed.

## Delegation And Parallelism Guard Contract

Router and Orchestrator may shape delegated work, but they must not act as the
first policy boundary. Before delegation or parallel fan-out, callers should
run the compact summary through:

- `delegation_guard(summary)`
- `parallelism_guard(summary)`

The guards block when:

- the snapshot carries a noncanonical or blocked Execution Engine identity
- the snapshot was invalidated by a runtime step
- re-anchor is required
- live contradictions exist
- promoted user constraints are missing
- carried history rules match known failure classes
- an external dependency is still active
- consumer lane lacks writable targets
- execution mode is `verify` or `recover`
- closure is `incomplete` or `destructive`
- host capability state cannot support safe delegated execution
- the current admissibility outcome is `deny` or `defer`

The guard reason must be human-readable and should point at the truthful next
move instead of merely saying "blocked."

## Program And Wave Authoring Sidecar

The Execution Engine includes a thin authoring sidecar for execution-wave
programs, but it does not replace the canonical umbrella-wave source contract.
The write surface remains:

- `odylith/radar/source/programs/<umbrella-id>.execution-waves.v1.json`

The sidecar exists so coding agents can author waves against the same
execution-policy assumptions used by the rest of Odylith. It must not create a
parallel program schema.

## Invariants

- Context Engine owns grounding; Execution Engine owns admissibility.
- The Context Engine to Execution Engine handoff uses canonical
  `execution-engine` identity only.
- Execution summaries consume the shared compact snapshot instead of
  re-deriving local policy state.
- The base contract is host-general first.
- Host-specific behavior is additive and capability-gated.
- Hard user constraints are promoted into structured records before execution.
- A denied or deferred action must carry a recovery path when one exists.
- A live external dependency should be resumed by default, not restarted.
- A blocking contradiction prevents mutation and delegation.
- Verify and recover modes are critical-path modes.
- Incomplete or destructive closure blocks mutation and fan-out.
- Consumer diagnostic anchors are not writable targets.
- Compact summaries must preserve real reasons, not only counts.
- Runtime sync reuse metadata must travel with snapshots built during sync.
- Snapshot reuse and cost fields are diagnostic, deterministic, and no-op
  quiet.
- Intervention rendering may consume execution posture but must not redefine
  or bypass it.
- The engine must stay useful without optional host features; unsupported
  capability state should fail closed.

## Failure Modes

### False Admit

The engine admits implementation or delegation while scope is ambiguous,
closure is unsafe, a user constraint is unpromoted, or an external wait is
active. This is the highest-risk class because it lets agent motion outrun
truth.

Required response: add a failing test that reproduces the admission, harden
policy or summary extraction, and confirm the nearest admissible alternative.

### Stale Frontier

The event stream or compact summary reports a next move that no longer matches
proof state, sync state, or external dependency state.

Required response: inspect `runtime_surface_governance.py`,
`frontier.py`, `sync_runtime_contract.py`, and the packet source that supplied
proof state.

### Surface Fork

Shell, Compass, packet, router, or remediator code explains execution posture
by re-deriving local policy instead of reading the shared summary.

Required response: replace surface-local policy with
`summary_fields_from_execution_engine` or the compact snapshot and add
surface regression coverage.

### Host Drift

Codex and Claude Code diverge in base policy semantics instead of only host
capability hints.

Required response: fix the shared contract first, then adjust host profile
fields or the runtime profile ladder.

### Bypass By Direct Tool Call

A host path directly invokes tools without consuming the execution snapshot.

Required response: decide whether that host path is intentionally outside the
Execution Engine boundary. If not, add an adapter or preflight that routes the
planned action through admissibility before execution.

## What To Change Together

- Contract type changes:
  update `contract.py`, snapshot compaction, summary fields, tests, and docs.
- Policy rule changes:
  update `policy.py`, nearby-denial expectations, lane guards, and regression
  tests.
- Frontier changes:
  update event stream ordering, frontier derivation, compact summary fields,
  and surface readouts.
- Host profile changes:
  update `ExecutionHostProfile`, runtime profile ladder, Codex and Claude
  contract tests, and related docs.
- Turn-intake or target-resolution changes:
  update Context Engine packet assembly, bootstrap/session compaction,
  `runtime_surface_governance.py`, and consumer-lane tests.
- External dependency changes:
  update receipt normalization, wait-state handling, resume tokens, and proof
  state integration.
- Closure-domain changes:
  update dependency graph inference, closure classification, validation
  synthesis, lane guards, and destructive-subset tests.
- Intervention posture changes:
  update Governance Intervention Engine consumers without moving rendering
  ownership into the Execution Engine.
- Program/wave sidecar changes:
  update CLI sidecar behavior and the canonical execution-wave contract
  together.

## Validation Playbook

Focused runtime validation:

- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_execution_engine.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_program_wave_authoring.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_execution_wave_contract.py tests/unit/runtime/test_execution_wave_view_model.py`

CLI and integration validation:

- `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py`
- `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_context_engine_turn_intake.py`

Registry validation:

- `odylith validate registry --repo-root .`
- `odylith registry refresh --repo-root .`

For changes that alter packet integration or host behavior, also run the
relevant Context Engine packet tests and host-runtime contract tests.

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-04-16 · Implementation:** Hardened Context Engine to Execution Engine alignment with canonical identity propagation, identity-first guard blocking, benchmark identity gates, and refreshed release-proof surfaces.
  - Scope: B-099
  - Evidence: src/odylith/runtime/context_engine/execution_engine_handshake.py, src/odylith/runtime/execution_engine/runtime_lane_policy.py
- **2026-04-16 · Implementation:** Hard-cut Context Engine and Execution Engine alignment Wave 1 to canonical execution-engine identity; focused execution tests, broader runtime benchmark tests, registry/backlog validators, sync check, Atlas freshness, and diff check pass.
  - Scope: B-099, B-100
  - Evidence: odylith/radar/source/programs/B-099.execution-waves.v1.json, odylith/registry/source/components/execution-engine/CURRENT_SPEC.md +2 more
<!-- registry-requirements:end -->

## Feature History

- 2026-04-09: Promoted execution engine into a first-class Registry component so Odylith can turn grounded truth into admissible next-action control, preserve hard user constraints, and keep the shared execution contract host-general across Codex and Claude Code. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072))
- 2026-04-09: Added shared runtime-lane policy and compact surface summaries so packet reads, router or orchestrator guards, shell or Compass posture, and deterministic remediation all consume the same execution-engine snapshot instead of re-deriving local policy. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072))
- 2026-04-10: Expanded the runtime contract so packet summaries can carry structured `turn_context`, lane-fenced `target_resolution`, and `presentation_policy` through the shared execution-engine snapshot. (Plan: [B-082](odylith/radar/radar.html?view=plan&workstream=B-082))
- 2026-04-11: Grew the execution profile ladder to a `(host_family, profile) -> (model, reasoning_effort)` map so Claude delegation resolves to haiku, sonnet, or opus while Codex tuples stay byte-identical, and flipped the host-capability contract to declare `supports_explicit_model_selection=True` for both validated host families. (Plan: [B-084](odylith/radar/radar.html?view=plan&workstream=B-084), Bug: [CB-103](odylith/casebook/casebook.html?view=bug&bug=CB-103))
- 2026-04-12: Hardened the core engine with inline user-correction promotion, richer closure domains, typed pressure signals, sync-aware runtime provenance, and shared execution-event shaping so packet summaries, shell or Compass posture, and sync-backed surfaces all explain the same admissibility state. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072), Plan: [B-091](odylith/radar/radar.html?view=plan&workstream=B-091))
- 2026-04-13: Optimized the execution engine for Claude Code with host-specific capability fields, Claude presentation defaults, context-pressure events, artifact-path lane guards, and two Claude-specific history-rule failure classes. Wired execution engine into all three delivery paths that previously bypassed it: the non-hot-path bootstrap compactor, the hot-path bootstrap delivery, and the context dossier delivery. 49 tests, 385 regression pass. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072))
- 2026-04-14: Clarified Execution Engine as an intervention input rather than an intervention renderer: it now supplies shared admissibility and urgency posture to the new conversation-observation engine without owning the human voice or proposal UX. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-16: Cut the Registry and benchmark contract over to `execution-engine` as the only accepted component id, removed compatibility aliases, and kept the detailed runtime contract for admissibility, frontier, closure, receipts, validation, host profile, and guard behavior. (Plan: [B-100](odylith/radar/radar.html?view=plan&workstream=B-100))
- 2026-04-16: Added handshake `v1` and compact snapshot reuse across Context Engine packet builders and packet summaries; added snapshot duration plus token-cost diagnostics to the execution benchmark family. (Plan: [B-101](odylith/radar/radar.html?view=plan&workstream=B-101), Plan: [B-103](odylith/radar/radar.html?view=plan&workstream=B-103))
- 2026-04-16: Added paired Codex and Claude semantic parity proof and Claude execution benchmark scenarios for route-ready and wait/resume lanes while keeping host differences behind `ExecutionHostProfile`. (Plan: [B-102](odylith/radar/radar.html?view=plan&workstream=B-102))
