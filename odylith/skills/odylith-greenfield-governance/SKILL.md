# Odylith Greenfield Governance

Use this skill when the operator asks Odylith to build, govern, plan, or
architect a new project before source code exists.

1. Do not refuse merely because the repo has no app source. Greenfield intent
   is valid proposal evidence, not source evidence.
2. Run the host-reasoning contract path:
   `./.odylith/bin/odylith greenfield propose --repo-root . --prompt "<operator request>"`.
3. Use the active supported host's full reasoning to draft the proposal in normal
   chat. The CLI output is the evidence/schema/guardrail contract, not a
   canned in-code domain list. Render concrete backlog candidates, program waves,
   release plan, planned Registry components, draft Atlas diagrams, security
   and privacy posture, operational risks, validation strategy, assumptions,
   and open questions that are specific to the operator prompt. Always include
   one explicit umbrella parent workstream such as `WS-00 Govern <Project>`
   before child workstreams; child rows use `WS-01+` and should never masquerade
   as the program itself. Each draft Atlas diagram must include
   host-authored `mermaid_source`; Odylith validates and scaffolds the source
   after confirmation, but it must not invent the topology. Keep Mermaid
   sequence message text parser-safe by using words instead of semicolons in
   arrow labels. Default the first
   greenfield release target to `0.0.1` unless the operator provides a
   different release target, and identify the first-wave workstreams that should
   target that release. Make the proposal easy to operate: name the program,
   wave labels, release selector, targeted first-wave workstreams, impacted
   components, related diagram slugs, and proof gates in plain language. Also
   state what happens after apply: which child workstream starts coding first,
   what tests or browser proofs verify it, and which dashboard view confirms the
   program is ready for the next wave. Candidate Registry components must read
   like implementation runways, not placeholders: include the first child
   workstream, wave, release target, first coding slice, definition of done,
   dependency expectations, interface expectations, and verification commands.
   The umbrella parent gives program context; it is not the first coding anchor.
4. Do not write records until the operator confirms the proposal or gives
   explicit edits. On confirmation, run:
   `./.odylith/bin/odylith greenfield apply --repo-root . --proposal-file <proposal.json> --confirm --release 0.0.1`.
   Apply runs a deterministic greenfield Tribunal before writes, then refreshes
   Radar, Registry, Atlas, and Compass after the accepted artifacts are written.
5. Preserve the evidence boundary: observed source, user intent, and Odylith
   assumptions must stay distinct. For consumer apps, include proportional
   security, privacy, abuse, accessibility, data-retention, compliance, and
   operational risk posture instead of generic risk copy. For science and math, reason from the
   domain named by the user and propose correctness obligations such as proof
   checking, reproducibility, units, tolerances, derivation review, datasets,
   peer review, or validation fixtures only when they actually fit.
6. For vague or broad prompts, preserve the program-formation contract without
   forcing a fixed bucket: show the parent workstream, child-boundary
   strategy, wave-to-workstream policy, provisional release selector, and the
   decisive assumptions before asking the operator to confirm or revise.
7. Keep latency low: rely on `greenfield apply` for the final batched visibility
   refresh instead of running separate Radar, Registry, Atlas, or Compass refresh
   commands after each artifact family.
