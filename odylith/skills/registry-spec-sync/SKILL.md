# registry-spec-sync

Use when component-spec traceability, requirements synchronization, or Registry/detail parity needs repair.

## Lane Boundary
- `./.odylith/bin/odylith` chooses how Odylith runs.
- It does not decide which files the agent may edit.
- In consumer repos, repo-code validation still belongs to the consumer
  toolchain.
- In the Odylith product repo, live unreleased `src/odylith/*` execution
  belongs only to detached `source-local` inside maintainer mode.

## Canonical Commands

```bash
./.odylith/bin/odylith governance sync-component-spec-requirements --repo-root . --component <component_id_or_alias>
./.odylith/bin/odylith governance sync-component-spec-requirements --repo-root . --check-only
./.odylith/bin/odylith sync --repo-root . --force
./.odylith/bin/odylith sync --repo-root . --check-only --check-clean
```

## Rules

- Keep component specs, Registry detail views, and local truth in the same change.
- Do not hand-edit generated Registry artifacts when the sync pipeline owns them.
