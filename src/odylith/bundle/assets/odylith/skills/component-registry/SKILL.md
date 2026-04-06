# component-registry

Use when refreshing, validating, or auditing the Registry surface and its linked component specs, or when execution reveals an untracked or under-specified system boundary that Odylith should start governing.

## Lane Boundary
- In consumer repos, use `./.odylith/bin/odylith` for Registry/governance
  commands and use the consumer repo's own toolchain for repo-code validation.

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
