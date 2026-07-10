- Bug ID: CB-229

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-07-10

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The installed greenfield release matrix validates that a write transaction reports committed, but it does not require the commit-only, prewrite-clean, rollback, or sealed-hash invariants and its persisted per-case summary omits those facts. A future regression could move generation or repair after confirmation and still receive a passing matrix if the write eventually commits.

- Impact: Maintainers can overstate the non-negotiable post-confirm guarantee because release evidence proves completion without proving that confirmation committed an already compiled transaction.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Committed 0.1.15 local release matrix at eca44acc2

- Detected By: Receipt-level audit after the 14-case installed release matrix passed

- Failure Signature: greenfield_matrix_quality_scoring.write_committed checks only write_transaction.status; greenfield_matrix_proof_scope.post_confirm_manifest_summary omits transaction custody fields

- Trigger Path: Run make greenfield-post-confirm-matrix and inspect greenfield-post-confirm-matrix.v1.json per-case post_confirm_manifest_summary

- Ownership: Installed release proof and ProductCreateTransaction custody verification

- Timeline: Captured 2026-07-10 through `odylith bug capture`.

- Blast Radius: All standard installed matrix cases and any release-readiness claim based on their persisted summaries

- SLO/SLA Impact: No runtime latency impact; release confidence is overstated

- Data Risk: No direct data loss; the gap could fail to catch future late-generation or partial-write regressions

- Security/Compliance: Security posture: rollback, precondition, and sealed-hash evidence are trust-boundary controls. The observed gap exposes no credentials or customer data, but release proof must fail closed if those controls are absent.

- Invariant Violated: A passing installed matrix must prove that confirmation verified and atomically committed a precompiled sealed write set with rollback enabled, not merely that some write reached committed status

- Root Cause: The legacy quality helper predates the precompiled transaction kernel and retained a completion-only predicate; the proof summary was never widened when the write_transaction receipt gained custody fields

- Solution: Release scoring now requires committed status, commit-only apply, a clean prewrite package, enabled rollback, and valid ProductCreateTransaction and repository write-set SHA-256 hashes that match both the final manifest transaction summary and the create payload summary. A positive, finite, in-budget post-confirm elapsed time is mandatory. Standard and rescue scoring share the same field-specific custody diagnostics, and the persisted per-case summary retains the exact receipt facts without inventing a zero time when evidence is absent.

- Rollback/Forward Fix: Forward-fix the release harness before using the matrix as final release proof

- Verification: The focused installed-matrix scoring, proof-scope, and campaign suite passed 104 tests. False commit-only, prewrite-clean, rollback, transaction-hash, and write-set-hash values each fail with field-specific diagnostics; wrong-but-valid hashes fail cross-summary matching; missing, zero, negative, and malformed elapsed values fail; rescue output preserves the specific custody failure; and absent timing remains null in persisted proof. Fresh committed dist eca44acc2 then passed all 14 standard cases at hard 10/10 with zero issues: compile-and-create completed in 38.997-49.791s and commit-only apply in 0.103-0.126s. Browser proof passed 14/14, and cleanup plus platform-leakage checks passed. Synthetic rescue completed in 62.599s with a 0.116s commit-only apply; natural rescue completed in 77.449s with a 0.113s commit-only apply.

- Prevention: Version the receipt predicate with the transaction kernel and fail closed when required fields are absent

- Agent Guardrails: Do not infer commit-only behavior from command success, issue_count zero, or status committed; inspect the sealed transaction receipt

- Preflight Checks: Before release readiness, assert commit_only true, prewrite_clean_before_commit true, rollback_guard enabled, nonempty transaction and write-set hashes, and bounded positive post-confirm elapsed time

- Regression Tests Added: `test_quality_verdict_requires_commit_only_transaction_custody`, `test_quality_verdict_rejects_create_payload_transaction_hash_mismatch`, `test_quality_verdict_requires_positive_measured_post_confirm_time`, `test_rescue_cli_issues_report_specific_commit_only_custody_failure`, and expanded proof-summary coverage

- Monitoring Updates: Persist per-case write-transaction custody in the JSON proof artifact and retain the standard, browser, cleanup, leakage, and rescue receipt checks as release gates

- Version/Build: 0.1.15 committed dist eca44acc2

- Config/Flags: release proof tier with browser and rescue enabled

- Customer Comms: None; maintainer release-proof defect

- Related Incidents/Bugs: CB-226

- Fixed In: Pending 0.1.15 release proof

- Code References: - scripts/release/greenfield_matrix_quality_scoring.py
- scripts/release/greenfield_matrix_proof_scope.py
- tests/unit/install/test_greenfield_post_confirm_matrix.py
- tests/unit/install/test_greenfield_post_confirm_matrix_proof_scope.py
