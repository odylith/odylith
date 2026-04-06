# casebook-bug-capture

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
