# AGENTS.md

Registry source is surface-owned truth.

- Keep the authoritative product component inventory in `component_registry.v1.json`.
- Keep the canonical per-component dossiers under `components/<component-id>/`.
- Treat `components/<component-id>/CURRENT_SPEC.md` as the living current spec for that component.
- Treat `components/<component-id>/FORENSICS.v1.json` as the Registry-generated forensic sidecar for that component.
- In consumer repos diagnosing Odylith product issues, Registry source is read-only: prepare component-ready maintainer evidence instead of editing local Odylith Registry truth.
- Do not relocate Registry source into a shared docs bucket.
- Update Registry source through the owning governance flows and `odylith sync`, not by inventing duplicate component-spec ledgers elsewhere.
