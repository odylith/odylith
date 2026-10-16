# CLAUDE.md

## Governance-Learning
- Before changing or validating this surface for a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first.
- Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed.
- Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

@AGENTS.md

## Claude Code

- This scoped file ensures Claude loads the same Radar subtree contract as other hosts.
- Prefer the `odylith-workstream` or `odylith-governance-scribe` subagent when the slice is primarily about workstream source truth.
- Extend an existing workstream before creating a new one. Use `/odylith-workstream-new` only when the slice is genuinely new and cannot truthfully attach to current Radar state.
- Edit workstream markdown under `ideas/` and let governed surface refresh rebuild the derived backlog artifacts.
- For broader Odylith context outside this subtree, follow `odylith/AGENTS.md` and the repo-root bridge.
- Do not treat this file as a workstream record; it is only the Claude companion for this scope.
