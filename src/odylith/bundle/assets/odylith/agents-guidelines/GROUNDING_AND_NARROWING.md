# Grounding And Narrowing

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

- In Odylith repos, Codex and Claude Code should reach for the repo-local Odylith entrypoint before agent-native repo search.
- Use raw repo search only to seed Odylith when the prompt and worktree provide no usable anchors, or when Odylith explicitly signals widening.
- Grounding narrows evidence; in consumer Odylith-fix requests it is not permission to patch `odylith/` or run repair, sync, upgrade, or dashboard-refresh flows.
- In consumer commentary, describe the work in task terms. Keep startup, fallback, and packet-selection internals implicit. If an earlier repo-local start attempt degraded but work can continue, do not narrate that history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never use control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real block requires it, or a lane distinction matters.
- Keep Odylith ambient by default: weave grounded facts into ordinary task updates, and only break out explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels when the point is sharp enough to earn the interruption.
- At closeout, one short `Odylith Assist:` line is optional. Prefer `**Odylith Assist:**` when Markdown formatting is available. Lead with the user win, link updated governance IDs inline only when they actually changed, name affected governance-contract IDs from bounded request or packet truth when no governed file moved, and ground the line in concrete observed counts, measured deltas, or validation outcomes. When the evidence supports it, frame the edge against `odylith_off` or the broader unguided path. Keep it crisp, authentic, clear, simple, insightful, soulful, friendly, free-flowing, human, and factual. Silence is better than filler. At most one supplemental closeout line may appear, chosen from `Odylith Risks:`, `Odylith Insight:`, or `Odylith History:` when the signal is real.
- Separate prompt assembly into policy, routing, and payload layers; do not collapse them back into one broad baseline.
- Start narrow, not broad.
- Treat concrete paths, components, ids, and workstream references as seeds.
- Once seeded, stay on packet selection instead of bouncing back to coverage scans or host-native search.
- Keep the evidence cone small and deliberate.
- Broad shared/global files are weak routing evidence on their own.
- When the slice is broad or ambiguous, prefer a compact narrowing pass over a speculative context flood.
- If ambiguity remains, widen transparently instead of acting on incomplete scope.
