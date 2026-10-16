# Odylith Atlas Auto Update

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes
`$odylith-atlas-auto-update` or asks to refresh Atlas diagrams from
change-watch metadata.

1. Run `./.odylith/bin/odylith atlas auto-update --repo-root .`.
2. If Atlas auto-update reports no changed paths, say so plainly.
3. If freshness or render gates fail, surface the exact blocker and next
   command instead of widening the task.
