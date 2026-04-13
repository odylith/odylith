# Odylith Operator Instructions

Everything an operator can say to a coding agent in an Odylith-enabled repo,
what happens behind the scenes, and how long it takes.

Odylith works through three layers: **things you say** (natural language
instructions to the agent), **things the agent does** (slash commands and
subagent delegation), and **things that happen automatically** (hooks that fire
on every edit, every session start, every compaction). All three layers share
the same Python codebase and the same execution governance contract.

---

## Layer 1: What You Say to the Agent

These are natural language instructions. The agent translates them into Odylith
CLI calls, context lookups, governance updates, and validation runs. You never
need to know the CLI — just describe what you want.

### Starting and Grounding Work

| Instruction | What happens | Time |
|---|---|---|
| "Fix the bug in the checkout flow" | Agent runs `/odylith-start` to ground the task, matches workstream via LanceDB, builds execution contract, resolves the component, loads the context packet with admissibility decisions | ~2s |
| "Work on B-073" | Agent runs `/odylith-context B-073` to resolve the workstream anchor, loads related entities, delivery scopes, and execution governance | ~5s |
| "What's the state of the repo?" | Agent runs `/odylith-session-brief` to build a Compass-derived summary of active workstreams, next actions, risks, and recent activity | ~2s |
| "What version of Odylith is installed?" | Agent runs `/odylith-version` to show pinned, active, and available versions plus the current posture (consumer vs maintainer, pinned vs source-local) | ~1s |
| "Is Odylith healthy?" | Agent runs `/odylith-doctor` to verify launcher integrity, runtime pinning, project assets, and Compass readiness | ~1.5s |
| "Check if Claude Code is set up right" | Agent runs `/odylith-compatibility` to probe the local Claude CLI, project hooks, settings, and baked modules | ~0.1s |

### Searching and Exploring

| Instruction | What happens | Time |
|---|---|---|
| "Find everything related to execution governance" | Agent runs `/odylith-query "execution governance"` to search LanceDB (exact lookup) + Tantivy (sparse text) across 2,711 compiled documents | ~1.3s |
| "Show me the execution-governance component" | Agent runs `/odylith-context execution-governance` to resolve the component entity with relations, delivery scopes, and governance snapshot | ~5s |
| "What workstreams are active?" | Agent reads the Compass runtime payload from `odylith/compass/runtime/current.v1.json` or runs `/odylith-compass-refresh-wait` to get a fresh view | ~2s cached |
| "Show me the standup brief" | Agent reads the Compass brief or triggers the compass-executive skill to interpret the latest narrated brief | ~0.1s cached |

### Planning and Creating Work

| Instruction | What happens | Time |
|---|---|---|
| "Create a workstream for this" | Agent runs `/odylith-workstream-new` which calls `odylith backlog create --repo-root . --title <title>` to create a new Radar workstream with proper schema | ~0.3s |
| "Plan the implementation" | Agent runs `/odylith-plan` which first grounds via `/odylith-start` or `/odylith-context`, then builds a bounded technical plan under `odylith/technical-plans/` | varies |
| "File a bug for this" | Agent runs `/odylith-case` which searches existing Casebook bugs first (to avoid duplicates), then captures the failure evidence with repro details | varies |
| "Hand this off" | Agent runs `/odylith-handoff` to prepare a bounded handoff document with the active slice, what was done, what remains, and validation state | varies |
| "Create a worktree for this" | Agent runs `/odylith-worktree` to create an isolated git worktree with the required `<year>/freedom/<tag>` branch format | ~1s |

### Making Changes

| Instruction | What happens | Time |
|---|---|---|
| "Fix it" / "Implement this" / "Refactor that" | Agent edits files → PostToolUse hook fires async governance sync (validates backlog contract, renders surfaces, mirrors bundle) | ~0.1s hook, ~7s background sync |
| "Only use the authoritative lane" | Execution governance promotes this as a `HardConstraint` on the active contract; future actions that leave the lane are denied | instant |
| "Don't touch the test files" | Execution governance promotes this as a forbidden-move constraint; edits to test files are denied by admissibility | instant |
| "Deploy to cell-01" | Execution governance checks resource closure (safe/incomplete/destructive), validates scope, checks external dependencies, and admits or denies | instant |

### Validating and Testing

| Instruction | What happens | Time |
|---|---|---|
| "Run the tests" | Agent runs the repo's test toolchain; Odylith tracks the result in the execution frontier | varies |
| "Validate the backlog" | Agent runs `/odylith-backlog-validate` which checks 95 workstreams for schema, traceability, plan bindings, and queue posture | ~0.3s |
| "Validate the registry" | Agent runs `/odylith-registry-validate` which checks 25 components for shape, linkage, forensics, and deep-skill policy | ~0.4s |
| "Sync the governance surfaces" | Agent runs `/odylith-sync-governance` — the full 22-step pipeline: normalize plans, backfill traceability, validate contracts, render Compass/Radar/Registry/Casebook/Atlas/Shell, mirror bundle | ~7s forced |
| "Render the Atlas diagrams" | Agent runs `/odylith-atlas-render` to validate the Mermaid catalog and check diagram freshness | ~0.1s |
| "Update the Atlas diagrams" | Agent runs `/odylith-atlas-auto-update` to refresh impacted diagrams from change-watch metadata | ~0.1s |
| "Sync the component specs" | Agent runs `/odylith-registry-sync-specs` to fold Compass requirement evidence into per-component living specs | ~0.1s |

### Compass and Observability

| Instruction | What happens | Time |
|---|---|---|
| "Refresh the Compass" | Agent runs `/odylith-compass-refresh-wait` — renders the full Compass surface and waits for brief settlement | ~2s cached / ~25s cold |
| "Log this checkpoint" | Agent runs `/odylith-compass-log` to append a bounded execution note to the Compass timeline | ~0.07s |
| "What's the execution state?" | Agent reads the execution governance snapshot from the context packet — admissibility outcome, frontier phase, active blocker, pressure signals | instant |
| "What changed recently?" | Agent reads the Compass timeline events and transaction history from the runtime payload | instant |

### Delegation and Subagents

| Instruction | What happens | Time |
|---|---|---|
| "Delegate this to a subagent" | Execution governance checks if the host supports delegation (Claude: task_tool_subagents, Codex: routed_spawn), checks lane policy guards, and admits or denies | instant |
| "Run this in parallel" | Lane policy checks artifact-path support, closure safety, and host capability before admitting parallel fan-out | instant |
| "Review this change" | Agent spawns the `odylith-reviewer` subagent which checks for regressions, governance drift, and missing proof without editing files | varies |
| "Validate this slice" | Agent spawns the `odylith-validator` subagent which runs bounded validation, interprets failure signatures, and flags skipped coverage | varies |

---

## Layer 2: Slash Commands

These are explicit commands the operator can type directly. Each maps to an
Odylith CLI call.

| Command | CLI | Time |
|---|---|---|
| `/odylith-start` | `odylith start --repo-root .` | 1.7s |
| `/odylith-version` | `odylith version --repo-root .` | 0.8s |
| `/odylith-session-brief` | `odylith claude session-start --repo-root .` | 1.8s |
| `/odylith-compatibility` | `odylith claude compatibility --repo-root .` | 0.06s |
| `/odylith-doctor` | `odylith doctor --repo-root .` | 1.4s |
| `/odylith-context <ref>` | `odylith context --repo-root . <ref>` | 5.0s |
| `/odylith-query <terms>` | `odylith query --repo-root . "<terms>"` | 1.3s |
| `/odylith-compass-refresh-wait` | `odylith compass refresh --repo-root . --wait` | 2-60s |
| `/odylith-compass-log` | `odylith compass log --repo-root . --kind <kind> --summary <text>` | 0.07s |
| `/odylith-sync-governance` | `odylith sync --repo-root . [--force]` | 0.1-7s |
| `/odylith-atlas-render` | `odylith atlas render --repo-root .` | 0.08s |
| `/odylith-atlas-auto-update` | `odylith atlas auto-update --repo-root .` | 0.07s |
| `/odylith-backlog-validate` | `odylith validate backlog-contract --repo-root .` | 0.3s |
| `/odylith-registry-validate` | `odylith validate component-registry-contract --repo-root .` | 0.4s |
| `/odylith-registry-sync-specs` | `odylith governance sync-component-spec-requirements --repo-root .` | 0.1s |
| `/odylith-workstream-new` | `odylith backlog create --repo-root . --title <title>` | 0.3s |
| `/odylith-plan` | Grounds context, then builds a technical plan | varies |
| `/odylith-handoff` | Grounds context, then builds a handoff document | varies |
| `/odylith-case` | Searches existing bugs, then captures failure evidence | varies |
| `/odylith-worktree` | Creates an isolated git worktree | ~1s |

---

## Layer 3: Automatic Hooks

These fire without the operator asking. They are configured in
`.claude/settings.json` and run on every matching event in the session.

| Event | What fires | What it does | Timeout |
|---|---|---|---|
| **SessionStart** | `odylith claude session-start` | Writes the governed brief to Claude auto-memory, checks brief staleness (>4h triggers background Compass refresh), prints startup summary | 30s |
| **UserPromptSubmit** | `odylith claude prompt-context` | Injects Odylith context anchors into the prompt based on workstream evidence in the user's message | 30s |
| **PreToolUse (Bash)** | `odylith claude bash-guard` | Guards dangerous bash commands against the active execution contract | 10s |
| **PostToolUse (Write/Edit)** | `odylith claude post-edit-checkpoint` | Async governance sync after every file edit — validates contracts, renders affected surfaces, mirrors bundle | 180s (async) |
| **SubagentStart** | `odylith claude subagent-start` | Injects the active Odylith slice into the subagent's context so it inherits grounding and governance | 20s |
| **SubagentStop** | `odylith claude subagent-stop` | Records the subagent's result in the Compass timeline | 30s (async) |
| **PreCompact** | `odylith claude pre-compact-snapshot` | Writes a restart snapshot to Claude auto-memory before context compaction so the next turn can resume from grounded state | 20s |
| **Stop** | `odylith claude stop-summary` | Records the session stop in the Compass timeline | 20s |

---

## Layer 4: Project Subagents

These are specialized agents that the main session spawns for bounded
delegation. Each runs in its own context with the Odylith slice injected.

| Subagent | When it's used | What it does |
|---|---|---|
| **odylith-workstream** | Implementing a bounded workstream slice | Edits code while respecting repo guidance, governance, and validation contracts |
| **odylith-validator** | Proving a change is correct | Runs bounded validation, interprets failure signatures, flags skipped coverage |
| **odylith-reviewer** | Reviewing before commit/handoff | Checks for regressions, governance drift, and missing proof (read-only) |
| **odylith-governance-scribe** | Updating governance records | Writes to Radar, plans, Casebook, Registry, Atlas from implementation evidence |
| **odylith-registry-scribe** | Updating component specs | Edits `CURRENT_SPEC.md` and registry dossiers for changed components |
| **odylith-atlas-diagrammer** | Updating architecture diagrams | Edits `.mmd` source diagrams and catalog truth with rendered-artifact discipline |
| **odylith-compass-narrator** | Narrating standup briefs | Turns grounded state into crisp prose for the Compass dashboard |
| **odylith-compass-briefer** | Interpreting Compass state | Diagnoses stale vs fresh, reads governance against runtime, diagnoses blockers |
| **odylith-context-engine** | Exploring context packets | Careful retrieval discrimination across candidate packets, routes, and anchors |

---

## Layer 5: Background Skills

These are triggered automatically by the agent when it recognizes a matching
situation. The operator doesn't need to invoke them.

| Skill | Trigger | What it does |
|---|---|---|
| **session-context** | Session start, context compaction, turn transitions | Preserves and resumes Odylith session context and continuity |
| **context-engine-operations** | Entity lookup, packet routing, retrieval | Works with context-engine packets, retrieval, and routing |
| **delivery-governance-surface-ops** | After source-of-truth changes | Maintains delivery and governance surfaces |
| **component-registry** | Component boundary changes | Updates or inspects the Registry inventory |
| **diagram-catalog** | Architecture changes | Updates Atlas diagram catalog truth |
| **casebook-bug-preflight** | Before creating a bug | Checks prerequisites to avoid duplicate or malformed bug records |
| **casebook-bug-capture** | After failure evidence is gathered | Captures a new bug with grounded repro details |
| **casebook-bug-investigation** | When investigating an existing bug | Gathers evidence and connects to governed surfaces |
| **registry-spec-sync** | After component implementation changes | Syncs implementation evidence into component specs |
| **schema-registry-governance** | After schema changes | Maintains schema-governance contracts |
| **security-hardening** | During bounded product changes | Applies security-hardening guidance |
| **subagent-router** | Before delegation | Chooses local vs bounded delegation, shapes routed payloads |
| **subagent-orchestrator** | Multi-subagent work | Plans delegation ownership, bounded fanout, and merge-safe orchestration |
| **compass-executive** | When the operator asks about repo state | Interprets Compass briefs and executive summaries |
| **compass-timeline-stream** | When reviewing execution history | Works with timeline and execution-stream evidence |

---

## Execution Governance (Invisible Layer)

Every action the agent takes is screened by the execution engine. This runs
inside every context packet and every admissibility decision. The operator never
sees it directly, but it shapes every move.

| What it checks | What happens when it fires |
|---|---|
| **Admissibility** | Every intended action is screened: `admit`, `deny`, or `defer`. Denied actions get a nearest admissible alternative. |
| **Hard constraints** | User corrections ("don't use X", "only touch Y") are promoted into the execution contract and enforced on every subsequent action. |
| **Contradiction detection** | If an intended action contradicts the contract, user instructions, docs, or live state, it's flagged and blocked. |
| **Resource closure** | Before mutating, the engine checks if the scope is safe, incomplete (missing dependencies), or destructive (partial overlap with a destructive group). |
| **Frontier tracking** | The engine tracks current phase, last successful phase, active blocker, and truthful next move across the session. |
| **External dependency wait** | If a CI run, deploy, or callback is in flight, the engine defers new work until the dependency resolves or the operator explicitly overrides. |
| **History rule pressure** | Known failure patterns (context exhaustion, subagent timeout, lane drift, repeated rediscovery) are recognized and block re-execution of the same mistake. |
| **Host-aware delegation** | Claude gets `bounded_task_subagent` alternatives; Codex gets `routed_spawn`. Artifact-path guards block unsafe parallel fan-out on hosts that can't share file state. |
| **Context pressure** | When context window pressure is high or critical, it's surfaced as a pressure signal so downstream consumers can adjust scope. |

---

## Host Behavior

Odylith detects the host automatically from environment variables and adapts.

| Aspect | Claude Code | Codex |
|---|---|---|
| **Detection** | `CLAUDE_CODE_*` env vars, `__CFBundleIdentifier` | `CODEX_THREAD_ID`, `CODEX_SHELL` |
| **Delegation style** | `task_tool_subagents` | `routed_spawn` |
| **Narration model** | `claude-haiku-4-5`, low effort | `gpt-5.3-codex-spark`, medium effort |
| **Binary discovery** | Glob: `~/Library/Application Support/Claude/claude-code/*/claude.app/...` | Static: `/Applications/Codex.app/Contents/Resources/codex` |
| **Narration timeout** | 60s per brief | 30s per brief (local inference, faster) |
| **Supports interrupt** | No | Yes |
| **Supports artifact paths** | No | Yes |
| **Presentation defaults** | `task_first` commentary, suppress routing receipts | None (uses contract defaults) |
| **Profile ladder** | haiku (analysis/fast) → sonnet (write) → opus (frontier) | gpt-5.4-mini → spark → codex → gpt-5.4 |

Switching hosts mid-day (Claude session then Codex session on the same repo)
works automatically. Provider-scoped backoff ensures a credit failure on one
host doesn't block the other.
