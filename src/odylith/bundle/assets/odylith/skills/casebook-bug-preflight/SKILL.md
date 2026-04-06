# casebook-bug-preflight

Use before any substantive fix, debug loop, or governed closeout slice that might need durable failure memory so the relevant bug history, workstream links, component links, and validation surfaces are grounded first.

## Canonical Commands

```bash
./.odylith/bin/odylith context-engine --repo-root . governance-slice --working-tree
./.odylith/bin/odylith context-engine --repo-root . impact <paths...>
./.odylith/bin/odylith sync --repo-root . --check-only --check-clean
```

## Rules

- Check existing Casebook entries before opening new bug work.
- Search the related workstream, components, diagrams, and validation obligations alongside the bug history so you can decide whether to update an existing bug, reopen it, or capture a genuinely new failure mode.
- Carry related bug ids or explicit `no related bug found` evidence into the active plan or handoff.
- If the slice already has a named failure mode or repeated-debug loop, escalate into `casebook-bug-capture` in the same turn instead of deferring durable bug memory.
