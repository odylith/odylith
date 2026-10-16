# Odylith Query

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes `$odylith-query` or asks
to search the local Odylith projection store after concrete anchors already
exist.

1. Confirm that a concrete noun already exists, such as a workstream,
   component, path, bug id, or diagram id.
2. Run `./.odylith/bin/odylith query --repo-root . "<terms>"`.
3. Use the result to narrow the next file reads, tests, or edits instead of
   expanding into broad unguided repo search.
4. Do not use this as a substitute for the initial Odylith grounding step.
