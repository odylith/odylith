- Bug ID: CB-349

- Status: Open

- Created: 2026-08-19

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The active standard candidate uses four host stages with zero retries, while release evidence still binds an older two-call critic-and-author mechanism. Its resource gate applies a non-strict 60-second ceiling whenever restart_count is zero, never selects the explicit 120-second deep tier, permits restarts, and caps calls below the active standard commit path. A green release report could therefore certify different behavior than the consumer mechanism.

- Impact: A release can appear ready without proving the mechanism that consumers actually execute or the non-negotiable standard, rescue, and explicit-deep latency laws.

- Components Affected: release

- Environment(s): Detached source-local Greenfield release candidate on 2026-08-19

- Detected By: Goal-drift audit comparing the active standard pipeline, development evidence producer, and release evaluator contracts

- Failure Signature: Active commit path records four calls and zero restarts; development evidence declares model_calls_per_case=2; release evidence caps calls at 3, permits one restart, uses <=60000 for restart-free cases, and has no reachable explicit-deep <=120000 branch.

- Trigger Path: standard semantic pipeline evidence -> development cohort evidence -> release evaluation resource gates

- Ownership: Greenfield mechanism identity and release-evidence resource-tier contract

- Timeline: Captured 2026-08-19 through `odylith bug capture`.

- Blast Radius: All Greenfield release-readiness claims, Codex and Claude parity evidence, development cohorts, and protected-holdout admission

- SLO/SLA Impact: Can falsely certify or falsely reject the mandatory strict under-60 standard path, at-most-90 rescue path, and explicit-only at-most-120 deep path.

- Data Risk: No direct data mutation; high governance-truth risk because an unproved mechanism may be released.

- Security/Compliance: No direct exposure; provenance and release attestation are unreliable when evidence binds another mechanism.

- Invariant Violated: Release evidence must bind the exact consumer mechanism and enforce standard <60s, rescue <=90s, explicit deep <=120s, zero automatic deep, and zero undeclared retries.

- Root Cause: Mechanism evolution was not coupled to a versioned release-evidence identity and tier schema; old two-stage producer assumptions remained authoritative after the four-stage candidate replaced them.

- Solution: Introduce one versioned mechanism execution contract and tier-exact evidence rows; make the active standard pipeline and release evaluator consume it; demote old two-stage evidence to comparison-only; reject mechanism, call-count, retry, or tier mismatches; delete losing release authority after the winner is frozen.

- Rollback/Forward Fix: Forward fix only. Do not loosen call ceilings or relabel old evidence as the current mechanism.

- Verification: Structural proof of one mechanism identity owner; positive and negative evaluator tests for strict 60, inclusive 90/120, explicit deep only, zero retry, and exact call profile; full development cohort from the winning mechanism before holdout admission.

- Prevention: Every mechanism cutover must version and atomically migrate its producer, evaluator, fixtures, and structural tests; release reports must identify the exact mechanism and execution tier.

- Agent Guardrails: Do not tune examples, add parser rules, loosen ceilings, or count stale two-stage evidence as proof. Compare mechanisms on product utility and delete the losing release path.

- Preflight Checks: Keep the protected final holdout untouched; freeze the winning mechanism and development evidence before changing holdout admission.

- Related Incidents/Bugs: CB-334, CB-340

- Code References: - scripts/release/greenfield_semantic_standard_pipeline_experiment.py
- scripts/release/greenfield_semantic_development_evidence.py
- scripts/release/greenfield_semantic_development_cohort.py
- scripts/release/greenfield_semantic_release_evidence.py

- Implementation Checkpoint (2026-08-19): A single typed semantic-execution contract now owns the active four-call topology, exact Codex and Claude host profiles, zero-retry rule, and the three timing comparisons. Standard completion is accepted only below 60,000 ms; rescue is accepted through 90,000 ms only when it binds the canonical hash of a prior typed standard failure; explicit deep is accepted through 120,000 ms only with an explicit operator-or-CI entry reason; automatic deep remains forbidden. Standard and rescue pipeline receipts now seal this mechanism identity and contract hash. Rescue execution moved into its own owner instead of leaving a second controller in the standard module. The clarification path now requires one fresh schema-constrained author challenge and deterministically seals the exact one-question packet with no product facts or relations, so a fast single-critic decision can no longer masquerade as release-grade evidence. The operating envelope derives its latency and mechanism declarations from the shared contract. Focused operating-envelope, mechanism, host, typed-custody, clarification, and pipeline proof passes 92 tests. The release evaluator and development cohort still bind the retired two-call mechanism, so CB-349 remains P1/Open and release/holdout admission remains blocked until that authority is migrated and the full active-mechanism cohort is independently reviewed.

- Implementation Checkpoint (2026-08-19, active-mechanism cohort): The development producer, release evaluator, deterministic-law contract, fake holdout rail, and versioned v4 evaluation fixtures now consume only `parallel_materiality_atomic_source_then_typed_graph_completion`; the retired two-call development-evidence and host-execution authorities are deleted. Frozen plans and every receipt bind the exact Greenfield runtime/release source fingerprint, assignment, pinned stage identity, packet, review package, and sealed transaction. The materiality critic now selects deterministic evidence-block handles instead of authoring quote bytes, supporting-system consumers use one typed index-set contract, and the bounded source-role comparison selected Luna/low over Sol/low after it converted three independent failure families into validated useful outcomes at 42.502, 28.238, and 50.949 seconds. On source fingerprint `70584d7aece0c97bfe306f1a4f80c8b80d948913421052631ae12c429a3e463e`, the fresh 24-case cohort reached 22 useful standard outcomes below 60 seconds and two useful rescue outcomes at 46.755 and 58.267 seconds, with zero deadline failures, zero environment failures, zero restarts, and no deep-tier execution. Broad semantic proof passes 236 tests and transaction/severance proof passes 108 tests. CB-349 remains P1/Open because independent semantic/package review, deterministic-law evidence on an immutable revision, host parity, lower-capability safety, install/browser/dashboard proof, and the protected holdout are still pending; execution success alone is not release readiness.

- Implementation Checkpoint (2026-08-20, selection-only rescue): Fresh development pressure falsified completion re-authoring as the rescue mechanism. A complex six-actor case exhausted both a 33-second and a 39-second rescue authoring budget even after compact-presentation experiments, while the standard path had already produced two complete typed candidates. Those losing variants were removed. The replacement pre-admits both existing source candidates through the full deterministic graph contract and gives the fourth host call only three choices: select the full-source candidate, select the source-only candidate, or ask one material question. Rescue authors no graph and performs no merge, repair, or prose parsing. The provider contract also replaced two disjoint nested `oneOf` branches with provider-supported `anyOf`; exact object-to-citation binding remains deterministic. Focused mechanism proof passes 134 tests. On implementation fingerprint `81830ce83b180599e58715d8adfa7a76a1959ed8246f696ea17bf2925d5a49ca`, the fresh 24-case cohort produced all 24 expected useful outcomes: 17 verified commits and 7 focused clarifications, 14 standard and 10 bounded-rescue completions, zero deadline or environment failures, zero restarts, zero automatic deep runs, and all cases below the strict 60-second standard ceiling. The slowest case completed in 55.026 seconds. The exact plan and manifest hashes are `b3909e7e03dab71bbbee1a46efb6ec4c367edf9691ea09dc04de65493146a794` and `77cfd376ca2c85bee83a783a96ea8d576722ab9e90d1e4972d3bed74b3968d1e`. CB-349 remains P1/Open until independent semantic/package review, deterministic-law evidence, Codex/Claude parity, lower-capability safety, install/browser/dashboard proof, and the untouched protected holdout pass on these exact mechanism bytes.

- Release-Evidence Checkpoint (2026-08-20, selected-candidate receipt custody): The first immutable candidate-bundle compile stopped on `gfhi-001` because final deterministic admission selected run 0 while its copied source receipt still marked run 1 as `selected`. The graph and transaction were valid, but the evidence row contradicted itself. The correction moves source-selection status and index binding into one shared receipt owner used by both production and the release verifier. Selecting either admitted candidate now atomically marks that run `selected`, demotes the other admitted run to `comparison_passed`, and rejects any status/index disagreement. The evidence verifier no longer assumes source-only run 1 must always win; it requires exactly one selected admitted run whose status and index agree. Focused receipt, cohort, pipeline, and execution proof passes 60 tests. A fresh exact `gfhi-001` run selected run 0 consistently, passed release-evidence verification, produced a verified transaction in 35.223 seconds with three calls, and used no retry or rescue. The prior 24-case cohort remains historical mechanism evidence but cannot become the revision-bound candidate bundle; a fresh plan, deterministic-law report, and full cohort are required on the corrected fingerprint before independent release evaluation resumes.

- Mechanism-Reopen Checkpoint (2026-08-20, incomplete independent redundancy): The fresh revision-bound cohort on implementation fingerprint `a87905ca25313c758f88c839ac3a83d0bed5b4e58a91cc15a6bcf57c8202145d` was stopped at the first real product failure. Cases `gfhi-001` through `gfhi-016` reached useful terminals inside the 60/90 contract with zero retries or automatic deep execution. On `gfhi-017`, the sole full-graph hypothesis call produced no usable candidate while the independent source-only hypothesis authored a source graph whose state transition and visible output referenced nonexistent flattened step index `8`; deterministic validation correctly rejected it. Selection-only rescue then failed at 48.048 seconds because neither existing hypothesis was an admissible complete candidate, and fresh graph authorship is correctly forbidden in rescue. This falsifies the current `one full graph + one source-only graph` topology as complete redundancy: only one run owns completion, so one host-call failure can leave rescue with no selectable package. Do not restore completion re-authoring, loosen step validation, infer the intended step, add a third lexical repair path, or count the earlier 24/24 cohort as release proof. Reopen bounded mechanism comparison around independently complete candidates and node-owned state/output relations; preserve strict standard `<60s`, rescue `<=90s`, explicit-only deep `<=120s`, exact citations, zero retries, and the untouched protected holdout.
