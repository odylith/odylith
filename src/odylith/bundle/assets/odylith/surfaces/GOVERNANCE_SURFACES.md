# Odylith Governance Surfaces

Odylith owns the product behavior for Radar, Atlas, Compass, Registry,
Casebook, and the tooling shell while continuing to read repo truth in place.

Related product docs:

- `odylith/PRODUCT_COMPONENTS.md`
- `odylith/runtime/TRIBUNAL_AND_REMEDIATION.md`
- `odylith/OPERATING_MODEL.md`
- `odylith/registry/source/components/radar/CURRENT_SPEC.md`
- `odylith/registry/source/components/atlas/CURRENT_SPEC.md`
- `odylith/registry/source/components/compass/CURRENT_SPEC.md`
- `odylith/registry/source/components/registry/CURRENT_SPEC.md`
- `odylith/registry/source/components/casebook/CURRENT_SPEC.md`

## Canonical Commands

```bash
odylith sync --repo-root . --force
odylith sync --repo-root . --check-only --check-clean
odylith compass log --repo-root . --kind decision --summary "<summary>"
odylith compass update --repo-root . --statement "<current execution state>"
```

## Repo Truth Roots

- `odylith/radar/source/`
- `odylith/casebook/bugs/`
- `odylith/technical-plans/`
- `odylith/atlas/source/`
- `odylith/compass/runtime/`
- `odylith/registry/source/`

## Rules

- Do not hand-edit generated surface artifacts when a renderer or `odylith sync` owns them.
- Keep repo truth local; Odylith reads and renders it, but does not become the source of truth for it.
- Keep each governance surface's source inputs and generated artifacts in that surface's own subtree, while the canonical component dossier lives under `odylith/registry/source/components/`.
- Use the `odylith/` guidance tree for Odylith-owned product behavior and keep repo-root guidance authoritative for repo-owned paths outside `odylith/`.
