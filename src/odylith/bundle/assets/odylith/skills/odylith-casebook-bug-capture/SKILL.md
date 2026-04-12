# odylith-casebook-bug-capture

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

Use when capturing a new Casebook bug record or updating an open bug with fresh evidence, especially when a named failure mode or repeated-debug loop needs durable repo memory in the same turn.

## Rules

- Search for an existing bug first; update, reopen, or consolidate the existing record before creating a parallel duplicate.
- Give every new bug record a stable `Bug ID` in the `CB-###` sequence and keep that ID unchanged when the title, status, or file location evolves.
- Keep the bug narrative factual and reproduction-oriented.
- Link the affected workstream, components, tests, and artifacts explicitly.
- Link the affected diagrams, validation obligations, and next guardrails or preflight checks whenever they are known.
- Refresh governed Odylith surfaces after meaningful bug truth changes.

## Canonical Commands

```bash
./.odylith/bin/odylith compass log --repo-root . --kind implementation --summary "<bug capture update>"
./.odylith/bin/odylith sync --repo-root . --force
```
