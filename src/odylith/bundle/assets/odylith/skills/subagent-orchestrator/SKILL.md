# Subagent Orchestrator

Use this skill when the task is about delegation planning, execution ownership, or safe fanout.

## Default Flow
- ground first
- route second
- treat prompt-level orchestration as the default path for substantive grounded Codex work
- keep progress updates about scope, delegation, and validation, not about startup, routing, or prior degraded attempts, unless a command or blocker must be surfaced
- keep any Odylith-by-name closeout to one optional `Odylith assist:` line grounded in concrete observed counts, measured deltas, or validation outcomes; prefer `**Odylith assist:**` when Markdown formatting is available. Lead with the user win, frame the edge against `odylith_off` or the broader unguided path when the evidence supports it, and keep it soulful, friendly, authentic, and factual
- delegate only bounded work, and only spawn native subagents in Codex
- prefer emitted `single_leaf`, `serial_batch`, or `parallel_batch` contracts over manual fanout decisions once Odylith has a route-ready slice
- keep validation and stop conditions explicit
- in Claude Code, treat the emitted orchestration plan as local-only guidance and do not spawn native subagents
