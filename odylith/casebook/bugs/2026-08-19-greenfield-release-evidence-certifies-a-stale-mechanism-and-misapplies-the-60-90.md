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
