# CLI-First Non-Negotiable Policy

## Scope
- This policy is non-negotiable and applies to both Codex and Claude Code.
- It governs every grounded workstream, governance slice, validation pass, and session upkeep turn in this repository and in every repository that runs Odylith.
- It overrides any earlier guidance that still implied hand-editing governed truth is acceptable when a CLI exists.

## The Rule
- Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. This is the non-negotiable.
- When an Odylith CLI command exists for an operation, the agent must call that CLI command and must not hand-author the same content.
- Hand-authoring or hand-editing governed files where a dedicated CLI exists is forbidden and is a hard policy violation, not a stylistic preference.
- If a CLI surface is unclear, check `./.odylith/bin/odylith --help` and the matching subcommand `--help` before falling back to direct Edit tool calls.
- If no CLI owns the exact operation, hand-editing remains allowed, but only for the specific content the CLI cannot author, and the agent must still run `./.odylith/bin/odylith sync --repo-root . --impact-mode selective <paths>` afterwards to refresh every governed projection.

## Why This Is Non-Negotiable
- Every hand-edit of governed truth races with the Odylith writer, silently drifts generated surfaces, and creates partial states that fail `odylith sync --check-only`.
- CLI commands record authoritative events, emit execution-governance receipts, and keep downstream surfaces (Radar, Compass, Atlas, Registry, Casebook) consistent in one step.
- Skipping CLI commands wastes operator time, forces a redundant refresh, and produces exactly the kind of governance drift Odylith exists to prevent.

## Authoritative CLI Surface (non-exhaustive)
- `./.odylith/bin/odylith bug capture` for new Casebook bug records. The
  command is fail-closed: it requires grounded intake evidence and must not be
  used as a title-only placeholder writer.
- `./.odylith/bin/odylith release {create,update,list,show,add,remove,move}` for release-planning truth. Never hand-edit `odylith/radar/source/releases/releases.v1.json` or `odylith/radar/source/releases/release-assignment-events.v1.jsonl`.
- `./.odylith/bin/odylith backlog create` for new Radar workstreams.
  The command is fail-closed: it requires grounded Problem, Customer,
  Opportunity, Product View, and Success Metrics input and must not be used as
  a title-only placeholder writer. Never hand-author rows in
  `odylith/radar/source/INDEX.md` for new backlog ids.
- `./.odylith/bin/odylith governance backfill-workstream-traceability` for Radar idea traceability fields such as `workstream_parent`, `workstream_children`, and reciprocal links.
- `./.odylith/bin/odylith governance reconcile-plan-workstream-binding` for active-plan rows and bindings in `odylith/technical-plans/INDEX.md`.
- `./.odylith/bin/odylith governance auto-promote-workstream-phase` for Radar workstream phase promotion driven by live evidence.
- `./.odylith/bin/odylith governance sync-component-spec-requirements` for regenerating Registry `FORENSICS.v1.json` sidecars and component spec requirements.
- `./.odylith/bin/odylith governance normalize-plan-risk-mitigation` for technical-plan risk and mitigation sections.
- `./.odylith/bin/odylith sync [--check-only] [--impact-mode selective <paths>]` for governance and surface refresh.
- `./.odylith/bin/odylith radar refresh --repo-root .`, `./.odylith/bin/odylith registry refresh --repo-root .`, `./.odylith/bin/odylith casebook refresh --repo-root .`, `./.odylith/bin/odylith atlas refresh --repo-root . [--atlas-sync]`, and `./.odylith/bin/odylith compass refresh --repo-root .` for owned-surface quick visibility after a narrow truth change. Use `./.odylith/bin/odylith compass deep-refresh --repo-root .` when you also need standup-brief settlement.
- `./.odylith/bin/odylith compass {log,refresh,deep-refresh,update,restore-history,watch-transactions}` for Compass timeline events and runtime snapshots.
- `./.odylith/bin/odylith atlas ...` for Atlas diagram catalog and rendering operations.
- `./.odylith/bin/odylith program ...` and `./.odylith/bin/odylith wave ...` for umbrella execution-wave members and gates.
- `./.odylith/bin/odylith dashboard refresh --repo-root . [--surfaces ...]` for explicit multi-surface shell rerenders when the task is about a combined view rather than one owned surface.
- `./.odylith/bin/odylith validate ...` for governance and contract validators.
- `./.odylith/bin/odylith context`, `./.odylith/bin/odylith query`, `./.odylith/bin/odylith session-brief`, `./.odylith/bin/odylith context-engine ...` for grounding and retrieval.
- `./.odylith/bin/odylith subagent-router ...` and `./.odylith/bin/odylith subagent-orchestrator ...` for bounded leaf routing and orchestration.
- `./.odylith/bin/odylith benchmark ...` for the Odylith benchmark harness.
- `./.odylith/bin/odylith start`, `./.odylith/bin/odylith lane`, `./.odylith/bin/odylith install`, `./.odylith/bin/odylith reinstall`, `./.odylith/bin/odylith upgrade`, `./.odylith/bin/odylith rollback`, `./.odylith/bin/odylith version`, `./.odylith/bin/odylith doctor` for install, lane posture, and runtime lifecycle.

## Narrow Allowed Hand-Edit Surfaces
- Hand-editing is only allowed for authored content that has no CLI owner. Examples:
  - Technical-plan body content under `odylith/technical-plans/` (Goal, Learnings, Must-Ship, Validation, Outcome Snapshot). The plan index rows are CLI-managed.
  - Casebook bug narrative under `odylith/casebook/bugs/` (Description, Impact, Resolution notes, Related Incidents). The Casebook INDEX projection is derived from these files via `odylith sync`.
  - Registry `CURRENT_SPEC.md` living specs under `odylith/registry/source/components/*/`. The `FORENSICS.v1.json` sidecars are CLI-managed.
  - Atlas `.mmd` diagram sources under `odylith/atlas/source/`. The `catalog/diagrams.v1.json` projection is CLI-managed.
  - Guidance markdown under `odylith/agents-guidelines/` and skill shims under `odylith/skills/`.
  - Scoped `AGENTS.md` and `CLAUDE.md` companion files.
- Even in the allowed surfaces, run `./.odylith/bin/odylith sync --repo-root . --impact-mode selective <changed_paths>` after the edit to refresh governed projections.

## Failure Mode Handling
- If the CLI reports `selector did not match` or similar, do not hand-edit the underlying file as a workaround. Re-check the selector, read the subcommand help, and either use the correct selector or surface the blocker to the operator.
- If the CLI is missing a subcommand for an operation the agent believes should be governed, treat that as a maintainer-feedback packet rather than a license to hand-edit.
- If a CLI exists but the agent has already hand-edited the file, re-run the matching CLI command to re-assert governed truth and make the edit idempotent. Record the CLI miss in Casebook as a learning.

## Host Coverage
- Codex and Claude Code both execute under this policy.
- In Codex, CLI-first applies to the primary session and every routed `spawn_agent` leaf.
- In Claude Code, CLI-first applies to the primary session and every Task-tool subagent spawn.
- The policy travels through Odylith subagent routing so delegated leaves inherit the same CLI-first contract.

## Learning Anchor
- The canonical Casebook learning for this policy is `CB-104: Agents hand-edited governed truth when Odylith CLI commands existed`. Treat that learning as the grounding anchor when onboarding new hosts or skills.
