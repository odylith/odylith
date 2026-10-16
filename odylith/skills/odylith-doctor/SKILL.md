# Odylith Doctor

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes `$odylith-doctor` or asks
to verify or repair the current Odylith install.

1. Run `./.odylith/bin/odylith doctor --repo-root .` for inspection.
2. Add `--repair` only when the user explicitly asks for repair or when the
   current task is clearly repair-authorized.
3. Add `--reset-local-state` only when the user explicitly wants a stronger
   local-state reset.
4. Report the verified posture or blocker instead of retrying blindly.
