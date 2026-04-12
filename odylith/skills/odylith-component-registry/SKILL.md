# odylith-component-registry

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

Use when refreshing, validating, or auditing the Registry surface and its linked component specs, or when execution reveals an untracked or under-specified system boundary that Odylith should start governing.

## Lane Boundary
- In consumer repos, use `./.odylith/bin/odylith` for Registry/governance
  commands and use the consumer repo's own toolchain for repo-code validation.
- In the Odylith product repo's maintainer mode, pinned dogfood is the default
  proof posture and detached `source-local` is the explicit dev posture for
  live source execution.

## Canonical Commands

```bash
./.odylith/bin/odylith governance sync-component-spec-requirements --repo-root . --component <component_id_or_alias>
./.odylith/bin/odylith governance sync-component-spec-requirements --repo-root . --check-only
./.odylith/bin/odylith validate component-registry --repo-root . --policy-mode enforce-critical --enforce-deep-skills
./.odylith/bin/odylith sync --repo-root . --force
./.odylith/bin/odylith sync --repo-root . --check-only --check-clean --registry-policy-mode enforce-critical --enforce-deep-skills
```

## Rules

- Search the existing component inventory first and extend, reopen, or deepen an existing component before adding a duplicate entry.
- Keep the component registry deeply linked to Radar, Atlas, Compass, and local component specs.
- Prefer the sync pipeline over hand-editing generated Registry artifacts.
- Add `--deep-skill-components <component>` when enforcing a specific deep-skill surface such as `msk` or `kafka-topic`.
- Meaningful Compass events must map to at least one component through explicit tags or deterministic inference.
- Keep candidate-versus-curated decisions explicit; do not silently promote auto-derived tokens into first-class components.
- If no component exists for a materially important surface, suggest or create a reviewed `candidate` entry in the same turn; promote it to first-class only when the evidence is strong enough.
- When a component exists but its living spec is thin, deepen it with technically specific boundary, responsibility, interface, control, validation, and feature-history detail instead of leaving a placeholder.
