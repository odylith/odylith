# Odylith Registry Validate

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes
`$odylith-registry-validate` or asks to validate Registry component inventory
contracts.

1. Run `./.odylith/bin/odylith validate component-registry --repo-root .`.
2. Report the contract result, component counts, and any critical policy
   finding.
3. Keep follow-up bounded to the surfaced Registry contract issue.
