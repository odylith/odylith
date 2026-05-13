# Odylith Greenfield Governance

Use this skill when the operator asks Odylith to build, govern, plan, or
architect a new project before source code exists.

1. Do not refuse merely because the repo has no app source. Greenfield intent
   is valid proposal evidence, not source evidence.
2. Run the Product Intent Confirmation path:
   `./.odylith/bin/odylith greenfield propose --repo-root . --prompt "<operator request>"`.
3. Treat the default CLI text as the host reasoning contract, not the
   interpretation itself. The host must write the Product Intent Confirmation
   in chat from live reasoning: what the product is, who the human actors are,
   which external and internal systems matter, what assumptions are being made,
   which ambiguities change the proposal, and a clear next-step block:
   confirm to expand into the proposal contract, edit to correct the
   interpretation, or reject to stop with no records written.
   It must not generate backlog, Registry, Atlas, release waves, validation
   obligations, or proposal JSON before the operator confirms the
   interpretation.
4. In chat, do not rely on collapsed Bash/tool output as the only visible
   confirmation. Do not replace live product reasoning with a generic
   "apply as-is, revise, or export JSON" menu. If the transcript collapses,
   write the short Product Intent Confirmation yourself. When the CLI returns
   proposal stdout directly, do not hide it behind collapsed tool output or
   replace it with a thin host-written summary; surface the actual confirmation
   or proposal content that matters.
5. After the operator confirms or edits the intent, use
   `greenfield propose --confirm-intent` for the complete proposal schema and
   proof contract. Treat that stdout or its `--format json` output as the
   full host-facing handoff. Do not search `src/odylith`, `.odylith`,
   `odylith/skills`, installed bundle files, local examples, or Python modules
   to discover schema fields after confirmation. The host authors the proposal
   JSON from the confirmed intent and source posture, usually as
   `odylith-greenfield-proposal.json`. This is the only point where
   every workstream, component, architecture view, wave, risk, validation
   obligation, memory prior, and transfer prior should exist.
6. Do not write records until the operator confirms the host-authored
   proposal. Prompt-only `greenfield create` is not the path for greenfield
   truth. Apply the accepted proposal with
   `./.odylith/bin/odylith greenfield apply --repo-root . --proposal-file odylith-greenfield-proposal.json --confirm --release 0.0.1`.
   `greenfield apply` runs deterministic validation, the Tribunal write gate,
   project-record writes, and the batched visibility refresh before printing
   the handoff.
7. Preserve the evidence boundary: observed source, user intent, and Odylith
   assumptions must stay distinct. For consumer apps, include proportional
   security, privacy, abuse, accessibility, data-retention, compliance, and
   operational risk posture instead of generic risk copy. For science and math, reason from the
   domain named by the user and propose correctness obligations such as proof
   checking, reproducibility, units, tolerances, derivation review, datasets,
   peer review, or validation fixtures only when they actually fit.
8. For vague or broad prompts, preserve the project-first and
   program-formation contract without forcing a fixed bucket: show the parent
   workstream, child-boundary strategy, wave-to-workstream policy,
   provisional release selector, decisive assumptions, customization options,
   and coding-readiness gates before asking the operator to confirm or revise.
   Do not rush to `start B-***`; greenfield apply creates accepted project
   truth, and coding begins only after the operator accepts the product gates
   and a child workstream has a technical plan.
9. Keep latency low: rely on `greenfield apply` for the
   final batched visibility refresh instead of running separate refresh commands
   after each artifact family.
