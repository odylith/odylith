# Atlas Source AGENTS

## Governance-Learning
- Before changing or validating this surface for a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first.
- Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed.
- Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Scope: applies to all files under `odylith/atlas/source/`.

## Purpose
- Keep Atlas diagram source and catalog truth in the Atlas surface itself.

## Ownership
- Atlas diagram source is repo-local Odylith truth for the current repository.
- Odylith owns the schema, guidance, and render contract for this surface.
- In consumer repos diagnosing Odylith product issues, Atlas source is read-only: collect diagram ids, source paths, and stale or parse evidence for the maintainer instead of editing local Atlas truth.
- Do not relocate Atlas source into a shared docs bucket.

## Contract
- `odylith/atlas/source/catalog/diagrams.v1.json` is the diagram inventory.
- Mermaid source files under this tree are the authoritative topology/source records for the current repository's Odylith-governed surfaces.
- Human-visible Atlas copy must explain the diagram in project terms, not only
  topology mechanics. Titles, summaries, labels, and box descriptions must be
  concise, grammatical, and clear about what each actor, system, state,
  boundary, or proof object means.
