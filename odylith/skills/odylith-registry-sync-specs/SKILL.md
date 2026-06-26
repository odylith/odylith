# Odylith Registry Sync Specs

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes
`$odylith-registry-sync-specs` or asks to sync mapped Compass requirement
evidence into component living specs.

1. Run `./.odylith/bin/odylith governance sync-component-spec-requirements --repo-root .`.
2. Report which components or forensics records updated.
3. If nothing changed, say that plainly instead of implying hidden work.
