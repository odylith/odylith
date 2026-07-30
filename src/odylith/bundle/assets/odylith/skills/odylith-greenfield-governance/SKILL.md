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

1. Do not refuse merely because the repo has no app source. Greenfield intent is
   proposal evidence, not source evidence.
   Product meaning comes before artifact mapping.
2. Run `./.odylith/bin/odylith greenfield propose --repo-root . --prompt "<operator request>"`.
   It treats the prompt and any EDIT Markdown as untrusted evidence, compiles typed
   custody facts, repairs and quality-gates the complete staged ProductCreateTransaction,
   and only then renders the visible confirmation.
3. Show that transaction-bound preview directly in chat. Keep product story, state object,
   first complete path, actors, systems, assumptions, ambiguities, and proof boundary clear
   and concise. End with one `## Choose one command` block:
   - **CONFIRM** commits this already validated, hash-bound package.
   - **EDIT** supplies corrections as new evidence and rebuilds a replacement package and hash.
   - **REJECT** stops with no governed records written.
   Ask one focused question only when uncertainty materially changes the first release;
   otherwise state the assumption. Markdown is evidence and a human view, never product truth.
4. Do not hide the final rail behind collapsed tool output or replace it with a generic menu.
   Do not expose internal repair chatter, proposal JSON, source-schema exploration, parser
   retries, or a second confirmation. The visible prose must remain simple, legible,
   grammatical, and specific.
5. After **CONFIRM**, run
   `./.odylith/bin/odylith greenfield create --repo-root . --transaction-file .odylith/runtime/greenfield/product-create-transaction.v1.json --transaction-hash <hash> --confirm`.
   Create only verifies receipt, hash, compiler identity, and repo preconditions; writes
   sealed bytes atomically under rollback guard; validates readback; and reports success or
   an environment/IO failure. It does not parse Markdown, call a host model, generate
   artifacts, or repair product prose after confirmation. Relay the returned post-confirm navigation block exactly once,
   beginning with the Project route
   `odylith/index.html?tab=project`; it is the user-facing handoff to the committed
   governance package. Do not ask for another confirmation, run another refresh, or imply
   that application code was created.
6. If compilation, validation, or the Tribunal cannot produce a transaction, repair the
   product/compiler before presenting CONFIRM. Explain only material blockers in product
   language and write no records. If JSON is explicitly requested, use
   `greenfield propose --format json` as an audit view; never rebuild transaction data by hand.
7. Preserve the evidence boundary: observed source, user intent, and Odylith
   assumptions must stay distinct. For consumer apps, include proportional
   security, privacy, abuse, accessibility, data-retention, compliance, and
   operational risk posture instead of generic risk copy. For science, math,
   research, model, simulation, prediction, or evaluation requests, preserve
   deep evidence semantics in both the visible Product Intent Confirmation and
   post-confirm artifacts: observed quantity, source data or evidence, method
   or model boundary, variables or parameters, baseline or comparison,
   uncertainty or tolerance, reproducibility proof, and excluded claims. Reason
   from the domain named by the user, do not invent scientific facts, and add
   correctness obligations such as proof checking, reproducibility, units,
   tolerances, derivation review, datasets, independent review, or validation
   fixtures only when they actually fit.
8. For vague or broad prompts, preserve the project-first and
   program-formation contract without forcing a fixed bucket: show the parent
   workstream, child-boundary strategy, wave-to-workstream policy,
   provisional release selector, decisive assumptions, customization options,
   and coding-readiness gates before asking the operator to confirm or revise.
   Do not rush to `start B-***`; confirmed create writes accepted project
   truth, and coding begins only after the operator accepts the product gates
   and a child workstream has a technical plan.
9. Keep latency low: rely on hash-confirmed `greenfield create
   --transaction-file ... --transaction-hash ... --confirm` for the final
   batched visibility refresh instead of running separate refresh commands
   after each artifact family.
