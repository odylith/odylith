# Atlas Source AGENTS

Scope: applies to all files under `odylith/atlas/source/`.

## Purpose
- Keep Atlas diagram source and catalog truth in the Atlas surface itself.

## Ownership
- Atlas diagram source is repo-local Odylith truth for the current repository.
- Odylith owns the schema, guidance, and render contract for this surface.
- In consumer repos diagnosing Odylith product issues, Atlas source is
  read-only: collect diagram ids, source paths, and stale or parse evidence
  for handoff instead of editing local Atlas truth.
- Do not relocate Atlas source into a shared docs bucket.

## Contract
- `odylith/atlas/source/catalog/diagrams.v1.json` is the diagram inventory.
- Mermaid source files under this tree are the authoritative topology/source records for the current repository's Odylith-governed surfaces.
