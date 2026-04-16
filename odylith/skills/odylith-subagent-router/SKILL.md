# Subagent Router

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

Use this skill when the task is about choosing local execution versus delegation and about shaping route-ready execution payloads.

## Default Flow
- preserve retained routing data
- default to routed native delegation for substantive grounded work when the current host supports it unless Odylith returns `main_thread`
- keep consumer-facing route explanations task-first; do not narrate routing or degraded-start history unless a command, blocker, or lane distinction matters
- keep Odylith ambient by default during work; weave routing facts into ordinary updates and only emit explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` lines when the signal is real
- reserve Odylith-by-name closeout text for one optional `Odylith Assist:` line grounded in concrete observed counts, measured deltas, or validation outcomes; prefer `**Odylith Assist:**` when Markdown formatting is available. Lead with the user win, link updated governance IDs inline only when they actually changed, name affected governance-contract IDs from bounded request or packet truth when no governed file moved, frame the edge against `odylith_off` or the broader unguided path when the evidence supports it, and keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Silence is better than filler.
- keep reasons-to-stay-local explicit
- let Odylith-earned depth and delegation readiness drive the model ladder instead of manually jumping to the heaviest tier
- prefer additive routing contracts over prompt-only conventions
- treat native delegation as capability-gated by host contract; Codex uses routed `spawn_agent` payloads, while Claude Code uses Task-tool subagents plus the same routed contract and checked-in `.claude/` project assets
