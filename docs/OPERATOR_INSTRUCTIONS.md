# Odylith Operator Instructions

Everything you can say to a coding agent in an Odylith-enabled repo. The agent
translates each instruction into Odylith CLI calls — you never need to know the
CLI surface. Works identically on Codex and Claude Code.

---

## Discover

Explore your repo and understand what Odylith sees.

| Say this | What happens |
|---|---|
| **"Odylith, show me what you can do"** | Reads source structure, import graph, and manifests. Suggests components, workstreams, diagrams, and issues with the exact command to create each one. `odylith show` |
| **"Odylith, what's the state of the repo?"** | Builds a Compass-derived summary of active workstreams, next actions, risks, and recent activity. `odylith session-brief` |
| **"Odylith, find everything related to checkout"** | Searches all governed records for matches. Replace `checkout` with whatever you're looking for in your repo. `odylith query "checkout"` |
| **"Odylith, show me the payments component"** | Resolves one entity into a full context dossier with relations, delivery scopes, and governance snapshot. Replace `payments` with any component, workstream, bug, or diagram ID in your repo. `odylith context payments` |
| **"Odylith, what workstreams are active?"** | Reads the live Compass runtime payload for current workstream posture. |
| **"Odylith, what's the architecture impact of these changes?"** | Resolves topology grounding and diagram-watch gaps for changed paths. `odylith architecture` |
| **"Odylith, show me the governance slice for this workstream"** | Builds a compact governance and delivery-truth packet for one scope. `odylith governance-slice` |
| **"Odylith, what's the delivery intelligence for this?"** | Reads the delivery intelligence artifact for posture mode, governance lag, blast radius, and trajectory. |

---

## Create

Build governance records that give the agent durable context.

### Workstreams (Radar)

| Say this | What happens |
|---|---|
| **"Create a workstream for auth migration"** | Creates a Radar record with schema, ordering score, and INDEX patching. `odylith backlog create --title "Auth migration to JWT"` |
| **"Plan the implementation for B-073"** | Grounds the workstream, then builds a bounded technical plan under `odylith/technical-plans/`. |
| **"Split B-073 into two workstreams"** | Creates child workstreams with proper parent-child traceability and split lineage. |
| **"Reopen B-041"** | Reopens a finished or parked workstream with proper reopen lineage tracking. |
| **"Park B-073"** | Parks a workstream — removes it from the active queue while preserving all history. |

### Components (Registry)

| Say this | What happens |
|---|---|
| **"Register a component for the auth service"** | Creates a registry entry and scaffolds `CURRENT_SPEC.md`. `odylith component register --id auth-service --path src/auth --label "Auth Service"` |
| **"Update the component spec for auth"** | Spawns the registry-scribe subagent to edit the living spec with implementation evidence. |
| **"What components exist?"** | Reads the component registry manifest. `odylith context <component-id>` for a specific dossier. |
| **"Sync the component specs"** | Folds Compass requirement evidence into per-component living specs. `odylith governance sync-component-spec-requirements` |
| **"Show me the forensic timeline for auth-service"** | Reads the component's forensic sidecar — timestamped events, coverage status, evidence channels. |

### Bugs (Casebook)

| Say this | What happens |
|---|---|
| **"File a bug for this"** | Creates a Casebook record with CB-### ID and INDEX patching. `odylith bug capture --title "Description" --component <id>` |
| **"Investigate CB-105"** | Loads the bug dossier and gathers evidence across governed surfaces. `odylith context CB-105` |
| **"Is there already a bug for this?"** | Searches existing Casebook records to avoid duplicates. `odylith query "description"` |
| **"Close CB-105 with this fix"** | Updates the bug status, records the solution, verification, and prevention fields. |
| **"What bugs are open?"** | Reads the Casebook INDEX for open bugs sorted by severity. |

### Diagrams (Atlas)

| Say this | What happens |
|---|---|
| **"Create a diagram for the auth flow"** | Creates catalog entry and optional Mermaid source. `odylith atlas scaffold --slug auth-flow --title "Auth Flow" --kind flowchart` |
| **"Update diagram D-017"** | Spawns the atlas-diagrammer subagent to edit the `.mmd` source with rendered-artifact discipline. |
| **"Render the Atlas diagrams"** | Validates the Mermaid catalog and checks diagram freshness. `odylith atlas render` |
| **"Auto-update impacted diagrams"** | Refreshes diagrams based on change-watch metadata. `odylith atlas auto-update` |
| **"Which diagrams are stale?"** | Reads the Atlas catalog for diagrams whose change-watch paths have been modified since last review. |

### Programs, Waves, and Releases

| Say this | What happens |
|---|---|
| **"Create a program for the v2 launch"** | Creates an umbrella execution-wave program. `odylith program create --title "V2 Launch"` |
| **"What's the program status?"** | Shows one program summary and next posture. `odylith program status` |
| **"What's the next authoring step?"** | Returns one truthful next command for the program. `odylith program next` |
| **"Create a wave inside the v2 program"** | Adds a wave with member slots. `odylith wave create --program <id> --label "Wave 1: Core"` |
| **"Assign B-073 to wave 1"** | `odylith wave assign --program <id> --wave <wave-id> --workstream B-073` |
| **"Remove B-073 from its wave"** | `odylith wave unassign --program <id> --wave <wave-id> --workstream B-073` |
| **"Add a gate for B-073 in wave 1"** | `odylith wave gate-add --program <id> --wave <wave-id> --workstream B-073 --gate <ref>` |
| **"What's the wave status?"** | Shows current member and gate posture. `odylith wave status` |
| **"Create a release definition"** | `odylith release create --version <version>` |
| **"Assign B-073 to the next release"** | `odylith release add --workstream B-073 --release <release-id>` |
| **"Move B-073 to a different release"** | `odylith release move --workstream B-073 --to <release-id>` |
| **"Remove B-073 from its release"** | `odylith release remove --workstream B-073` |
| **"What's in the current release?"** | `odylith release show --release <release-id>` |
| **"List all releases"** | `odylith release list` |

---

## Execute

Do the actual work — Odylith governs every move automatically.

| Say this | What happens |
|---|---|
| **"Fix the bug in the checkout flow"** | Grounds the task via `odylith start`, matches workstream, builds execution contract, resolves component, loads context packet — then edits. Every file edit triggers async governance sync in the background. |
| **"Work on B-073"** | Resolves the workstream anchor, loads related entities and delivery scopes. `odylith context B-073` |
| **"Only touch files in src/auth"** | Promoted to a hard constraint — edits outside `src/auth` are denied by the execution engine. |
| **"Don't touch the test files"** | Promoted to a forbidden-move constraint enforced on every subsequent action. |
| **"Create a worktree for this"** | Creates an isolated git worktree so this work doesn't interfere with other branches. |
| **"Hand this off"** | Prepares a bounded handoff with the active slice, what was done, what remains, and validation state. |

### Delegation

| Say this | What happens |
|---|---|
| **"Delegate this to a subagent"** | Checks host delegation support, lane policy, and admits or denies. Claude uses task-tool subagents; Codex uses routed spawn. |
| **"Run this in parallel"** | Lane policy checks artifact-path support, closure safety, and host capability before admitting parallel fan-out. |
| **"Review this change"** | Spawns the **reviewer** subagent — checks regressions, governance drift, and missing proof without editing files. |
| **"Validate this slice"** | Spawns the **validator** subagent — runs tests, interprets failures, flags skipped coverage. |
| **"Implement this workstream slice"** | Spawns the **workstream** subagent — edits code while respecting repo guidance, governance, and validation contracts. |
| **"Update the governance records"** | Spawns the **governance-scribe** subagent — writes to Radar, plans, Casebook, Registry, Atlas from implementation evidence. |
| **"Update the component spec"** | Spawns the **registry-scribe** subagent — edits `CURRENT_SPEC.md` and registry dossiers. |
| **"Update the architecture diagrams"** | Spawns the **atlas-diagrammer** subagent — edits `.mmd` source with rendered-artifact discipline. |
| **"Narrate the standup brief"** | Spawns the **compass-narrator** subagent — turns grounded state into crisp prose. |
| **"Diagnose the Compass state"** | Spawns the **compass-briefer** subagent — distinguishes stale from fresh, reads governance against runtime, diagnoses blockers. |
| **"Explore the context packets"** | Spawns the **context-engine** subagent — careful retrieval discrimination across candidate packets, routes, and anchors. |

---

## Observe

See what happened, what matters now, and what's next.

| Say this | What happens |
|---|---|
| **"What's the standup brief?"** | Reads the latest narrated Compass brief — what changed, what matters, what's next. |
| **"Show me what happened in the last 48 hours"** | Reads Compass timeline events in the 48h audit window. |
| **"Refresh the Compass"** | Renders the full Compass surface and waits for brief settlement. `odylith compass refresh --wait` |
| **"Log this checkpoint"** | Appends a bounded execution note to the Compass timeline. `odylith compass log` |
| **"I want the brief to focus on auth work"** | Narrows Compass brief scope to workstreams touching the auth component. |
| **"Make the brief shorter"** | Adjusts narration to the compact voice contract — fewer details, same signal. |
| **"What's the execution state?"** | Reads the execution governance snapshot — admissibility outcome, frontier phase, active blocker, pressure signals. |
| **"What changed recently?"** | Reads the Compass timeline events and transaction history from the runtime payload. |
| **"Show me the execution timeline for B-073"** | Reads the workstream-scoped Compass timeline with all related events. |

---

## Validate and Sync

Check that governance records are correct and surfaces are current.

| Say this | What happens |
|---|---|
| **"Run the tests"** | Runs the repo's own test toolchain. Odylith tracks the result in the execution frontier. |
| **"Validate the backlog"** | Checks workstreams for schema, traceability, plan bindings, and queue posture. `odylith validate backlog-contract` |
| **"Validate the registry"** | Checks components for shape, linkage, forensics, and policy. `odylith validate component-registry` |
| **"Validate plan traceability"** | Checks technical plans for proper workstream bindings. `odylith validate plan-traceability` |
| **"Validate plan risk mitigation"** | Checks risk and mitigation sections in technical plans. `odylith validate plan-risk-mitigation` |
| **"Sync the governance surfaces"** | Full pipeline — normalize plans, backfill traceability, validate contracts, render all surfaces, mirror bundle. `odylith sync` |
| **"Force sync everything"** | Same pipeline but bypasses incremental caching. `odylith sync --force` |
| **"Sync the component specs"** | Folds Compass requirement evidence into per-component living specs. `odylith governance sync-component-spec-requirements` |
| **"Backfill workstream traceability"** | Rebuilds the traceability graph from workstream metadata. `odylith governance backfill-workstream-traceability` |
| **"Reconcile plan-workstream bindings"** | Ensures plans and workstreams point at each other correctly. `odylith governance reconcile-plan-workstream-binding` |
| **"Refresh the dashboard"** | Renders local dashboard surfaces without a full governance sync. `odylith dashboard refresh` |

---

## Status and Health

Check Odylith itself.

| Say this | What happens |
|---|---|
| **"What version of Odylith is installed?"** | Shows pinned, active, and available versions. `odylith version` |
| **"Is Odylith healthy?"** | Verifies launcher integrity, runtime pinning, project assets, and Compass readiness. `odylith doctor` |
| **"Check if Claude Code is set up right"** | Probes local Claude CLI, project hooks, settings, and baked modules. `odylith claude compatibility` |
| **"Turn Odylith off"** | Detaches Odylith-first guidance so agents fall back to default behavior. `odylith off` |
| **"Turn Odylith back on"** | Restores Odylith-first guidance. `odylith on` |
| **"Upgrade Odylith"** | Stages and activates the pinned runtime without rewriting repo-owned truth. `odylith upgrade` |
| **"Rollback Odylith"** | Atomically returns to the previous verified runtime. `odylith rollback` |
| **"Reinstall Odylith"** | Full reinstall with verified pinned runtime in one step. `odylith reinstall` |

---

## Automatic Behavior

These fire without the operator asking. Configured in project hooks and run on
every matching event.

| Event | What fires | What it does |
|---|---|---|
| **Session start** | `session-start` hook | Writes governed brief to auto-memory, checks staleness (>4h triggers background Compass refresh), prints startup summary |
| **Every prompt** | `prompt-context` hook | Injects Odylith context anchors based on workstream evidence in the user's message |
| **Every bash command** | `bash-guard` hook | Guards dangerous commands against the active execution contract |
| **Every file edit** | `post-edit-checkpoint` hook | Async governance sync — validates contracts, renders affected surfaces, mirrors bundle |
| **Subagent spawn** | `subagent-start` hook | Injects the active Odylith slice so the subagent inherits grounding and governance |
| **Subagent stop** | `subagent-stop` hook | Records the subagent's result in the Compass timeline |
| **Context compaction** | `pre-compact-snapshot` hook | Writes restart snapshot to auto-memory so the next turn resumes from grounded state |
| **Session stop** | `stop-summary` hook | Records the session stop in the Compass timeline |

---

## Execution Governance (Invisible)

Every action the agent takes is screened by the execution engine. The operator
never sees this directly, but it shapes every move.

| What it checks | What happens |
|---|---|
| **Admissibility** | Every intended action is screened: `admit`, `deny`, or `defer`. Denied actions get a nearest admissible alternative. |
| **Hard constraints** | User corrections ("don't use X", "only touch Y") are promoted into the execution contract and enforced on every subsequent action. |
| **Contradiction detection** | If an intended action contradicts the contract, user instructions, docs, or live state, it's flagged and blocked. |
| **Resource closure** | Before mutating, the engine checks if the scope is safe, incomplete (missing dependencies), or destructive. |
| **Frontier tracking** | The engine tracks current phase, last successful phase, active blocker, and truthful next move across the session. |
| **External dependency wait** | If a CI run, deploy, or callback is in flight, the engine defers new work until the dependency resolves. |
| **History rule pressure** | Known failure patterns (context exhaustion, subagent timeout, lane drift, repeated rediscovery) are recognized and block re-execution of the same mistake. |
| **Host-aware delegation** | Claude gets `bounded_task_subagent` alternatives; Codex gets `routed_spawn`. Artifact-path guards block unsafe parallel fan-out on hosts that can't share file state. |
| **Context pressure** | When context window pressure is high or critical, it's surfaced as a pressure signal so downstream consumers can adjust scope. |

---

## Host Behavior

Odylith detects the host automatically and adapts.

| Aspect | Claude Code | Codex |
|---|---|---|
| **Delegation style** | Task-tool subagents | Routed spawn |
| **Supports parallel fan-out** | No (no artifact paths) | Yes |
| **Supports interrupt** | No | Yes |
| **Compass narration** | claude-haiku-4-5, 60s timeout | gpt-5.3-codex-spark, 30s timeout |
| **Presentation** | Task-first commentary, suppress routing receipts | Contract defaults |

Switching hosts mid-day (Claude session then Codex session on the same repo)
works automatically. The governance records, Compass history, and all surfaces
are shared — only the execution lane adapts.
