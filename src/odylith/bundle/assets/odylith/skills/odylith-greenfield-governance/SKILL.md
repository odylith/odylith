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
   It treats the prompt and corrections as untrusted evidence, compiles typed
   custody facts, and quality-gates the complete staged ProductCreateTransaction.
3. Show the transaction-bound, read-only preview directly in chat. Keep Product
   story, State object, First complete path, actors, systems, assumptions,
   ambiguities and Proof boundary clear. No qualified confirmation interface is
   attached. Do not append chat decision commands, offer publication, or run
   create from a chat approval. Host names and registered hooks are not proof of
   fault-safe interception or visible completion.
4. Ask one focused question only when uncertainty materially changes the first
   release; otherwise state the assumption. Markdown is evidence and a human
   view, never product truth. Corrections through `propose --edit` rebuild the
   staged package with a new hash. Keep internal repair chatter and proposal JSON
   out of the normal view; do not inspect source for schema or narrate retries.
5. Explicit operator invocation of `odylith greenfield create` with
   `--transaction-file`, `--transaction-hash`, and `--confirm` is a separate
   deterministic interface, not a fallback for chat approval. It verifies the
   compiler receipt, hash and preconditions, publishes sealed bytes under rollback
   guard, validates readback and returns its outcome. It never interprets evidence,
   calls a model, generates artifacts or rebuilds persistent projections after
   confirmation. Native host eligibility remains open; report that blocker
   plainly rather than inventing a write offer. If JSON is explicitly requested,
   use `greenfield propose --format json`; never rebuild transaction data by hand.
   For that explicit operator invocation, relay its outcome without reinterpretation.
   Relay the returned post-confirm navigation block exactly once; do not regenerate
   artifacts, rebuild projections or substitute a model-authored success message.
6. Preserve the evidence boundary: observed source, user intent, and Odylith
   assumptions must stay distinct. For consumer apps, include proportional
   security, privacy, abuse, accessibility, data-retention, compliance, and
   operational risk posture instead of generic risk copy. For science, math,
   research, model, simulation, prediction, or evaluation requests, preserve
   deep evidence semantics in both the visible product preview and
   post-confirm artifacts: observed quantity, source data or evidence, method
   or model boundary, variables or parameters, baseline or comparison,
   uncertainty or tolerance, reproducibility proof, and excluded claims. Reason
   from the domain named by the user, do not invent scientific facts, and add
   correctness obligations such as proof checking, reproducibility, units,
   tolerances, derivation review, datasets, independent review, or validation
   fixtures only when they actually fit.
7. For vague or broad prompts, preserve the project-formation contract without
   forcing a fixed bucket: show the parent workstream, child-boundary strategy,
   provisional release selector, decisive assumptions, customization options,
   and coding-readiness gates for the operator to review.
   Greenfield onboarding must not create Compass program or execution-wave
   records; those remain explicit later planning decisions. Do not rush to
   `start B-***`; confirmed create writes accepted project truth, and coding
   begins only after the operator accepts the product gates and a child
   workstream has a technical plan.
