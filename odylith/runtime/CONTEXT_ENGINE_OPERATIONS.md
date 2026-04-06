# Odylith Context Engine Operations

Use this guide for the Odylith runtime lifecycle in the current repo.

## Primary Commands

```bash
odylith context-engine --repo-root . status
odylith context-engine --repo-root . doctor
odylith context-engine --repo-root . warmup
odylith context-engine --repo-root . bootstrap-session --working-tree --working-tree-scope session --session-id <id>
odylith context-engine --repo-root . impact <paths...>
odylith context-engine --repo-root . architecture <paths...>
```

## Operating Rules

- Treat Odylith as a path-scoped accelerator over repo-local truth, not a substitute for direct source reads on broad or ambiguous slices.
- If a packet reports `full_scan_recommended: true` or exposes diagram-watch gaps, widen back to direct repo reads before implementation.
- Prefer `impact` for explicit coding slices, `architecture` for topology-sensitive work, and `bootstrap-session` for new or shared-dirty sessions.
- `status` and `doctor` are the supported runtime lifecycle commands; avoid repo-local module entrypoints.

## Validation

```bash
odylith sync --repo-root . --force
odylith sync --repo-root . --check-only --check-clean
```
