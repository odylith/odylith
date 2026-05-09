# Odylith Greenfield Governance

Use this skill when the operator asks Odylith to build, govern, plan, or
architect a new project before source code exists.

1. Do not refuse merely because the repo has no app source. Greenfield intent
   is valid proposal evidence, not source evidence.
2. Run the proposal preview path:
   `./.odylith/bin/odylith greenfield propose --repo-root . --prompt "<operator request>"`.
3. Treat the default CLI text as a compact review gate, not the deep record dump.
   It should show the product interpretation, direction choices, non-goals,
   first release ambition, candidate boundaries, review views, and proof gates
   in product language. If the operator or reviewer needs the complete accepted
   object, use `greenfield propose --format json`; the JSON is where every
   workstream, component, architecture view, wave, risk, validation obligation,
   memory prior, and transfer prior can live without flooding the first review.
   Do not hand-build `odylith-greenfield-proposal.json`, do not reconstruct JSON
   from prose, and do not patch schema fields in front of the operator. Use host
   reasoning only to critique, amend, or answer open questions when the operator
   asks for changes.
4. Do not write records until the operator confirms the proposal or gives
   explicit edits. On confirmation, prefer the one-command path:
   `./.odylith/bin/odylith greenfield create --repo-root . --prompt "<operator request>" --release 0.0.1 --confirm`.
   If a workflow explicitly needs a proposal file, obtain it from
   `greenfield propose --format json` and pass that canonical JSON to
   `greenfield apply`; never author the file by hand. `create` and `apply` run
   deterministic validation, the Tribunal write gate, project-record writes,
   and the batched visibility refresh before printing the handoff.
5. Preserve the evidence boundary: observed source, user intent, and Odylith
   assumptions must stay distinct. For consumer apps, include proportional
   security, privacy, abuse, accessibility, data-retention, compliance, and
   operational risk posture instead of generic risk copy. For science and math, reason from the
   domain named by the user and propose correctness obligations such as proof
   checking, reproducibility, units, tolerances, derivation review, datasets,
   peer review, or validation fixtures only when they actually fit.
6. For vague or broad prompts, preserve the project-first and
   program-formation contract without forcing a fixed bucket: show the parent
   workstream, child-boundary strategy, wave-to-workstream policy,
   provisional release selector, decisive assumptions, customization options,
   and coding-readiness gates before asking the operator to confirm or revise.
   Do not rush to `start B-***`; greenfield apply creates the governed project
   truth, and coding begins only after the operator accepts the product gates
   and a child workstream has a technical plan.
7. Keep latency low: rely on `greenfield create` or `greenfield apply` for the
   final batched visibility refresh instead of running separate refresh commands
   after each artifact family.
