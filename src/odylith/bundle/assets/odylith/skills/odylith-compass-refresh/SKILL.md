# Odylith Compass Refresh

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes `$odylith-compass-refresh`
or asks to refresh Compass and wait for the current pass to settle.

1. Run `./.odylith/bin/odylith compass deep-refresh --repo-root .`.
2. Report whether the refresh completed, deferred, or surfaced a provider or
   runtime blocker.
3. If the refresh is blocked, summarize the blocker instead of retrying
   blindly.
