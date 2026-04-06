# compass-timeline-stream

Use when logging bounded Compass timeline events for decisions, implementation updates, or execution statements.

## Canonical Commands

```bash
./.odylith/bin/odylith compass log --repo-root . --kind decision --summary "<decision>"
./.odylith/bin/odylith compass log --repo-root . --kind implementation --summary "<implementation update>"
./.odylith/bin/odylith compass update --repo-root . --statement "<current execution state>"
```

## Rules

- Keep summaries crisp and engineering-meaningful.
- Include workstream, component, and artifact links whenever they are known.
- Treat timeline events as additive runtime evidence, not source-of-truth records.
