# Odylith Context

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes `$odylith-context` or
asks to resolve a known Odylith anchor into the smallest useful local context.

1. Use this only after the current turn has run `odylith start`, or after a
   fresh session-start packet already exists and an exact anchor is known,
   such as a workstream id, bug id, component, diagram id, or repo path.
2. Do not run this in parallel with `odylith start`; startup is the serial
   gate and context is the follow-on exact-anchor packet.
3. Run `./.odylith/bin/odylith context --repo-root . <ref>`.
4. Summarize the resolved slice, the governed records or code paths it points
   at, and the next concrete implementation or validation move.
5. Do not widen into raw repo search until the context packet stops being
   sufficient.
