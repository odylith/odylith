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
| **"Odylith, what's the state of the repo?"** | Builds a Compass-derived summary — active workstreams, next actions, risks, recent activity. `odylith session-brief` |
| **"Odylith, find everything related to auth"** | Searches LanceDB + Tantivy across all compiled documents — workstreams, components, plans, bugs, diagrams. `odylith query "auth"` |
| **"Odylith, show me the auth-service component"** | Resolves one entity into a full context dossier with relations, delivery scopes, and governance snapshot. `odylith context auth-service` |
| **"Odylith, what workstreams are active?"** | Reads the live Compass runtime payload for current workstream posture. |
| **"Odylith, what's the architecture impact of these changes?"** | Resolves plane/stack topology grounding and diagram-watch gaps for changed paths. `odylith architecture` |

---

## Create

Build governance records that give the agent durable context.

### Workstreams (Radar)

| Say this | What happens |
|---|---|
| **"Create a workstream for auth migration"** | Creates a Radar record with schema, ordering score, and INDEX patching. `odylith backlog create --title "Auth migration to JWT"` |
| **"Plan the implementation for B-073"** | Grounds the workstream, then builds a bounded technical plan under `odylith/technical-plans/`. |

### Components (Registry)

| Say this | What happens |
|---|---|
| **"Register a component for the auth service"** | Creates a registry entry and scaffolds `CURRENT_SPEC.md`. `odylith component register --id auth-service --path src/auth --label "Auth Service"` |
| **"Update the component spec for auth"** | Spawns the registry-scribe subagent to edit the living spec with implementation evidence. |
| **"What components exist?"** | Reads the component registry manifest. `odylith context <component-id>` for a specific dossier. |

### Bugs (Casebook)

| Say this | What happens |
|---|---|
| **"File a bug for this"** | Creates a Casebook record with CB-### ID and INDEX patching. `odylith bug capture --title "Description" --component <id>` |
| **"Investigate CB-105"** | Loads the bug dossier and gathers evidence across governed surfaces. `odylith context CB-105` |
| **"Is there already a bug for this?"** | Searches existing Casebook records to avoid duplicates. `odylith query "description"` |

### Diagrams (Atlas)

| Say this | What happens |
|---|---|
| **"Create a diagram for the auth flow"** | Creates catalog entry and optional Mermaid source. `odylith atlas scaffold --slug auth-flow --title "Auth Flow" --kind flowchart` |
| **"Update diagram D-017"** | Spawns the atlas-diagrammer subagent to edit the `.mmd` source with rendered-artifact discipline. |
| **"Render the Atlas diagrams"** | Validates the Mermaid catalog and checks diagram freshness. `odylith atlas render` |
| **"Auto-update impacted diagrams"** | Refreshes diagrams based on change-watch metadata. `odylith atlas auto-update` |

### Programs, Waves, and Releases

| Say this | What happens |
|---|---|
| **"Create a program for the v2 launch"** | Creates an umbrella execution-wave program. `odylith program create --title "V2 Launch"` |
| **"Create a wave inside the v2 program"** | Adds a wave with member slots. `odylith wave create --program <id> --label "Wave 1: Core"` |
| **"Assign B-073 to wave 1"** | `odylith wave assign --program <id> --wave <wave-id> --workstream B-073` |
| **"Create a release definition"** | `odylith release create --version <version>` |
| **"Assign B-073 to the next release"** | `odylith release add --workstream B-073 --release <release-id>` |
| **"Move B-073 to a different release"** | `odylith release move --workstream B-073 --to <release-id>` |
| **"What's in the current release?"** | `odylith release show --release <release-id>` |

---

## Execute

Do the actual work — Odylith governs every move automatically.

| Say this | What happens |
|---|---|
| **"Fix the bug in the checkout flow"** | Grounds the task via `odylith start`, matches workstream, builds execution contract, resolves component, loads context packet — then edits. Every file edit triggers async governance sync in the background. |
| **"Work on B-073"** | Resolves the workstream anchor, loads related entities and delivery scopes. `odylith context B-073` |
| **"Only touch files in src/auth"** | Promoted to a hard constraint — edits outside `src/auth` are denied by the execution engine. |
| **"Don't touch the test files"** | Promoted to a forbidden-move constraint enforced on every subsequent action. |
| **"Delegate this to a subagent"** | Checks host delegation support, lane policy, and admits or denies. Claude uses task-tool subagents; Codex uses routed spawn. |
| **"Review this change"** | Spawns the reviewer subagent — checks regressions, governance drift, and missing proof without editing. |
| **"Validate this slice"** | Spawns the validator subagent — runs tests, interprets failures, flags skipped coverage. |
| **"Hand this off"** | Prepares a bounded handoff with the active slice, what was done, what remains, and validation state. |

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

---

## Validate and Sync

Check that governance records are correct and surfaces are current.

| Say this | What happens |
|---|---|
| **"Run the tests"** | Runs the repo's own test toolchain. Odylith tracks the result in the execution frontier. |
| **"Validate the backlog"** | Checks workstreams for schema, traceability, plan bindings, and queue posture. `odylith validate backlog-contract` |
| **"Validate the registry"** | Checks components for shape, linkage, forensics, and policy. `odylith validate component-registry` |
| **"Sync the governance surfaces"** | Full pipeline — normalize plans, backfill traceability, validate contracts, render all surfaces, mirror bundle. `odylith sync` |
| **"Sync the component specs"** | Folds Compass requirement evidence into per-component living specs. `odylith governance sync-component-spec-requirements` |

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

---

## Automatic Behavior

These fire without the operator asking. Configured in project hooks and run on
every matching event.

| Event | What happens |
|---|---|
| **Session start** | Writes governed brief to auto-memory, checks staleness, prints startup summary |
| **Every prompt** | Injects Odylith context anchors based on workstream evidence in the message |
| **Every bash command** | Guards dangerous commands against the active execution contract |
| **Every file edit** | Async governance sync — validates contracts, renders affected surfaces, mirrors bundle |
| **Subagent spawn** | Injects the active Odylith slice so the subagent inherits grounding |
| **Subagent stop** | Records the result in the Compass timeline |
| **Context compaction** | Writes restart snapshot to auto-memory so the next turn resumes from grounded state |
| **Session stop** | Records the session stop in Compass |

---

## Execution Governance (Invisible)

Every action the agent takes is screened. The operator never sees this directly,
but it shapes every move.

- **Admissibility** — every action is screened: admit, deny, or defer
- **Hard constraints** — user corrections are promoted into the execution contract
- **Contradiction detection** — actions that contradict the contract, docs, or live state are blocked
- **Resource closure** — checks if scope is safe, incomplete, or destructive before mutating
- **Frontier tracking** — tracks phase, blocker, and truthful next move across the session
- **History rule pressure** — known failure patterns block re-execution of the same mistake
- **Host-aware delegation** — Claude gets task-tool subagents, Codex gets routed spawn
- **Context pressure** — surfaces when context window is high so consumers adjust scope
