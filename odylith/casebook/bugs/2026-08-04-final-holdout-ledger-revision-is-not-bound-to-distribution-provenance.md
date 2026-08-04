- Bug ID: CB-314

- Status: Open

- Created: 2026-08-04

- Severity: P1

- Reproducibility: Consistent

- Type: Test

- Description: The semantic release CLI accepts any 40-character hexadecimal implementation revision and would record it in the one-shot ledger without comparing it to the built distribution's signed build-provenance head. A mistyped non-existent revision passed preflight during the aborted CB-313 attempt.

- Impact: A passing holdout could be attributed to the wrong implementation commit, undermining reproducibility and release audit integrity.

- Components Affected: release

- Environment(s): Odylith 0.1.15 local release assets with build-provenance.v1.json at commit 751b8f82a

- Detected By: Adversarial inspection of the aborted semantic holdout command and distribution provenance

- Failure Signature: Implementation revision 751b8f82a3ee465177403e56c51e3e4b7341e12d passed format validation although the distribution provenance head is 751b8f82a545ea9b14e168e19cf4542ce44f1f0f.

- Trigger Path: Supply any 40-hex --implementation-revision to the semantic release campaign regardless of dist build-provenance.v1.json.

- Ownership: Release campaign implementation identity and final-holdout ledger binding

- Timeline: Observed 2026-08-04 before any holdout execution; ledger remained absent because CB-313 failed earlier.

- Blast Radius: Every semantic final-holdout claim where the operator mistypes or misstates the implementation revision.

- SLO/SLA Impact: Can invalidate the auditability of an otherwise successful one-shot release proof.

- Data Risk: No consumer data risk; release evidence can be misattributed.

- Security/Compliance: Integrity and provenance defect; no signature bypass, but the ledger does not consume the available signed provenance identity.

- Invariant Violated: The one-shot holdout ledger implementation_revision must exactly equal the tested distribution's build-provenance source head.

- Root Cause: Campaign validation checks only revision syntax and never reads the dist build provenance already emitted by local release construction.

- Solution: Fail preflight unless --implementation-revision exactly matches build-provenance.v1.json source.head and source.sha for the selected distribution.

- Rollback/Forward Fix: Forward fix in the release harness; do not infer identity from the directory name or current Git checkout.

- Verification: Add matching, mismatching, malformed, and missing distribution-provenance tests before the next one-shot attempt.

- Prevention: Derive every release ledger identity from signed package provenance and use operator input only as an explicit cross-check.

- Agent Guardrails: Never claim a holdout revision from a short hash, directory label, current branch, or manually completed hash.

- Preflight Checks: Read dist/build-provenance.v1.json and compare both source.head and source.sha before claiming the ledger.

- Regression Tests Added: Extend campaign-runner semantic release tests to reject a revision that differs from build-provenance.v1.json.

- Monitoring Updates: Persist the verified distribution provenance hash in release proof inputs and the terminal campaign payload.

- Version/Build: 0.1.15 dist /private/tmp/odylith-local-release-0.1.15-751b8f82a

- Config/Flags: Semantic release with explicit implementation revision and one-shot ledger.

- Customer Comms: Internal release-proof integrity defect; no consumer project affected.

- Related Incidents/Bugs: CB-313, CB-312, B-142

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_matrix_campaign_runner.py
- scripts/release/greenfield_final_holdout_guard.py
- /private/tmp/odylith-local-release-0.1.15-751b8f82a/build-provenance.v1.json
