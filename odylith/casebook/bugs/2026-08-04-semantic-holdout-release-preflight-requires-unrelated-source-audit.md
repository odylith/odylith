- Bug ID: CB-312

- Status: Open

- Created: 2026-08-04

- Severity: P1

- Reproducibility: Consistent

- Type: Test

- Description: The one-shot semantic Greenfield holdout is hash-bound by the frozen evaluation contract, but campaign shard preflight unconditionally requires a source-corpus release audit for every release shard. The intended semantic release lane therefore fails before claiming or executing the holdout.

- Impact: Blocks the final independent semantic release proof even when the holdout hash, frozen floors, implementation revision, and one-shot ledger are valid.

- Components Affected: greenfield-governance

- Environment(s): Odylith 0.1.15 maintainer release campaign at b5af452ae3ee07d8de32862d39251df0ed52b19e

- Detected By: Final holdout preflight after the clean installed 14-case matrix

- Failure Signature: release proof requires --release-audit-file for a semantic holdout shard that correctly has no source-corpus audit

- Trigger Path: Run greenfield_matrix_campaign_runner with one release case file also supplied as semantic annotations, the frozen evaluation manifest, a fresh holdout ledger, and the frozen implementation revision.

- Ownership: Greenfield matrix campaign shard preflight and semantic release proof routing

- Timeline: Observed 2026-08-04 before the private 24-case holdout was executed; the holdout remains unclaimed and unexecuted.

- Blast Radius: All one-shot semantic final-holdout campaigns; discovery and source-provenanced release corpora are unaffected.

- SLO/SLA Impact: Prevents release-readiness settlement after all maintained installed cases pass.

- Data Risk: No governed project writes or holdout product executions occur; the failure is pre-execution.

- Security/Compliance: No security or compliance boundary is weakened; the fix must preserve source-audit requirements for source-provenanced release corpora.

- Invariant Violated: A semantic holdout must be admitted by its frozen evaluation contract and one-shot ledger, while source-provenanced corpora must independently retain their audit requirement.

- Root Cause: Shard preflight branches only on proof_tier=release and does not distinguish semantic release evidence from source-provenanced release evidence.

- Solution: Recognize a complete semantic-release shard contract as a separate release evidence class and bypass only the source-corpus audit preflight for that class; retain frozen-contract validation and the one-shot ledger in the matrix runner.

- Rollback/Forward Fix: Forward fix in the release harness only; do not weaken product quality gates or source-corpus audit rules.

- Verification: Add positive semantic-release preflight coverage and negative coverage proving partial semantic fields and ordinary release shards still require the source audit; rerun campaign tests before the holdout.

- Prevention: Keep release evidence classes explicit in shard preflight tests instead of treating every release proof as source-provenanced.

- Agent Guardrails: Never fabricate an audit for a synthetic semantic holdout and never bypass source audits for source-provenanced corpora.

- Preflight Checks: Verify the holdout SHA-256 remains 3558ab3ffe23a285303bdbdcca560cec31fb3eee261e0aa9bc610b9f04f5e2a and its one-shot ledger does not exist before execution.

- Regression Tests Added: Extend tests/unit/install/test_greenfield_matrix_campaign_release_scope.py to admit complete semantic-release shards and reject partial semantic or unaudited source-corpus release shards.

- Monitoring Updates: Campaign result must report semantic frozen-floor posture and terminal one-shot ledger status.

- Version/Build: 0.1.15 branch 2026/freedom/v0.1.15

- Config/Flags: Release tier, full install, browser proof, rescue proof, commit recovery, semantic annotations, evaluation manifest, fresh final-holdout ledger.

- Customer Comms: Internal release blocker; no consumer project was affected.

- Related Incidents/Bugs: CB-303, B-142

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_matrix_campaign_shard_runner.py
- scripts/release/greenfield_preconfirm_matrix.py
- tests/unit/install/test_greenfield_matrix_campaign_release_scope.py
