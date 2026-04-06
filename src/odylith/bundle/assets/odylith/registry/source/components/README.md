# Component Dossiers

Each folder under this tree is the Registry-owned dossier for one tracked
component.

## Current layout
- `CURRENT_SPEC.md`
  The canonical living spec for the component, including feature updates.
- `FORENSICS.v1.json`
  A Registry-generated forensic snapshot built from mapped timelines,
  traceability, and forensic-coverage state.

The current spec remains the authoritative contract and feature-update record.
The forensic sidecar is derived evidence, not hand-authored source.

## Why this is a folder
- Every tracked component gets one stable dossier path under
  `components/<component-id>/`.
- The spec, forensics, and future component-owned sidecars stay colocated.
- Surface components and engine components share the same storage contract even
  though the manifest keeps them in separate categories.
- Registry tooling can read or regenerate one dossier without guessing file
  naming conventions from a flat directory.
