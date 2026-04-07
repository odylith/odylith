# Subagent Orchestrator
Last updated: 2026-03-31


Last updated (UTC): 2026-03-31

## Purpose
Subagent Orchestrator is Odylith's prompt-level decomposition engine. It takes
one grounded prompt and decides whether the work remains local, becomes one
delegated leaf, or expands into a conservative serial or parallel execution
plan with explicit merge barriers.

In Codex, this orchestration contract applies to substantive grounded repo work
across the consumer lane and both Odylith product-repo maintainer postures:
pinned dogfood and detached `source-local` maintainer dev.

## Scope And Non-Goals
### The orchestrator owns
- Prompt decomposition across multiple possible leaves.
- Selection among orchestration modes:
  `local_only`, `single_leaf`, `serial_batch`, and `parallel_batch`.
- Parallel-safety classification.
- Main-thread follow-up retention for work that must not be delegated.
- Decision ledger persistence and closeout tracking.
- Local-only orchestration tuning.

### The orchestrator does not own
- Leaf model/profile selection. Every delegated leaf still goes through the
  Subagent Router.
- Grounding the repo from scratch. It expects bounded context or request
  signals.
- Spawning agents itself. It emits the plan the live agent should execute.

## Developer Mental Model
- The orchestrator sits one level above the router.
- The router answers: "given one leaf, should it be delegated and how?"
- The orchestrator answers: "should this prompt stay whole, or should it be
  split into local work and one or more leaves?"
- The orchestrator is conservative. Parallel fan-out is an optimization, not a
  right.
- Consumer-facing rationale text must stay task-first. Human-readable notes
  should explain scope, readiness, merge burden, or validation pressure
  without narrating Odylith control-plane steps or routine `odylith start`,
  `odylith context`, or `odylith query` commands. Mention Odylith by name
  only when the user explicitly asks for the command, a live blocker requires
  it, or a runtime boundary matters.
- If a host chooses to name Odylith directly in the final handoff, that
  belongs in at most one short `Odylith Assist:` line grounded in concrete
  observed counts, measured deltas, or validation outcomes. Prefer
  `**Odylith Assist:**` when Markdown formatting is available. Lead with the
  user win, not Odylith mechanics, link updated governance ids inline when
  they were actually changed, and frame the edge against `odylith_off` or the
  broader unguided path when the evidence supports it. Keep it crisp,
  authentic, clear, simple, insightful, soulful, friendly, free-flowing,
  human, and factual. It is not part of the orchestrator's mid-task rationale
  stream.

## Public Command Surface
Public entrypoint: `odylith subagent-orchestrator`

- `plan`
  Build an `OrchestrationDecision` for a grounded prompt.
- `record-feedback`
  Persist execution feedback into orchestration-local tuning state.
- `show-tuning`
  Print the current tuning state.
- `show-ledger`
  Show one persisted decision ledger.
- `record-ledger`
  Persist transcript pointers, result handoffs, follow-up state, and closeout
  state for a decision.

The CLI can optionally mirror plan and feedback audit rows into
`odylith/compass/runtime/codex-stream.v1.jsonl`.

## Persistent State
- `.odylith/subagent_orchestrator/tuning.v1.json`
  Local orchestration-mode bias and family-specific feedback.
- `.odylith/subagent_orchestrator/decision-ledgers/`
  One JSON decision ledger per orchestration decision.
- `odylith/compass/runtime/codex-stream.v1.jsonl`
  Optional orchestration audit stream.

## Core Types
### `OrchestrationRequest`
Grounded prompt-level input. Key fields include:
- prompt, acceptance criteria, candidate paths, workstreams, and components
- validation commands
- task kind, phase, and accuracy preference
- repo-work and write intent flags
- correctness, latency, evolving-context, and evidence-grounding posture
- working-tree and session scope
- claimed paths
- `odylith_operation` and `odylith_auto_ground`
- `context_signals`

### `SubtaskSlice`
One delegated leaf emitted by the orchestrator. It includes:
- stable subtask id and prompt
- owned and read path sets
- dependency ids
- deliverables
- explicit owner, goal, expected output, and termination condition
- route result fields copied from the router
- spawn and closeout overrides
- host-tool contract, runtime banners, and native spawn payload
- validation commands

### `MainThreadFollowup`
Explicit work retained locally. It records:
- follow-up id
- scope role and paths
- dependency ids
- owner, goal, deliverables
- why the work must stay local

### `OrchestrationDecision`
Top-level plan. It includes:
- `mode`
- `decision_id`
- whether delegation is used at all
- `parallel_safety`
- `task_family`
- confidence, refusal stage, and rationale
- merge-barrier notes
- execution-contract notes
- local-only reasons and budget notes
- main-thread follow-ups
- delegated subtask slices
- request echo
- inspection artifacts and closeout overrides

### `ExecutionFeedback`
Structured tuning signal after execution:
- accepted
- merge conflict count
- rescope required
- false parallelization
- escalated leaf count
- token efficiency
- notes and feedback id

## Orchestration Modes
- `local_only`
  No delegated leaves are emitted.
- `single_leaf`
  One delegated leaf is emitted and routed.
- `serial_batch`
  Multiple leaves exist, but ordering and merge barriers require serialized
  execution.
- `parallel_batch`
  Multiple leaves may proceed concurrently because their ownership boundaries
  are safely disjoint.

## Parallel Safety Classes
- `read_only_safe`
  Read-only work that can run in parallel without a merge burden.
- `disjoint_write_safe`
  Writes are allowed, but owned paths are disjoint enough for bounded parallel
  execution.
- `serial_ordered`
  Multiple leaves are viable, but the work has ordering constraints.
- `local_only`
  The slice is not safe to fan out.

## Planning Pipeline
1. Parse `OrchestrationRequest`.
2. Normalize path scope, prompt features, working-tree/session signals, and
   context hints.
3. Apply hard local-only gates for trivial prompts, under-scoped critical
   writes, or tightly coupled governance work.
4. Decide whether decomposition is warranted at all.
5. If decomposition is allowed, build candidate subtask slices and local
   follow-ups.
6. Classify parallel safety from owned-path overlap, coupled prefixes, and task
   family.
7. Route every delegated leaf through the Subagent Router.
8. Emit one `OrchestrationDecision`.
9. Persist a decision ledger and later update it with handoff, follow-up, and
   closeout state.

## What Makes A Slice Parallel-Safe
Parallelism is intentionally conservative. The orchestrator requires:
- clearly owned write surfaces
- low coordination burden across leaves
- bounded merge burden
- no shared governance bottleneck that really belongs in the main thread

Paths under tightly coupled prefixes such as `odylith/`, `docs/`,
`contracts/`, `skills/`, and similar governance-heavy trees are usually kept
local or downgraded to serial planning unless the ownership boundary is very
clear.

## Decision Ledger Contract
`build_decision_ledger(...)` persists one structured ledger containing:
- version, decision id, recorded and updated timestamps
- decision status and decision summary
- request summary
- inspection artifacts
- merge barrier notes and execution contract notes
- completion closeout overrides
- main-thread follow-ups
- delegated subtask entries
- ordered event log

Per-subtask ledger state can then track:
- status
- agent id and host thread id
- spawned timestamp
- transcript pointers
- result handoff summary, artifact paths, and validation commands
- follow-up state
- closeout status, closed time, and reason

This ledger is the source of truth for subtask lifecycle and should be updated
instead of inventing ad-hoc state elsewhere.

## Tuning Model
The orchestration tuning state stores:
- `mode_bias`
  Soft bias per orchestration mode.
- `family_mode_bias`
  Soft bias by task family and mode.
- `outcome_counts` and `family_outcome_counts`
  Local execution history.
- `applied_feedback_keys`
  Replay protection.

As with the router, tuning is advisory and cannot override safety gates.

## Integration With The Router
Every delegated `SubtaskSlice` carries router-derived fields such as:
- route profile, model, and reasoning effort
- route agent role
- route task-family policy data
- route spawn contract and host tool contract
- route idle-timeout and waiting policy
- route explanation lines and route confidence

That duplication is intentional. It makes the orchestration decision
self-contained and inspectable without recomputing routing later.

## What To Change Together
- New orchestration mode or safety class:
  update mode selection, tuning defaults, ledger summaries, and Compass audit
  logging together.
- New subtask contract field:
  update both `SubtaskSlice` and the ledger serialization logic.
- New decomposition heuristic:
  update the prompt planner and the merge-barrier notes so the reason for the
  split stays inspectable.
- New closeout behavior:
  update decision-ledger merge logic and closeout recommendation refresh logic
  together.

## Debugging Checklist
- `odylith subagent-orchestrator plan --repo-root . --input-file request.json --json`
  Inspect the emitted mode, subtasks, and main-thread follow-ups.
- `odylith subagent-orchestrator show-ledger --repo-root . --decision-id <id> --json`
  Confirm the persisted lifecycle state.
- `odylith subagent-orchestrator record-ledger --repo-root . --decision-id <id> --update-file update.json --json`
  Exercise closeout and handoff behavior explicitly.
- `odylith subagent-orchestrator show-tuning --repo-root . --json`
  Check whether local tuning is biasing borderline choices.

## Validation Playbook
### Orchestration
- `odylith subagent-orchestrator plan --repo-root . --input-file request.json --json`
- `odylith subagent-orchestrator record-feedback --repo-root . --decision-file decision.json --feedback-file feedback.json --json`
- `odylith subagent-orchestrator show-tuning --repo-root . --json`
- `odylith subagent-orchestrator show-ledger --repo-root . --decision-id <decision-id> --json`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-03-23 · Decision:** Successor created: B-276 reopens B-275 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md +2 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Registered the public orchestrator as an Odylith-owned product component with product-local governance and feature history. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-04-02: Fixed the public CLI wrapper so `odylith subagent-orchestrator --repo-root . --help` and verbed invocations preserve the documented verb-first contract instead of misrouting `--repo-root` ahead of the orchestrator subcommand. (Plan: [B-022](odylith/radar/radar.html?view=plan&workstream=B-022))
