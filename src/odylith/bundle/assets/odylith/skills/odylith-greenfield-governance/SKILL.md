# Odylith Greenfield Governance

Use this skill when the operator asks Odylith to build, govern, plan, or
architect a new project before source code exists.

1. Do not refuse merely because the repo has no app source. Greenfield intent
   is valid proposal evidence, not source evidence.
2. Run the provider-free proposal path:
   `./.odylith/bin/odylith greenfield propose --repo-root . --prompt "<operator request>"`.
3. Render the proposal in normal chat: backlog candidates, program waves,
   release plan, planned Registry components, draft Atlas diagrams,
   assumptions, risks, validation strategy, and open questions.
4. Do not write records until the operator confirms the proposal or gives
   explicit edits. On confirmation, run:
   `./.odylith/bin/odylith greenfield apply --repo-root . --proposal-file <proposal.json> --confirm --release next`.
5. Preserve the evidence boundary: observed source, user intent, and Odylith
   assumptions must stay distinct. Science and math projects need validation
   obligations for datasets, units, tolerances, reproducibility, derivations,
   and reference outputs instead of invented scientific claims.
