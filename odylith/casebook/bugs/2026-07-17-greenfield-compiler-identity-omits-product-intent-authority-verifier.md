- Bug ID: CB-273

- Status: Open

- Created: 2026-07-17

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A sealed ProductCreateTransaction records the compiler identity and confirm rechecks product-intent authority before writes. The identity manifest omitted greenfield_product_intent_envelope.py, so verifier semantics could change between proposal and confirmation without invalidating the compiled transaction.

- Impact: Confirmation-integrity risk: an accepted transaction can execute under different product-intent authority semantics after confirmation.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repository, source-local maintainer posture

- Detected By: Independent adversarial post-confirm boundary review

- Failure Signature: _COMPILER_IDENTITY_SOURCE_FILES excludes runtime/domain_intelligence/greenfield_product_intent_envelope.py while require_product_intent_authority runs during transaction build and commit verification.

- Trigger Path: Compile a greenfield transaction, change product-intent authority verifier semantics, then confirm without compiler identity invalidation.

- Ownership: Greenfield precompiled create transaction compiler

- Timeline: Captured 2026-07-17 during adversarial source review before release proof.

- Blast Radius: All confirmed Greenfield create transactions

- SLO/SLA Impact: Reliability guarantee is incomplete until the transaction identity binds every runtime authority executed after confirmation.

- Data Risk: No known data loss; operational semantics and audit provenance could differ after confirmation.

- Security/Compliance: Integrity risk only: no external security exposure is known; compliance and audit policy require the runtime authority at confirm to match the reviewed compiler identity.

- Invariant Violated: CONFIRM commits only the exact validated package and runtime semantics the user reviewed.

- Root Cause: The compiler identity source-file list was not extended for a product-intent authority module already executed by the commit path.

- Solution: Add greenfield_product_intent_envelope.py to compiler identity inputs and assert coverage in transaction provenance tests.

- Rollback/Forward Fix: Forward fix required before fresh installed-runtime proof; stale compiler receipts must be rejected before writes.

- Verification: Focused provenance tests prove source identity coverage and stale identity rejection before write; fresh installed-release matrix follows.

- Prevention: Review every post-confirm import and verifier against compiler identity whenever the commit path changes.

- Agent Guardrails: Treat runtime identity omissions as correctness defects, not documentation debt.

- Preflight Checks: Verify compiler identity covers every post-confirm authority and run stale-identity rejection tests before package proof.

- Regression Tests Added: test_compiler_identity_fingerprints_the_product_intent_authority_runtime

- Monitoring Updates: Installed matrix proof records compiler provenance verification.

- Version/Build: 0.1.15 source-local candidate

- Config/Flags: Default confirmed create path

- Customer Comms: Caught before release; no customer communication needed.

- Related Incidents/Bugs: CB-271

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_create_transaction.py
- src/odylith/runtime/domain_intelligence/greenfield_product_intent_envelope.py
