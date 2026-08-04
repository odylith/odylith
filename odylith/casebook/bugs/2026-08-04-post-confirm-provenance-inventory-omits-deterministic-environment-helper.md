- Bug ID: CB-310

- Status: FixedPendingRelease

- Created: 2026-08-04

- Severity: P2

- Reproducibility: Consistent

- Type: Test

- Description: The canonical confirmed-create trace executes the shared environment helper used by the completion handoff, but the exact post-confirm runtime-source inventory does not include that module.

- Impact: The release suite cannot prove that every post-confirm executable owner is explicitly reviewed, even though the observed helper is deterministic environment handling rather than semantic generation.

- Components Affected: domain-intelligence

- Environment(s): Odylith 0.1.15 source-local canonical validation at commit 3e650ce0f

- Detected By: Fresh-process canonical pytest shard 20 and isolated replay

- Failure Signature: Executed source set contains runtime/common/environment.py beyond the declared post-confirm runtime inventory.

- Trigger Path: Trace greenfield create --confirm through commit, readback, and completion handoff.

- Ownership: Greenfield post-confirm executable provenance contract

- Timeline: Detected as the only shard-20 failure after all other 199 tests in that shard passed; reproduced in isolation.

- Blast Radius: Release proof for every confirmed Greenfield create using the completion handoff.

- SLO/SLA Impact: Blocks canonical validation and clean distribution proof.

- Data Risk: No data mutation defect observed; proof custody is incomplete.

- Security/Compliance: No direct security exposure; the undeclared executable owner weakens auditability of the post-confirm boundary.

- Invariant Violated: Every post-confirm Odylith source module that executes must be explicitly present in the reviewed provenance inventory.

- Root Cause: The deterministic dashboard-handoff environment owner was added without extending the exact post-confirm runtime source manifest.

- Solution: Add runtime/common/environment.py to the reviewed post-confirm source inventory and retain the exact executed-set assertion.

- Rollback/Forward Fix: Forward fix to provenance metadata and its regression only; post-confirm behavior remains unchanged.

- Verification: Both the lower-level commit trace and canonical create-adapter trace passed with exact source-set equality; the full 38-test semantic-model/provenance group passed. The lower-level trace explicitly classifies the environment helper as untraced, while the CLI trace requires it to execute through the completion handoff. Canonical validation remains the release re-entry gate.

- Prevention: Treat every new post-confirm import as a manifest-reviewed contract change.

- Agent Guardrails: Do not weaken the exact-set assertion or wildcard whole runtime directories.

- Preflight Checks: Require the isolated trace to match the explicit source inventory exactly.

- Regression Tests Added: Existing exact post-confirm trace remains the regression gate.

- Monitoring Updates: No runtime monitor change; this is a deterministic release preflight.

- Version/Build: 0.1.15 branch 2026/freedom/v0.1.15

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_commit_transaction.py
- src/odylith/runtime/common/environment.py
- tests/unit/runtime/test_greenfield_transaction_provenance.py
