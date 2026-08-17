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
2. Treat the active host model as the semantic reasoner and Odylith as the
   deterministic verifier and publisher. Run
   `./.odylith/bin/odylith greenfield semantic-intent-request --repo-root . --prompt "<operator request>"`,
   then author the temporary packet at the returned destination. The request
   contains the exact evidence bytes and digest, packet schema, typed endpoint
   contracts, completeness invariants, and exact next invocation. Do not infer
   those contracts by reading runtime source.

   The current supported mechanism uses two fresh reasoning contexts. First, a
   prompt-only materiality critic sees the exact evidence and no candidate
   graph. It returns the complete field-by-field assessment, alternatives, and
   commit-or-clarify decision. Validate and preserve that assessment exactly.
   Second, a distinct graph author sees the same evidence plus the validated
   assessment, identifies actors and ownership, ordered actions, state
   transitions, visible outcomes, dependencies and access direction,
   constraints, non-goals, components, and proof, then completes every required
   source/graph challenge. The author may not rewrite the critic's assessment.
   A citation proves custody, not entailment. If either schema fails, block or
   start a fresh run from the original sealed phase input; never repair from a
   validator error. If the assessment requires clarification, ask its one
   focused question before graph authoring instead of silently merging a guess.

   This critic-before-author mechanism is the current evidence-supported
   release regime, not a permanent architectural commitment. Keep the outcome,
   safety, and proof laws fixed; replace the mechanism in a future version if
   comparative evidence shows a simpler or more reliable regime. The packet
   must:
   - model identity, actors, ordered workflow, state, visible output,
     dependencies, constraints, non-goals, component boundaries, and proof as
     typed facts and relations;
   - cite exact prompt or EDIT substrings for every fact, relation, and
     narrative;
   - label architectural or non-material additions as bounded interpretations
     or visible assumptions rather than source facts; and
   - use `clarification_required` only when one material unknown changes the
     first release. Ask that one focused question and stop before staging.

   Do not derive product meaning with shell text processing, regexes, parser
   retries, or hand-edited proposal JSON. The temporary packet is a host-to-
   product handoff, not governed truth and not a user-facing artifact.
3. Run
   `./.odylith/bin/odylith greenfield propose --repo-root . --prompt "<operator request>" --semantic-intent-file <temporary-packet.json>`.
   For EDIT, run
   `./.odylith/bin/odylith greenfield semantic-intent-request --repo-root . --supersedes-hash <hash> --edit "<corrections>"`.
   That request reconstructs the original evidence from the sealed pending
   transaction, binds the exact correction, and returns the replacement digest,
   packet destination, prior graph context, and next invocation. Odylith
   verifies schema shape, exact citations, graph references, ownership,
   material completeness, operating limits, projections, and the complete
   staged ProductCreateTransaction before it renders the visible confirmation.
   It must fail closed; never repair or reinterpret the packet inside the
   runtime.
4. Show that transaction-bound preview directly in chat. Keep product story, state object,
   first complete path, actors, systems, assumptions, ambiguities, and proof boundary clear
   and concise. End with one `## Choose one command` block:
   - **`CONFIRM <hash>`** commits this already validated, hash-bound package.
   - **`EDIT <hash> <corrections>`** supplies corrections as new evidence and rebuilds a replacement package and hash.
   - **`REJECT <hash>`** stops with no governed records written.
   Ask one focused question only when uncertainty materially changes the first release;
   otherwise state the assumption. Markdown is evidence and a human view, never product truth.
5. Do not hide the final rail behind collapsed tool output or replace it with a generic menu.
   Do not expose internal repair chatter, proposal JSON, source-schema exploration, parser
   retries, or a second confirmation. The visible prose must remain simple, legible,
   grammatical, and specific.
6. After **`CONFIRM <hash>`**, run
   `./.odylith/bin/odylith greenfield create --repo-root . --transaction-file .odylith/runtime/greenfield/pending/<hash>/product-create-transaction.v1.json --transaction-hash <hash> --confirm`.
   Create only verifies receipt, hash, compiler identity, and repo preconditions; writes
   sealed files with atomic replacement under a journaled rollback guard; switches the
   active-generation pointer used by canonical readers; validates readback; and reports success or
   an environment/IO failure. It does not parse Markdown, call a host model, generate
   artifacts, or repair product prose after confirmation. Relay the returned post-confirm navigation block exactly once,
   beginning with the Project route
   `odylith/index.html?tab=project`; it is the user-facing handoff to the committed
   governance package. Do not ask for another confirmation, run another refresh, or imply
   that application code was created.
7. If packet verification, projection validation, or the Tribunal cannot produce
   a transaction, distinguish a bad host interpretation from a product defect.
   Correct the temporary packet only when the cited evidence proves the intended
   meaning; otherwise fix the product/compiler before presenting CONFIRM. Never
   add a phrase rule, vocabulary exception, or hidden retry to make one prompt
   pass. Explain only material blockers in product language and write no
   records. If JSON is explicitly requested, use `greenfield propose --format
   json` as an audit view; never rebuild transaction data by hand.
8. Preserve the evidence boundary: observed source, user intent, and Odylith
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
9. For vague or broad prompts, preserve the project-formation contract without
   forcing a fixed bucket: show the parent workstream, child-boundary strategy,
   provisional release selector, decisive assumptions, customization options,
   and coding-readiness gates before asking the operator to confirm or revise.
   Greenfield onboarding must not create Compass program or execution-wave
   records; those remain explicit later planning decisions. Do not rush to
   `start B-***`; confirmed create writes accepted project truth, and coding
   begins only after the operator accepts the product gates and a child
   workstream has a technical plan.
10. Keep latency low: rely on host reasoning already active in the session and
   one deterministic pre-confirm compilation pass. Do not launch an internal
   provider ensemble or model retry loop. Rely on hash-confirmed `greenfield create
   --transaction-file ... --transaction-hash ... --confirm` for the final
   batched visibility refresh instead of running separate refresh commands
   after each artifact family.

After each development wave, check semantic fidelity, consumer utility,
cross-surface drift, complexity, latency, and new failure classes. Keep the
outcome and safety invariants fixed; keep the host prompt, graph schema,
projection design, and model profile provisional. Replace a mechanism that
repeatedly fails independent examples, and delete its superseded path after the
replacement is proved.
