# Odylith Context Engine Operations

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

Use this skill when the task is about packet choice, daemon health, warmup posture, retrieval quality, or context-engine debugging.

## Lane Boundary
- Consumer lane uses Odylith's managed runtime for Odylith commands, but target
  repo validation still belongs to the consumer repo's own toolchain.
- Product-repo maintainer mode has:
  - pinned dogfood posture for shipped-runtime proof
  - detached `source-local` posture for live unreleased `src/odylith/*`
    execution
- File-edit authority follows repo scope, not interpreter choice.

## Default Flow
- check `status` or `doctor` first
- use `start` as the default first-turn entrypoint, then choose the smallest Odylith packet that matches the slice and stay on Odylith for most grounded work
- use `bootstrap`, `context`, `query`, `session-brief`, and `governance-slice` when you need grounded start-up, exact-ref lookup, or governed-surface context instead of rediscovering them manually
- keep consumer commentary task-first; keep startup, fallback, and retained-packet history implicit, and skip prior degraded-start history unless it remains the current blocker
- keep Odylith ambient by default during work; weave packet facts into ordinary updates and only emit explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` lines when that signal is strong enough to matter
- if the final handoff benefits from naming Odylith, use at most one short `Odylith Assist:` line; prefer `**Odylith Assist:**` when Markdown formatting is available. Lead with the user win, link updated governance IDs inline only when they actually changed, name affected governance-contract IDs from bounded request or packet truth when no governed file moved, frame the edge against `odylith_off` or the broader unguided path when the evidence supports it, and back it with concrete observed counts, measured deltas, or validation outcomes while keeping it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Silence is better than filler.
- keep widening fail-closed when `selection_state` is weak or `full_scan_recommended=true`
- preserve retained routing data when handing off to orchestration
- For Guidance Behavior slices, read the compact `guidance_behavior_summary`
  as packet availability evidence only. It may carry case ids, fingerprints,
  runtime-layer wiring, and validator commands across Context Engine,
  Execution Engine, Memory Contracts, intervention evidence, and Tribunal
  readouts, but the full validator still runs explicitly with
  `./.odylith/bin/odylith validate guidance-behavior --repo-root .`.
- reserve explicit `serve` for intentionally warm repeated loops
- Keep delivery-intelligence and shell refresh deterministic when the persisted Tribunal reasoning artifact is missing; explicit provider-backed reasoning belongs to dedicated reasoning and briefing flows, not the refresh hot path.
- When shared projection/compiler/backend reuse is in play, verify the
  provenance tuple and active derivation generation instead of trusting a warm
  cache by default.
- If reuse looks wrong, use `./.odylith/bin/odylith sync --repo-root . --debug-cache`
  and inspect the local debug manifest under
  `.odylith/cache/odylith-context-engine/` before widening further.

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
./.odylith/bin/odylith validate guidance-behavior --repo-root .
```

## Rules

- Use `query` only after concrete nouns, ids, or path tokens are already known.
- Read `retrieval_plan`, `guidance_brief`, `packet_quality`, `packet_metrics`, and `routing_handoff` literally before delegating from a packet.
- If `diagram_watch_gaps` or `full_scan_recommended` appears, use the packet's printed fallback command first and then read the named source directly before widening further.
