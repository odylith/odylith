# Odylith Greenfield Governance

Use this skill when the operator asks Odylith to build, govern, plan, or
architect a new project before source code exists.

Governance-learning stays active during greenfield work. Every failed
post-confirm create, failed mechanism, bad generated artifact, semantic drift,
quality-gate miss, latency breach, or simulation defect must create or update Casebook
truth before the next simulation or fix pass; planned rearchitecture belongs
in Radar or technical plans, component-contract changes in Registry,
flow/topology changes in Atlas, and proof checkpoints in Compass. Before
fixing a greenfield bug, search existing Casebook and related governance
artifacts, read prior failed mechanisms, failed fix attempts, and guardrails,
do not repeat a fix path that already failed, and capture new
mechanism-level learning.

1. Do not refuse merely because the repo has no app source. Greenfield intent
   is valid proposal evidence, not source evidence.
2. Run the Product Intent Confirmation path:
   `./.odylith/bin/odylith greenfield propose --repo-root . --prompt "<operator request>"`.
3. Treat the default CLI text as the host reasoning contract, not the
   interpretation itself. The host must write the Product Intent Confirmation
   in chat from live reasoning. The visible confirmation must be sectioned
   Markdown, not one large paragraph and never a wall of prose: title, Product
   story, State object, First complete path, Human actors, External systems,
   Internal product systems, Critical assumptions, Ambiguities, Proof boundary,
   and a clear next-step block:
   confirm to expand into the proposal contract, edit to correct the
   interpretation, or reject to stop with no records written.
   Use short paragraphs for the story, state object, first path, and proof
   boundary. Use bullets for actors, systems, assumptions, and ambiguities.
   Do not wrap ordinary product, actor, state, or component names in code ticks
   or decorative bold markers.
   The confirmation and every created record must pass the clarity floor first:
   simple, easy to understand, legible, grammatically coherent, and clear.
   Product meaning comes before artifact mapping; clipped titles, malformed
   Markdown, repeated generic copy, or internal Odylith surface dumps are
   invalid greenfield narration.
   It must not generate backlog, Registry, Atlas, release waves, validation
   obligations, or proposal JSON before the operator confirms the
   interpretation.
4. In chat, do not rely on collapsed Bash/tool output as the only visible
   confirmation. Do not replace live product reasoning with a generic
   "apply as-is, revise, or export JSON" menu. If the transcript collapses,
   write the short Product Intent Confirmation yourself. After the operator
   confirms that intent, keep the proposal contract internal and surface only
   created records or validation/Tribunal blockers.
5. After the operator confirms or edits the intent, write the same visible
   Product Intent Confirmation to
   `.odylith/runtime/greenfield/confirmed-intent.md`, then run
   `greenfield create --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1`
   with the original prompt. Odylith first normalizes that Markdown into
   `.odylith/runtime/greenfield/confirmed-intent.json`, validates it, runs the
   bounded, provider-free post-confirm repair loop, runs the Tribunal write
   gate, writes records only after the final manifest passes, and refreshes
   readable views. Do not search `src/odylith`.
   Do not search `.odylith`, `odylith/skills`, installed bundle files,
   local examples, or Python modules to discover schema fields after confirmation. Do not
   hand-author, switch to, or repair proposal JSON after confirmation. Do not
   narrate parser/schema retries or intermediate create-shape failures in
   operator chat. `greenfield propose --intent-file
   .odylith/runtime/greenfield/confirmed-intent.md --confirm-intent --format
   json` is only an optional review artifact when explicitly requested.
6. The operator's Product Intent confirmation authorizes one confirmed create
   command and one governed write transaction; the command owns bounded
   internal repair passes before the final manifest/result. Do not stop at
   intermediate repairable package-quality or create-shape findings. Do not ask the operator to inspect proposal JSON or confirm a second time by default.
   The normal confirmed path is
   `./.odylith/bin/odylith greenfield create --repo-root . --prompt "<operator request>" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1`.
   If a reviewer asks for JSON, render
   `greenfield propose --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm-intent --format json`
   as an audit artifact only; never reconstruct it by hand and never turn it
   into a host-side data-shaping step. If validation or Tribunal rejects the proposal,
   show the blocking issues in product language and write no records.
7. Preserve the evidence boundary: observed source, user intent, and Odylith
   assumptions must stay distinct. For consumer apps, include proportional
   security, privacy, abuse, accessibility, data-retention, compliance, and
   operational risk posture instead of generic risk copy. For science and math, reason from the
   domain named by the user and propose correctness obligations such as proof
   checking, reproducibility, units, tolerances, derivation review, datasets,
   independent review, or validation fixtures only when they actually fit.
8. For vague or broad prompts, preserve the project-first and
   program-formation contract without forcing a fixed bucket: show the parent
   workstream, child-boundary strategy, wave-to-workstream policy,
   provisional release selector, decisive assumptions, customization options,
   and coding-readiness gates before asking the operator to confirm or revise.
   Do not rush to `start B-***`; confirmed create writes accepted project
   truth, and coding begins only after the operator accepts the product gates
   and a child workstream has a technical plan.
9. Keep latency low: rely on `greenfield create --confirm` for the
   final batched visibility refresh instead of running separate refresh commands
   after each artifact family.
