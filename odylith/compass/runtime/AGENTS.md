# Compass Runtime AGENTS

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
