# odylith-registry-spec-sync

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

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
