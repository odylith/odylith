# Subagent Router
Last updated: 2026-04-09


Last updated (UTC): 2026-04-09

## Purpose
Subagent Router is Odylith's bounded leaf-routing engine. It takes one already
scoped task and decides whether the work should remain in the main thread or be
delegated to one subagent, with an explicit model, reasoning-effort tier,
agent role, lifecycle contract, and host-tool payload.

This routed profile ladder applies across substantive grounded consumer-lane
work and both Odylith product-repo maintainer postures: pinned dogfood and
detached `source-local` maintainer dev. Native spawn remains capability-gated
by the resolved host runtime, with Codex as the currently validated
native-spawn host.

## Scope And Non-Goals
### The router owns
- Single-task route classification.
- Hard refusal gates for unsafe or under-scoped delegation.
- Selection across the supported profile ladder.
- Host-native spawn and closeout payload generation.
- Local-only adaptive tuning from recorded outcomes.

### The router does not own
- Prompt decomposition across multiple leaves. That belongs to the
  orchestrator.
- Repo grounding. It consumes bounded context signals rather than compiling
  them.
- Spawning agents directly. It emits a decision contract for the caller.
- Core admissibility policy. Execution Engine decides whether a next move
  is allowed before routing chooses the best delegated profile, and the router
  must fail closed when the governed frontier says the truthful next move is
  re-anchor, local recovery, or waiting on an external dependency.

## Developer Mental Model
- The router is the leaf authority. If a task has already been decomposed, the
  router is the component that decides whether that leaf is worth delegating.
- Hard gates beat soft scoring.
- `gpt-5.4` `xhigh` is a gated tier, not a default outcome.
- Tuning stored under `.odylith/` may bias future soft choices, but it cannot
  rewrite safety policy.
- Consumer-facing `why`, `explanation_lines`, and related human-readable route
  notes must stay task-first. They should describe scope, readiness, and
  blockers without narrating Odylith control-plane internals unless a literal
  command or runtime boundary matters.
- If a host names Odylith directly in the final handoff, keep that outside the
  route explanation stream and limit it to one short `Odylith Assist:` line
  backed by concrete observed counts, measured deltas, or validation outcomes.
  Prefer `**Odylith Assist:**` when Markdown formatting is available. Lead
  with the user win, not Odylith mechanics, link updated governance IDs inline
  only when they actually changed, name affected governance-contract IDs from
  bounded request or packet truth when no governed file moved, and frame the
  edge against `odylith_off` or the broader unguided path when the evidence
  supports it. Keep it crisp, authentic, clear, simple, insightful, soulful,
  friendly, free-flowing, human, and factual.

## Public Command Surface
Public entrypoint: `odylith subagent-router`

- `route`
  Parse one route request and emit one `RoutingDecision`.
- `escalate`
  Given an earlier decision and an explicit failure or ambiguity outcome,
  choose the next route profile.
- `record-outcome`
  Persist adaptive feedback into local tuning state.
- `show-tuning`
  Print the current local tuning state.

The CLI accepts inline JSON or `--input-file`/`--decision-file`/`--outcome-file`
payloads and can optionally mirror audit rows into
`odylith/compass/runtime/agent-stream.v1.jsonl`, while retaining read
compatibility for legacy `codex-stream.v1.jsonl` consumers during migration.

## Persistent State
- `.odylith/subagent_router/tuning.v1.json`
  Local profile bias, family bias, outcome counts, and applied outcome keys.
- `odylith/compass/runtime/agent-stream.v1.jsonl`
  Canonical optional route audit stream shared with Compass runtime posture,
  with legacy reader support for `codex-stream.v1.jsonl`.

## Core Types
### `RouteRequest`
Normalized leaf input before routing. Important fields:
- `prompt`
- `acceptance_criteria`
- `allowed_paths`
- `workstreams`
- `artifacts`
- `validation_commands`
- `components`
- `phase`
- `task_kind`
- `needs_write`
- `latency_sensitive`
- `correctness_critical`
- `requires_multi_agent_adjudication`
- `evolving_context_required`
- `evidence_cone_grounded`
- `accuracy_preference`
- `context_signals`

### `TaskAssessment`
The router's normalized feature model. It records:
- task family and phase
- whether the task is a feature implementation or mixed-phase slice
- ambiguity, blast radius, context breadth, coordination cost, and
  reversibility risk
- mechanicalness and write-scope clarity
- acceptance, artifact, and validation clarity
- latency pressure and requested depth
- accuracy bias and base confidence
- semantic signals, hard gate hits, and summarized context signals

### `RoutingDecision`
The output contract consumed by host code. It includes:
- `delegate`
- selected `profile`, `model`, and `reasoning_effort`
- `agent_role`
- reuse, waiting, idle-timeout, and close-after-result policy
- `why`, `explanation_lines`, and `scorecard`
- `escalation_profile`
- `hard_gate_hits`
- `host_tool_contract`
- `native_spawn_payload`
- `spawn_overrides`, `spawn_agent_overrides`, `close_agent_overrides`
- `spawn_task_message` and `spawn_contract_lines`
- `task_class_*` metadata
- `odylith_execution_profile`

### `RouteOutcome`
Recorded execution result used for escalation or tuning:
- accepted
- blocked
- ambiguous
- artifact_missing
- quality_too_weak
- escalated
- broader_coordination
- notes and outcome id

## Profile Ladder
The supported ordered profile ladder across native-spawn-capable hosts is:
- `main_thread`
  No delegation.
- `analysis_medium`
  `gpt-5.4-mini`, `medium`.
- `analysis_high`
  `gpt-5.4-mini`, `high`.
- `fast_worker`
  `gpt-5.3-codex-spark`, `medium`.
- `write_medium`
  `gpt-5.3-codex`, `medium`.
- `write_high`
  `gpt-5.3-codex`, `high`.
- `frontier_high`
  `gpt-5.4`, `high`.
- `frontier_xhigh`
  `gpt-5.4`, `xhigh`, gated.

Legacy ids `mini_*`, `spark_medium`, `codex_*`, and `gpt54_*` remain accepted
as read-compatibility aliases for one migration window, but new decisions and
docs should emit the neutral canonical ids above.

## Task-Family Policy Baselines
The router maintains explicit baseline policy per task family:
- `mechanical_patch`
  Defaults to `fast_worker` worker.
- `bounded_bugfix`
  Defaults to `write_medium` worker.
- `bounded_feature`
  Defaults to `write_high` worker.
- `analysis_review`
  Defaults to `analysis_high` explorer.
- `critical_change`
  Defaults to `frontier_high` worker.
- `coordination_heavy`
  Defaults to `main_thread`.

These are baselines, not guaranteed outcomes. Hard gates and backstops can
still keep a task local or promote it upward.

## Signal Extraction And Inference
The router combines three kinds of signals:
- Prompt semantics:
  keywords about writes, ambiguity, risk, reversibility, latency, validation,
  coordination, and task breadth.
- Explicit request structure:
  allowed paths, validation commands, artifacts, acceptance criteria, task
  flags, and correctness posture.
- Context signals:
  extracted from keys such as `routing_handoff`, `context_packet`,
  `evidence_pack`, `optimization_snapshot`, `architecture_audit`,
  `validation_bundle`, `governance_obligations`, `surface_refs`,
  `diagram_watch_gaps`, and compact `execution_engine_*` summary fields.

Execution Engine summary fields are first-class hard-gate inputs. Canonical
Execution Engine identity, re-anchor pressure, live contradictions, semantic
wait state, critical-path verify or recover modes, unsafe closure, and
host-serial posture must all be allowed to keep a leaf local before any
profile ladder scoring runs.

The router also enforces implied write-surface rules. For example, prompts that
mention tests, docs, governance artifacts, or contracts must declare path scope
that covers the corresponding prefixes.

## Decision Pipeline
1. Parse a `RouteRequest`.
2. Normalize strings, booleans, lists, and context signals.
3. Infer task family and build a `TaskAssessment`.
4. Apply hard gates for local-only or rescope-required conditions.
5. Score the available delegated profiles.
6. Apply task-family baseline policy, safety backstops, confidence backstops,
   and gated escalation rules.
7. Build host-facing lifecycle payloads:
   agent role, spawn overrides, runtime banners, idle policy, termination
   expectations, and reuse hints.
8. Emit one `RoutingDecision`.
9. Later, consume `RouteOutcome` via `record-outcome` and optionally
   `escalate` to tune or retry safely.

## Hard Gates And Guardrails
Typical reasons a task stays local or is forced to rescope include:
- trivial explanation or synthesis work where delegation would add overhead
- open-ended coordination-heavy or adjudication-heavy work
- critical or hard-to-reverse changes without a grounded evidence cone
- missing write scope for prompts that clearly imply edits
- implied write surfaces not covered by `allowed_paths`

Important guardrails:
- Hard gates override soft scoring.
- `frontier_xhigh` is not a default winner and should appear only after explicit
  risk or escalation logic unlocks it.
- Execution-governance defer or deny posture beats route-readiness scoring.
- The current routed Codex host-tool contract still supports only native
  `spawn_agent` agent types: `default`, `explorer`, and `worker`.
- Odylith may also ship repo-scoped Codex CLI custom project agents under
  `.codex/agents/*.toml`, but those are project-native Codex assets rather than
  router-selectable `spawn_agent` types until the host integration proves
  named-agent selection end to end.

## Tuning Model
Tuning is local-only and bias-bounded:
- `profile_bias`
  Soft global bias per delegated profile.
- `family_profile_bias`
  Soft bias per task family and profile.
- `outcome_counts` and `family_outcome_counts`
  Local execution history.
- `applied_outcome_keys`
  Deduplication guard so repeated outcome replays do not over-tune the state.

Tuning can influence close calls, but it cannot bypass hard safety rules.

## Host Integration Contract
The router emits structured payloads instead of free-form advice:
- `native_spawn_payload`
  Model, reasoning effort, agent role, and other host-tool-ready fields.
- `host_tool_contract`
  Declarative handoff the caller can inspect or log.
- `spawn_contract_lines`
  Human-readable delegation contract.
- `runtime_banner_lines`
  Short UI/runtime notes about role, termination expectations, and host limits.
- `close_agent_overrides`
  Closeout policy for delegated leaves.

This keeps routing policy centralized in code rather than spreading it across
prompt templates.

## What To Change Together
- New task family:
  update classification logic, add a `TaskClassPolicy`, and ensure explanation
  text and score/backstop logic agree.
- New context signal:
  teach `_extract_context_signals_payload(...)` and the downstream scoring logic
  how to interpret it.
- New host capability:
  update both the lifecycle payloads and the explanation/runtime banner logic.
- New guardrail:
  add it as an explicit hard gate or backstop, not as a hidden score tweak.

## Debugging Checklist
- `odylith subagent-router route --repo-root . --input-file route.json --json`
  Inspect the raw `assessment`, `scorecard`, and `explanation_lines`.
- `odylith subagent-router escalate --repo-root . --decision-file decision.json --outcome-file outcome.json --json`
  Confirm the escalation path.
- `odylith subagent-router show-tuning --repo-root . --json`
  Check whether local tuning is biasing borderline choices.
- Inspect `hard_gate_hits`, `manual_review_recommended`, and
  `rescope_required` before assuming the selected model tier is the problem.

## Validation Playbook
### Routing
- `odylith subagent-router route --repo-root . --input-file route.json --json`
- `odylith subagent-router escalate --repo-root . --decision-file decision.json --outcome-file outcome.json --json`
- `odylith subagent-router record-outcome --repo-root . --decision-file decision.json --outcome-file outcome.json --json`
- `odylith subagent-router show-tuning --repo-root . --json`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-03-23 · Decision:** Successor created: B-276 reopens B-275 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md +2 more
- **2026-03-16 · Implementation:** Implemented family-aware adaptive tuning, low-confidence GPT-5.4 promotion, smarter hard gates, and broader-coordination rescope handling in the Subagent Router.
  - Evidence: src/odylith/runtime/orchestration/subagent_router.py
- **2026-03-16 · Decision:** Deepened Subagent Router with task-family assessment, route-confidence backstops, and escalation refusal that can return control to the main thread.
  - Evidence: src/odylith/runtime/orchestration/subagent_router.py
- **2026-03-16 · Implementation:** Implemented the Subagent Router runtime, the thin router skill, the component spec and runbook, and the Atlas routing topology diagrams.
  - Evidence: odylith/atlas/source/catalog/diagrams.v1.json, odylith/registry/source/components/subagent-router/CURRENT_SPEC.md +1 more
- **2026-03-16 · Decision:** keep Subagent Router accuracy-first, hard-gated, and first-class in Registry and Atlas instead of hiding delegation policy in prompt folklore.
  - Evidence: odylith/atlas/source/catalog/diagrams.v1.json, odylith/registry/source/components/subagent-router/CURRENT_SPEC.md +1 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Registered the public router as an Odylith-owned product component with its own spec and governance linkage in the public repo. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-04-02: Fixed the public CLI wrapper so `odylith subagent-router --repo-root . --help` and verbed invocations preserve the documented verb-first contract instead of misrouting `--repo-root` ahead of the router subcommand. (Plan: [B-022](odylith/radar/radar.html?view=plan&workstream=B-022))
- 2026-04-09: Clarified that Subagent Router selects delegated execution profiles only after Execution Engine has screened the next move for admissibility. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072))
