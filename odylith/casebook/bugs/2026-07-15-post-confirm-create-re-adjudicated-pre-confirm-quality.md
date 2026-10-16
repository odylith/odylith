- Bug ID: CB-249

- Status: Open

- Created: 2026-07-15

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Commit-only create rechecked transaction quality manifest fields and compiled preview quality after CONFIRM. A transaction already compiled and approved could still be rejected for product-quality reasons after the user had confirmed.

- Impact: Violates the deterministic post-confirm product path and can turn a pre-confirm compiler defect into a customer-visible confirmation failure.

- Components Affected: odylith

- Environment(s): Odylith product-repo greenfield create transaction path

- Detected By: Adversarial transaction-boundary review

- Failure Signature: greenfield create rejected quality manifest or preview debt after confirmation before sealed writes

- Trigger Path: odylith greenfield propose then greenfield create --confirm

- Ownership: Greenfield precompiled create transaction kernel

- Timeline: Captured 2026-07-15 through `odylith bug capture`.

- Blast Radius: All greenfield confirmation flows

- SLO/SLA Impact: Blocks the post-confirm success guarantee

- Data Risk: No governed data loss because the rejection occurs before sealed writes.

- Security/Compliance: No direct security, privacy, accessibility, policy, or safety impact; this is a product-quality boundary failure.

- Invariant Violated: Post-confirm may verify receipts, transaction hash, compiler provenance, and repo preconditions, then atomically write and read back sealed bytes; it must not re-adjudicate product quality.

- Root Cause: Quality-manifest and commit-preview approval checks remained in the commit executor and write sink after pre-confirm compilation was introduced.

- Solution: Move quality-manifest and preview completeness gates into transaction compilation; commit only consumes sealed reporting data.

- Rollback/Forward Fix: Forward fix only

- Verification: Focused transaction, compiled-write, preview, commit-only, and direct create CLI tests pass after the move.

- Prevention: Keep commit-only boundary tests forbidding post-confirm quality validation and place every product-quality gate in the compiler contract.

- Agent Guardrails: Do not count an embedded quality-status reread as an allowed post-confirm verification.

- Preflight Checks: Validate transaction construction rejects unresolved quality and preview debt before CONFIRM.

- Regression Tests Added: Transaction builder rejects unapproved manifests; compiled package rejects preview debt before confirmation; write sink reports sealed preview without recheck.

- Version/Build: 0.1.15 development branch

- Related Incidents/Bugs: CB-205, CB-207, CB-248

- GitHub Status: fixed_pending_release

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_create_transaction.py
- src/odylith/runtime/domain_intelligence/greenfield_create_commit.py
- src/odylith/runtime/domain_intelligence/greenfield_compiled_write.py
