# casebook-bug-preflight

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

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
