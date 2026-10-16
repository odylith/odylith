# Odylith Start

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes `$odylith-start` or
directly asks to run the repo-local Odylith startup contract.

1. Run `./.odylith/bin/odylith start --repo-root .` for substantive work.
   Do not run `odylith context`, `odylith query`, `git status`, or broad
   repo search in parallel with this step; let startup finish first so the
   host transcript reflects the real grounding order.
2. If startup cannot narrow the slice but the user already named a workstream,
   bug, component, or path, follow with
   `./.odylith/bin/odylith context --repo-root . <ref>`.
3. Keep the next repo reads bounded to the resolved slice instead of widening
   into broad repo search immediately.
4. Summarize only the active slice and the next concrete move; do not narrate
   control-plane internals.
