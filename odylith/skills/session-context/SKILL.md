# Session Context

Use this skill when a session needs a grounded restart, a dirty-session delta, or a handoff summary without re-reading the whole repo, and when the agent needs to carry intent, constraints, validation obligations, and governance context forward instead of rediscovering them.

## Default Flow
- start from exact seeds when possible
- start a grounded turn with `odylith start`; use `odylith context` when you are restarting from one exact workstream, component, or path
- keep commentary task-first; describe narrowing, exact-ref lookup, or context recovery instead of narrating startup or retained-packet history, and skip prior degraded-start history unless it is the current blocker
- keep Odylith ambient by default during work; weave recovered context into ordinary updates and only break out explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` lines when the signal is genuinely worth the interruption
- reserve Odylith-by-name closeout text for one optional `Odylith Assist:` line; prefer `**Odylith Assist:**` when Markdown formatting is available. Lead with the user win, link updated governance ids inline when they were actually changed, frame the edge against `odylith_off` or the broader unguided path when the evidence supports it, and back it with concrete observed counts, measured deltas, or validation outcomes while keeping it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Silence is better than filler.
- prefer session-aware packets over broad lexical recall
- recover active intent, constraints, validation obligations, linked workstreams, components, diagrams, and bugs before substantive edits
- keep outstanding risks and validation obligations visible
- when carrying Compass or session memory forward, preserve the non-negotiable Compass voice contract from [Briefs Voice Contract](../registry/source/components/briefs-voice-contract/CURRENT_SPEC.md): friendly grounded maintainer narration, calm and simple human judgment, quiet celebration where earned, calm reassurance when facts support it, and no stock framing, workstream roll calls, repeated window leads, canned next/why/timing wrappers, rhetorical benchmark challenges, stagey metaphor, or house phrases
- preserve the cost contract too: Compass session carry-forward should lean on existing deterministic timeline and runtime memory, reuse exact cached live briefs when they match, and never turn an ordinary restart into a foreground provider refresh
- refresh session/Compass context after major decisions so later turns inherit real repo memory

## Canonical Commands

```bash
./.odylith/bin/odylith start --repo-root .
./.odylith/bin/odylith context --repo-root . <exact-ref>
./.odylith/bin/odylith context-engine --repo-root . session-brief --working-tree --working-tree-scope session --session-id <id> --intent "<intent>" --claim-path <path>
./.odylith/bin/odylith context-engine --repo-root . governance-slice --working-tree --working-tree-scope session --session-id <id> --claim-path <path>
./.odylith/bin/odylith compass log --repo-root . --kind implementation --summary "<intent-first update>"
```
