# AGENTS.md

## Governance-Learning
- Before changing or validating this surface for a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first.
- Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed.
- Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Registry source is surface-owned truth.

- Keep the authoritative product component inventory in `component_registry.v1.json`.
- Keep the canonical per-component dossiers under `components/<component-id>/`.
- Treat `components/<component-id>/CURRENT_SPEC.md` as the living current spec for that component.
- Treat `components/<component-id>/FORENSICS.v1.json` as the Registry-generated forensic sidecar for that component.
- In consumer repos diagnosing Odylith product issues, Registry source is read-only: prepare component-ready maintainer evidence instead of editing local Odylith Registry truth.
- Do not relocate Registry source into a shared docs bucket.
- Update Registry source through the owning governance flows and `odylith sync`, not by inventing duplicate component-spec ledgers elsewhere.
- Human-visible Registry copy must be simple, grammatical, and specific to the
  component. A component spec should explain ownership, boundary, inputs,
  outputs, collaborators, exclusions, and proof obligations without repeating
  the same boilerplate across every component.
