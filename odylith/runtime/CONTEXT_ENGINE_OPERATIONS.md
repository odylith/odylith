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
odylith sync --repo-root . --debug-cache
```

## Operating Rules

- Treat Odylith as a path-scoped accelerator over repo-local truth, not a substitute for direct source reads on broad or ambiguous slices.
- If a packet reports `full_scan_recommended: true` or exposes diagram-watch gaps, widen back to direct repo reads before implementation.
- Prefer `impact` for explicit coding slices, `architecture` for topology-sensitive work, and `bootstrap-session` for new or shared-dirty sessions.
- `status` and `doctor` are the supported runtime lifecycle commands; avoid repo-local module entrypoints.
- Shared projection/compiler/backend reuse is only valid when the persisted
  provenance tuple still matches the current repo root, scope, fingerprint,
  code version, and active derivation generation when a sync session is live.
- During governed sync, derivation-input mutations must advance the active
  derivation generation immediately. Do not treat every generated HTML/JS write
  as a truth mutation, but do invalidate on Registry, Atlas catalog,
  traceability, and delivery-intelligence truth changes.
- Fail closed on reuse mismatch. Rebuild locally rather than trusting a stale
  substrate or cached payload.
- Use `odylith sync --repo-root . --debug-cache` and the local debug manifest
  under `.odylith/cache/odylith-context-engine/` when you need to explain why a
  substrate or surface was reused or rebuilt.

## Validation

```bash
odylith sync --repo-root . --force
odylith sync --repo-root . --check-only --check-clean
odylith sync --repo-root . --debug-cache --check-only --runtime-mode standalone
```
