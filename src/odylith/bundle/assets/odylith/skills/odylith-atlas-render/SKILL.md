# Odylith Atlas Render

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes `$odylith-atlas-render`
or asks to render Atlas from the Mermaid catalog.

1. Run `./.odylith/bin/odylith atlas render --repo-root .`.
2. Report whether Atlas rendered cleanly or surfaced a freshness blocker.
3. If freshness blocks the render, say which follow-up command is needed
   rather than retrying blindly.
