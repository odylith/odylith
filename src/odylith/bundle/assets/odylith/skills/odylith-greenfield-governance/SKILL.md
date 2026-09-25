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
2. Use the active host as the single semantic author. First run
   `./.odylith/bin/odylith greenfield candidate-contract --repo-root . --prompt
   "<operator request>"`. Reason over its complete evidence and write exactly one
   JSON candidate matching the returned schema to a temporary file outside the
   repository. Then run `./.odylith/bin/odylith greenfield propose --repo-root .
   --prompt "<operator request>" --candidate-file '<temporary-file>'`.
   The candidate is an untrusted hypothesis: Odylith revalidates every source
   citation and typed relation, runs one independent semantic review, seals the
   custody facts, and quality-gates the complete staged ProductCreateTransaction.
   Do not inspect source code to infer the candidate schema. Do not add a parser,
   regex extraction pass, participant selector, remainder author, join, repair,
   retry, fallback candidate, or alternate model ladder. Stop on the first
   validation or review failure and record that mechanism evidence.
3. Show the read-only, transaction-bound preview directly. It publishes nothing, but prints
   three full shell-quoted terminal commands: `odylith greenfield decide --repo-root
   '<path>' CONFIRM '<hash>'`, `odylith greenfield decide --repo-root '<path>' EDIT
   '<hash>' --edit '<corrections>'` (or `--edit-evidence '<file>'`), and `odylith
   greenfield decide --repo-root '<path>' REJECT '<hash>'`. No qualified confirmation
   interface comes from ordinary chat approval, host names, or hooks.
4. `CONFIRM` and `REJECT` use the shared bounded deterministic owner without
   compiler or model work. For `EDIT`, run `greenfield candidate-contract` with
   `--transaction-hash '<old-hash>'` and the new `--edit` or `--edit-evidence`,
   author one new host candidate, then pass that same correction and
   `--candidate-file '<temporary-file>'` to `greenfield decide EDIT`. EDIT verifies
   the retained hash, compiles the sealed original source plus correction,
   preserves the original tier and advisory 90/120/150 targets, retains the old
   seal, and returns a new preview/hash. It adds no repair or fallback path.
5. `odylith greenfield create` with `--transaction-file`, `--transaction-hash`,
   and `--confirm` remains a separate commit-only interface, not a fallback for
   chat approval or `decide`. Do not create from a chat approval. It verifies the compiler receipt, hash and
   preconditions, publishes sealed bytes under rollback guard, validates readback,
   and returns its outcome. It never interprets evidence, calls a model, generates
   artifacts, or rebuilds persistent projections after confirmation. Native host
   eligibility remains open. If JSON is explicitly requested, use `greenfield
   propose --format json`; this is the proposal JSON boundary; never rebuild
   transaction data by hand.
   After an explicit terminal decision or create invocation, relay its returned
   outcome without reinterpretation. Relay the returned post-confirm navigation
   block exactly once; do not regenerate artifacts, rebuild projections, or
   substitute a model-authored success message. Never expose parser/schema
   retries or internal repair chatter to the operator.
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
