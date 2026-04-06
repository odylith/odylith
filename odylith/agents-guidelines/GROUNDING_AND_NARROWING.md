# Grounding And Narrowing

- In Odylith repos, Codex and Claude Code should reach for the repo-local Odylith entrypoint before agent-native repo search.
- Use raw repo search only to seed Odylith when the prompt and worktree provide no usable anchors, or when Odylith explicitly signals widening.
- Grounding narrows evidence; in consumer Odylith-fix requests it is not permission to patch `odylith/` or run repair, sync, upgrade, or dashboard-refresh flows.
- In consumer commentary, describe the work in task terms. Keep startup, fallback, and packet-selection internals implicit. If an earlier repo-local start attempt degraded but work can continue, do not narrate that history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never use control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real block requires it, or a lane distinction matters.
- At closeout, one short `Odylith assist:` line is optional. Prefer `**Odylith assist:**` when Markdown formatting is available. Lead with the user win, not Odylith mechanics. When the evidence supports it, frame the edge against `odylith_off` or the broader unguided path. Keep it soulful, friendly, authentic, and factual. Use only concrete observed counts, measured deltas, or validation outcomes; otherwise omit it.
- Separate prompt assembly into policy, routing, and payload layers; do not collapse them back into one broad baseline.
- Start narrow, not broad.
- Treat concrete paths, components, ids, and workstream references as seeds.
- Once seeded, stay on packet selection instead of bouncing back to coverage scans or host-native search.
- Keep the evidence cone small and deliberate.
- Broad shared/global files are weak routing evidence on their own.
- When the slice is broad or ambiguous, prefer a compact narrowing pass over a speculative context flood.
- If ambiguity remains, widen transparently instead of acting on incomplete scope.
