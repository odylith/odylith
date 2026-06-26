# Odylith Backlog Validate

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes
`$odylith-backlog-validate` or asks to validate Radar backlog and plan linkage
contracts.

1. Run `./.odylith/bin/odylith validate backlog-contract --repo-root .`.
2. Report the validated counts or the failing contract plainly.
3. Treat core-detail failures as real authoring defects: Problem, Customer,
   Opportunity, Product View, and Success Metrics must be grounded and cannot
   be placeholder or backlog-create boilerplate.
4. If the validator fails, keep the follow-up bounded to the contract error
   instead of broad governance cleanup.
