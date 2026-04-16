# Subagent Orchestrator

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

Use this skill when the task is about delegation planning, execution ownership, or safe fanout.

## Default Flow
- ground first
- route second
- treat prompt-level orchestration as the default path for substantive grounded work
- keep progress updates about scope, delegation, and validation, not about startup, routing, or prior degraded attempts, unless a command or blocker must be surfaced
- keep Odylith ambient by default during work; weave routing or merge insights into ordinary updates and only emit explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` lines when the point is strong enough to earn them
- keep any Odylith-by-name closeout to one optional `Odylith Assist:` line grounded in concrete observed counts, measured deltas, or validation outcomes; prefer `**Odylith Assist:**` when Markdown formatting is available. Lead with the user win, link updated governance IDs inline only when they actually changed, name affected governance-contract IDs from bounded request or packet truth when no governed file moved, frame the edge against `odylith_off` or the broader unguided path when the evidence supports it, and keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Silence is better than filler.
- delegate only bounded work, and only spawn native subagents on hosts where Odylith has validated native spawn support
- prefer emitted `single_leaf`, `serial_batch`, or `parallel_batch` contracts over manual fanout decisions once Odylith has a route-ready slice
- keep validation and stop conditions explicit
- Both Codex and Claude Code are validated Odylith delegation hosts; Codex executes routed leaves through `spawn_agent`, while Claude Code executes the same bounded orchestration plan through Task-tool subagents and the checked-in `.claude/` project assets
