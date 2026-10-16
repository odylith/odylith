# Radar Source AGENTS

## Governance-Learning
- Before changing or validating this surface for a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first.
- Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed.
- Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

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
- New idea specs must carry grounded core detail in `## Problem`,
  `## Customer`, `## Opportunity`, `## Product View`, and
  `## Success Metrics`. Placeholder text, title-derived boilerplate, and
  generic backlog-create defaults are invalid workstream truth.
- Human-visible Radar copy must be plain-English, grammatical, non-repetitive,
  and clear about the problem, customer, intended outcome, and evidence of
  success. If the reader cannot quickly tell what problem the workstream
  solves, the record is too thin even if the fields are present.
- Use `odylith backlog create` with the required grounded core-detail flags for
  new backlog ids. If an existing workstream is hollow, retrofill the source
  record from the bound plan or implementation evidence before refreshing
  Radar.
