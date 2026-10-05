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
2. Run `./.odylith/bin/odylith greenfield prepare --repo-root . --prompt
   "<operator request>"`. This product-owned parent supervises the four existing
   passes: authority gate, source-duty inventory, source-only verifier, and one
   candidate. It acquires and validates the same compiler-owned contracts and
   source receipts, stops on one material question, and returns the sealed
   read-only ProductCreateTransaction preview. Codex and Claude orchestration hosts may call this same
   route. Its pinned inference transport is direct Codex with Astra medium;
   this does not establish native Claude inference or confirmation eligibility.
   Missing Codex returns an environment error with no package publication.
   There is no alternate profile, retry, repair, fallback or full-candidate review.
   The gate and candidate share 300 seconds plus a 15-second completion reserve;
   inventory has 300 seconds, the source-only verifier 120, and each ledger check
   30. One nonreplenishing 660-second diagnostic parent covers contract acquisition,
   inference, local checks, retention, cleanup, observer return and pending
   diagnostic completion-record I/O and final raw whole/proposal checks. Receipt
   delivery, guardian retirement and final presentation are outside that interval. An independent
   guardian cancels blocked native work and owned descendants within a further
   two-second cancellation grace. The 660-second diagnostic cap is not a
   public-data-backed qualified bound. Newly staged seals remain unavailable to
   CONFIRM without its delivered completion receipt. The guardian stores only a
   digest, disclosing its private nonce after timed work passes. Late/error flows
   cannot disclose it even if cleanup fails. Post-certification delivery failures
   are accepted-or-unknown environment outcomes, never cancellation. Lost receipts
   cannot be regenerated. Old seals and their original receipts are preserved.
   Separate `candidate-contract`, `authority-check`, `source-ledger-check`, and
   `propose` commands remain available for explicit file-based source-custody
   workflows. Their receipts alone do not prove execution under the bounded parent.
   Do not inspect source to infer schemas or hand-author compiler transactions.
   After candidate receipt, no model, semantic or provider call is allowed.
   Independent semantic and UX review qualifies frozen release evidence only;
   it cannot admit, mutate or deny an individual consumer transaction.
   Verified product actions and exact actor bindings supply accepted component
   responsibilities. The candidate proposes architecture; typed lifecycle ownership
   preserves guards, boundaries and proof duties. Do not author duplicate
   responsibility quotations or infer product ownership from overlapping source.
3. Show the read-only, transaction-bound preview directly. The product writes
   its delivered receipt file and prints terminal commands naming it with
   `--completion-receipt '<path>'`. CONFIRM/REJECT use `odylith greenfield decide`;
   bounded EDIT uses `odylith greenfield prepare --transaction-hash '<hash>'
   --completion-receipt '<path>' --edit '<corrections>'`. An explicit receipt proves
   completed custody; it does not itself authorize publication. Public chat has no
   qualified confirmation interface. Ordinary chat or
   hooks cannot authorize creation. Unmarked manual seals retain their existing
   file-based confirmation contract.
4. `CONFIRM` and `REJECT` use the existing deterministic terminal owner with
   no compiler or model work. For a correction, run `odylith greenfield prepare
   --repo-root '<path>' --transaction-hash '<old-hash>' --completion-receipt '<path>'
   --edit '<correction>'`
   (or `--edit-evidence '<file>'`). One new supervised journey uses the sealed
   original source plus correction, preserves the old seal, and returns a new
   preview/hash or one question. It adds no repair or fallback. The explicit
   file-based `decide EDIT` interface remains available with its source gate,
   candidate and accepted ledger receipt; it alone does not establish parent timing.
   Its `source-ledger-check` calls require the prior `--transaction-hash`, exact
   retained `--prompt` and separate `--edit` or `--edit-evidence`; bounded prior
   seals also require their delivered `--completion-receipt`. Do not pass combined
   source as the retained prompt. The same source-only verifier gives a required
   disposition for every prior lifecycle duty. Preserved or changed duties need
   affirmative current carriers in the same typed section; each change or removal
   needs affirmative authorization from the complete compiler-bound correction.
   The verifier supplies that semantic judgment without a duplicate quote/context
   locator. A compound carrier may support multiple prior
   duties, each judged independently. Missing or uncertain rows stop before the
   candidate. Initial tasks/receipts stay v4/v7; fresh EDIT uses v6/v9 with prior seal and
   correction custody. The checklist cannot replace current truth or override an
   explicit correction. Exact historical v5/v8 remains passive sealed-readback
   compatibility and cannot authorize fresh authoring or admission. Complete keys
   and custody do not prove semantic accuracy.
5. `odylith greenfield create` with `--transaction-file`, `--transaction-hash`,
   and `--confirm` (plus `--completion-receipt` for bounded seals) remains a separate
   commit-only interface, not a fallback for
   chat approval or `decide`. Do not create from a chat approval. It verifies the compiler receipt, hash and
   preconditions, publishes sealed bytes under rollback guard, validates readback,
   and returns its outcome. It never interprets evidence, calls a model, generates
   artifacts, or rebuilds persistent projections after confirmation. Native host
   eligibility remains open. If JSON is explicitly requested, use `greenfield
   prepare --format json`; this is the proposal JSON boundary; never rebuild
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
