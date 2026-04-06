# Radar Source AGENTS

Scope: applies to all files under `odylith/radar/source/`.

## Purpose
- Maintain the canonical workstream backlog and ranking model for the current repository's Odylith governance surfaces.

## Ownership
- Radar source records are repo-local Odylith truth for the current repository.
- Odylith owns the schema, templates, guidance, and render contract for this surface.
- In consumer repos diagnosing Odylith product issues, Radar source is read-only: gather workstream and prioritization evidence, then hand it off instead of editing local Odylith backlog truth.
- Keep the workstream source under `odylith/radar/source/` instead of scattering it across external docs buckets or duplicate ledgers.

## Contract
- `odylith/radar/source/INDEX.md` is the canonical ranked workstream index.
- Idea specs live under `odylith/radar/source/ideas/`.
- Program files live under `odylith/radar/source/programs/`.
- Templates and policy live under `odylith/radar/source/templates/` and `odylith/radar/source/policy/`.
