# compass-executive

Use when you need Compass-driven executive or operator summaries over recent work, current execution, and next actions.

## Canonical Commands

```bash
odylith compass log --repo-root . --kind decision --summary "<decision>"
odylith compass log --repo-root . --kind implementation --summary "<implementation update>"
odylith compass update --repo-root . --statement "<current execution state>"
odylith sync --repo-root . --force
```

## Rules

- Keep Compass narrative concise, execution-meaningful, and grounded in local repo truth.
- Prefer Compass for recent activity and current execution posture, not as a replacement for direct bug/plan/workstream inspection.
