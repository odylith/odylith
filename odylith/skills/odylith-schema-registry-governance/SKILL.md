# odylith-schema-registry-governance

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

Use when registry-governance work touches schema-bearing contracts, component registration rules, or traceability obligations.

## Canonical Commands

```bash
odylith sync --repo-root . --force
odylith sync --repo-root . --check-only --check-clean --registry-policy-mode enforce-critical --enforce-deep-skills
```

## Rules

- Keep registry policy fail-closed.
- Reconcile component specs, registry truth, and governed surfaces together.
