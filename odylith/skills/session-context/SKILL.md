# Session Context

Use this skill when a session needs a grounded restart, a dirty-session delta, or a handoff summary without re-reading the whole repo, and when the agent needs to carry intent, constraints, validation obligations, and governance context forward instead of rediscovering them.

## Default Flow
- start from exact seeds when possible
- start a grounded turn with `odylith start`; use `odylith context` when you are restarting from one exact workstream, component, or path
- keep commentary task-first; describe narrowing, exact-ref lookup, or context recovery instead of narrating startup or retained-packet history, and skip prior degraded-start history unless it is the current blocker
- reserve Odylith-by-name closeout text for one optional `Odylith assist:` line; prefer `**Odylith assist:**` when Markdown formatting is available. Lead with the user win, frame the edge against `odylith_off` or the broader unguided path when the evidence supports it, and back it with concrete observed counts, measured deltas, or validation outcomes while keeping it soulful, friendly, authentic, and factual
- prefer session-aware packets over broad lexical recall
- recover active intent, constraints, validation obligations, linked workstreams, components, diagrams, and bugs before substantive edits
- keep outstanding risks and validation obligations visible
- refresh session/Compass context after major decisions so later turns inherit real repo memory

## Canonical Commands

```bash
./.odylith/bin/odylith start --repo-root .
./.odylith/bin/odylith context --repo-root . <exact-ref>
./.odylith/bin/odylith context-engine --repo-root . session-brief --working-tree --working-tree-scope session --session-id <id> --intent "<intent>" --claim-path <path>
./.odylith/bin/odylith context-engine --repo-root . governance-slice --working-tree --working-tree-scope session --session-id <id> --claim-path <path>
./.odylith/bin/odylith compass log --repo-root . --kind implementation --summary "<intent-first update>"
```
