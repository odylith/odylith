# CLAUDE.md

## Governance-Learning
- Before changing or validating this surface for a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first.
- Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed.
- Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

@AGENTS.md

## Claude Code

- This scoped file ensures Claude loads the same Compass runtime subtree contract as other hosts.
- Prefer the `odylith-compass-briefer` subagent or `/odylith-compass-refresh-wait` when the slice is brief state, runtime freshness, or Compass blockers.
- Treat `agent-stream.v1.jsonl` as the host-neutral live execution stream. Legacy `codex-stream.v1.jsonl` exists only for read compatibility during migration.
- Most files here are derived runtime state. Diagnose from them freely, but do not treat them as the place to author backlog, plan, registry, atlas, or bug truth.
- For broader Odylith context outside this subtree, follow `odylith/AGENTS.md` and the repo-root bridge.
- Do not treat this file as source-of-truth runtime history; it is only the Claude companion for this scope.
