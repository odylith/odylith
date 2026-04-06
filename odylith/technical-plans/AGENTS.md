# Technical Plans AGENTS

Scope: applies to all files under `odylith/technical-plans/`.

## Purpose
- Keep technical planning artifacts easy to find, current, and auditable.
- Separate active work from historical records.

## Ownership
- These plan records are repo-local Odylith truth for the current repository.
- In the public Odylith repo, they govern Odylith product work directly.
- In repos that carry Odylith under `odylith/`, they govern Odylith-governed work for that repository without taking ownership of the surrounding repo's non-Odylith source of truth.
- In consumer repos diagnosing Odylith product issues, these plan files are read-only: prepare a maintainer-ready plan payload instead of editing local Odylith plans.

## Folder Contract
- `odylith/technical-plans/in-progress/`: active plans only (`Status: In progress`).
- `odylith/technical-plans/parked/YYYY-MM/`: inactive-but-not-done plans (`Status: Parked`).
- `odylith/technical-plans/done/YYYY-MM/`: completed plans with date-prefixed filenames.
- `odylith/technical-plans/done/legacy/`: completed plans without date-prefixed filenames.
- `odylith/technical-plans/INDEX.md`: navigation + active registry.
- `odylith/technical-plans/AGENTS.md`: this policy file.
