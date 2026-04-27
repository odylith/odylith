# Odylith Backlog Validate

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
