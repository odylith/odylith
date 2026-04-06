# Registry Source

Registry source is the product-owned component system of record.

## What lives here
- `component_registry.v1.json`
  The authoritative inventory, linkage manifest, and category split between
  `governance_engine` and `governance_surface`.
- `components/<component-id>/CURRENT_SPEC.md`
  The canonical current spec for each tracked component.
- `components/<component-id>/FORENSICS.v1.json`
  The Registry-generated forensic snapshot for that component.

## Why this exists
Registry should let a developer answer one question in one place: what is this
component, why is it tracked, and what is its current contract right now.

That means the component inventory, canonical current specs, and Registry-owned
forensic sidecars all live under `odylith/registry/source/` instead of being
split across unrelated surface/runtime folders.

## Why one folder per component
Registry tracks components as dossiers, not as one flat pile of Markdown.

- `CURRENT_SPEC.md` carries the living contract and feature history.
- `FORENSICS.v1.json` carries the derived evidence snapshot.
- Future sidecars can be added without renaming or colliding with other
  components.
- Tooling can glob `components/<component-id>/` and treat every dossier the
  same way regardless of category.
