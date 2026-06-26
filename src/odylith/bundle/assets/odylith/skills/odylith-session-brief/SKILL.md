# Odylith Session Brief

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes `$odylith-session-brief`
or asks for a concise session brief grounded in current Odylith state.

1. Run `./.odylith/bin/odylith session-brief --repo-root .`.
2. Use current workstream, Compass, Casebook, and validation evidence that
   already exists.
3. Summarize what moved, what is blocked, and the next concrete move.
4. Prefer grounded evidence over narration flourishes.
