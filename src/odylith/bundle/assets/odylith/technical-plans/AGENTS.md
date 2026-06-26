# Technical Plans AGENTS

## Governance-Learning
- Before changing or validating this surface for a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first.
- Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed.
- Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

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
- There is no `odylith/technical-plans/source/` directory. `odylith plan
  --help` is a read-only command guide, not a plan writer. Use
  `odylith governance ...` and `odylith validate plan-* ...` for
  technical-plan maintenance and validation.
- Human-visible plan copy must be simple, grammatical, and directly useful for
  starting or reviewing implementation: name the slice, target files or
  modules, proof gates, validation commands, blockers, and stop conditions
  without clipped titles or boilerplate.
