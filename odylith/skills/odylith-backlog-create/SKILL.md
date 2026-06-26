# Odylith Backlog Create

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill only when the user explicitly invokes `$odylith-backlog-create`
or asks to create one or more Radar backlog workstreams.

1. Search existing Radar, plans, bugs, and recent Compass context first so you
   extend the right record instead of duplicating it.
2. Gather grounded core detail before authoring: Problem, Customer,
   Opportunity, Product View, and Success Metrics. Do not use title-derived
   boilerplate, `TBD`, `Details.`, or other placeholders.
   The visible workstream title and body must be simple, easy to understand,
   legible, grammatically coherent, and clear about the problem being solved,
   who benefits, what changes, and what evidence would prove success.
   Exception: when the user asks for a new greenfield project from intent
   only, use `odylith greenfield propose` first for Product Intent
   Confirmation. Only after the operator confirms the interpretation should
   `odylith greenfield propose --confirm-intent` or confirmed create
   draft missing fields, program waves, and release planning.
3. Run `./.odylith/bin/odylith backlog create --repo-root .` with `--title`,
   `--problem`, `--customer`, `--opportunity`, `--product-view`, and
   `--success-metrics`.
4. Keep the new workstream tightly scoped and tie it to the current slice.
5. Run `./.odylith/bin/odylith validate backlog-contract --repo-root .` or the
   owned Radar refresh path before handoff when the record was created.
6. Report the created or extended backlog record and any required follow-on
   plan or validation work.
