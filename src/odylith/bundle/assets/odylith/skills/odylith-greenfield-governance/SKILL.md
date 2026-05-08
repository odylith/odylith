# Odylith Greenfield Governance

Use this skill when the operator asks Odylith to build, govern, plan, or
architect a new project before source code exists.

1. Do not refuse merely because the repo has no app source. Greenfield intent
   is valid proposal evidence, not source evidence.
2. Run the canonical proposal path:
   `./.odylith/bin/odylith greenfield propose --repo-root . --prompt "<operator request>"`.
3. Treat the CLI proposal as apply-ready product output and a project-first
   control surface. Odylith builds the canonical proposal object, validates it
   against the apply contract, runs the greenfield Tribunal, and renders the
   human proposal from that same object. Review direction options,
   customization choices, architecture views, and coding-readiness gates before
   implementation planning starts.
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
   deterministic validation, the greenfield Tribunal, governed writes, and the
   batched Radar/Registry/Atlas/Compass refresh before printing the handoff.
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
7. Keep latency low: rely on `greenfield create` or `greenfield apply` for the
   final batched visibility refresh instead of running separate Radar, Registry,
   Atlas, or Compass refresh commands after each artifact family.
