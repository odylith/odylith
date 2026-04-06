# Odylith Context Engine Operations

Use this skill when the task is about packet choice, daemon health, warmup posture, retrieval quality, or context-engine debugging.

## Lane Boundary
- Consumer lane uses Odylith's managed runtime for Odylith commands, but target
  repo validation still belongs to the consumer repo's own toolchain.
- File-edit authority follows repo scope, not interpreter choice.

## Default Flow
- check `status` or `doctor` first
- use `start` as the default first-turn entrypoint, then choose the smallest Odylith packet that matches the slice and stay on Odylith for most grounded work
- use `bootstrap`, `context`, `query`, `session-brief`, and `governance-slice` when you need grounded start-up, exact-ref lookup, or governed-surface context instead of rediscovering them manually
- keep consumer commentary task-first; keep startup, fallback, and retained-packet history implicit, and skip prior degraded-start history unless it remains the current blocker
- if the final handoff benefits from naming Odylith, use at most one short `Odylith assist:` line; prefer `**Odylith assist:**` when Markdown formatting is available. Lead with the user win, frame the edge against `odylith_off` or the broader unguided path when the evidence supports it, and back it with concrete observed counts, measured deltas, or validation outcomes while keeping it soulful, friendly, authentic, and factual
- keep widening fail-closed when `selection_state` is weak or `full_scan_recommended=true`
- preserve retained routing data when handing off to orchestration
- reserve explicit `serve` for intentionally warm repeated loops
- Keep delivery-intelligence and shell refresh deterministic when the persisted Tribunal reasoning artifact is missing; explicit provider-backed reasoning belongs to dedicated reasoning and briefing flows, not the refresh hot path.

## Canonical Commands

```bash
./.odylith/bin/odylith start --repo-root .
./.odylith/bin/odylith context --repo-root . <exact-ref>
./.odylith/bin/odylith query --repo-root . "<text>"
./.odylith/bin/odylith context-engine --repo-root . status
./.odylith/bin/odylith context-engine --repo-root . doctor
./.odylith/bin/odylith context-engine --repo-root . impact <paths...>
./.odylith/bin/odylith context-engine --repo-root . architecture <paths...>
./.odylith/bin/odylith context-engine --repo-root . governance-slice --working-tree
./.odylith/bin/odylith context-engine --repo-root . session-brief --working-tree --working-tree-scope session --session-id <id> --claim-path <path>
./.odylith/bin/odylith context-engine --repo-root . benchmark --json
./.odylith/bin/odylith context-engine --repo-root . serve --watcher-backend auto
```

## Rules

- Use `query` only after concrete nouns, ids, or path tokens are already known.
- Read `retrieval_plan`, `guidance_brief`, `packet_quality`, `packet_metrics`, and `routing_handoff` literally before delegating from a packet.
- If `diagram_watch_gaps` or `full_scan_recommended` appears, use the packet's printed fallback command first and then read the named source directly before widening further.
