# Odylith Backlog Create

Use this skill only when the user explicitly invokes `$odylith-backlog-create`
or asks to create one or more Radar backlog workstreams.

1. Search existing Radar, plans, bugs, and recent Compass context first so you
   extend the right record instead of duplicating it.
2. Gather grounded core detail before authoring: Problem, Customer,
   Opportunity, Product View, and Success Metrics. Do not use title-derived
   boilerplate, `TBD`, `Details.`, or other placeholders.
   Exception: when the user asks for a new greenfield project from intent
   only, use `odylith greenfield propose` first. That proposal may draft the
   missing fields, program waves, and release plan with labeled assumptions,
   but final backlog writes still require confirmation.
3. Run `./.odylith/bin/odylith backlog create --repo-root .` with `--title`,
   `--problem`, `--customer`, `--opportunity`, `--product-view`, and
   `--success-metrics`.
4. Keep the new workstream tightly scoped and tie it to the current slice.
5. Run `./.odylith/bin/odylith validate backlog-contract --repo-root .` or the
   owned Radar refresh path before handoff when the record was created.
6. Report the created or extended backlog record and any required follow-on
   plan or validation work.
