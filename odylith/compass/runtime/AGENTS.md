# Compass Runtime AGENTS

## Governance-Learning
- Before changing or validating this surface for a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first.
- Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed.
- Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Scope: applies to all files under `odylith/compass/runtime/`.

## Purpose
- Keep Compass runtime truth local to the Compass surface.

## Ownership
- Compass runtime files are repo-local Odylith truth for the current repository.
- Odylith owns the schema, guidance, and render contract for this surface.
- Do not relocate Compass runtime truth into a shared docs bucket.

## Contract
- `odylith/compass/runtime/agent-stream.v1.jsonl` is the canonical append-only execution/event stream.
- `odylith/compass/runtime/codex-stream.v1.jsonl` remains a legacy-compatible input during migration.
- `odylith/compass/runtime/current.v1.json` and `current.v1.js` are the latest rendered runtime snapshot.
- `odylith/compass/runtime/history/` preserves active historical runtime snapshots.
- `odylith/compass/runtime/history/archive/` keeps compressed older daily snapshots for explicit restore.
- Human-visible Compass copy must be concise, grammatical, and clear about
  current state, trusted evidence, blockers, and next action. Timeout,
  unavailable, and degraded states must say what happened and what will happen
  next without vague or decorative filler.
