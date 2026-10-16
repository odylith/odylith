# Odylith Version

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes `$odylith-version` or
asks to inspect the pinned, active, and locally available Odylith versions.

1. Run `./.odylith/bin/odylith version --repo-root .`.
2. Report the active pinned runtime posture plainly.
3. When relevant, distinguish the active target release from the latest
   shipped release instead of collapsing them together.
