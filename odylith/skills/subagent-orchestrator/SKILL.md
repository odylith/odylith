# Subagent Orchestrator

Use this skill when the task is about delegation planning, execution ownership, or safe fanout.

## Default Flow
- ground first
- route second
- treat prompt-level orchestration as the default path for substantive grounded Codex work
- keep progress updates about scope, delegation, and validation, not about startup, routing, or prior degraded attempts, unless a command or blocker must be surfaced
- keep Odylith ambient by default during work; weave routing or merge insights into ordinary updates and only emit explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` lines when the point is strong enough to earn them
- keep any Odylith-by-name closeout to one optional `Odylith Assist:` line grounded in concrete observed counts, measured deltas, or validation outcomes; prefer `**Odylith Assist:**` when Markdown formatting is available. Lead with the user win, link updated governance ids inline when they were actually changed, frame the edge against `odylith_off` or the broader unguided path when the evidence supports it, and keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Silence is better than filler.
- delegate only bounded work, and only spawn native subagents in Codex
- prefer emitted `single_leaf`, `serial_batch`, or `parallel_batch` contracts over manual fanout decisions once Odylith has a route-ready slice
- keep validation and stop conditions explicit
- in Claude Code, treat the emitted orchestration plan as local-only guidance and do not spawn native subagents
