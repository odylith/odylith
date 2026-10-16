# CLAUDE.md

## Governance-Learning
- Before changing or validating this surface for a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first.
- Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed.
- Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

@AGENTS.md

## Claude Code

- This scoped file ensures Claude loads the same Atlas subtree contract as other hosts.
- Prefer the `odylith-atlas-diagrammer` subagent or the diagram-catalog skill shim when the slice is mostly diagram or catalog work.
- Treat `.mmd` files and `catalog/diagrams.v1.json` as the canonical Atlas source surfaces. Keep rendered dashboard artifacts aligned, but do not treat them as source truth.
- For broader Odylith context outside this subtree, follow `odylith/AGENTS.md` and the repo-root bridge.
- Do not treat this file as architecture source truth; it is only the Claude companion for this scope.
