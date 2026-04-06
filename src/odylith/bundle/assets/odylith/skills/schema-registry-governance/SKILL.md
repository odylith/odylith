# schema-registry-governance

Use when registry-governance work touches schema-bearing contracts, component registration rules, or traceability obligations.

## Canonical Commands

```bash
odylith sync --repo-root . --force
odylith sync --repo-root . --check-only --check-clean --registry-policy-mode enforce-critical --enforce-deep-skills
```

## Rules

- Keep registry policy fail-closed.
- Reconcile component specs, registry truth, and governed surfaces together.
