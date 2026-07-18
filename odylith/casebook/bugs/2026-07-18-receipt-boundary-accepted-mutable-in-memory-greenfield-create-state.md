- Bug ID: CB-276

- Status: Open

- Created: 2026-07-18

- Severity: P0

- Reproducibility: Always

- Type: DataLoss

- Description: The post-confirm Greenfield executor accepted a caller-supplied sealed projection. A caller could forge the private attestation and commit without a receipt, or mutate nested repository-write-set data after receipt loading and cause bytes different from the reviewed package to be written.

- Impact: A confirmed Greenfield create could write governed records that were not the package the user reviewed.

- Components Affected: odylith

- Environment(s): Odylith product runtime source tree

- Detected By: Independent adversarial architecture review

- Failure Signature: A forged in-memory SealedProductCreateCommit wrote a forged Radar record; mutating nested before_fingerprints or write-set data on a receipt-loaded projection altered subsequent writes.

- Trigger Path: Direct commit_greenfield_create_transaction invocation after confirmation

- Ownership: Greenfield precompiled create transaction kernel

- Timeline: Captured 2026-07-18 through `odylith bug capture`.

- Blast Radius: Every in-process Greenfield create caller and all governed write surfaces in its repository write set.

- SLO/SLA Impact: Invalidates the deterministic post-confirm guarantee.

- Data Risk: Unreviewed governed artifacts could be written; rollback remained available.

- Security/Compliance: No external attacker claim; the defect was an internal execution-integrity boundary failure.

- Invariant Violated: Confirmation must commit only bytes from the hash-bound pre-confirm receipt, with no caller-held mutable product state at the write boundary.

- Root Cause: The executor treated an attested public dataclass as authority and retained mutable nested mappings after receipt load.

- Solution: Commit accepts only transaction_file plus confirmed transaction_hash, reloads and verifies the receipt inside the write boundary, and sealed projections retain canonical JSON with copy-on-access.

- Rollback/Forward Fix: Forward fix only; no affected production transaction was identified.

- Verification: 168 receipt-boundary regression tests and 55 clean-process command-adapter tests pass; independent reviewers reproduced the old bypasses and found no remaining P0-P2 path.

- Prevention: Keep receipt reload and confirmed-hash comparison inside commit; preserve the nested-map mutation, forged-object rejection, operation-contract drift, and full runtime-frontier tests.

- Agent Guardrails: Do not infer a deterministic transaction boundary from type checks or frozen dataclasses. Adversarially attempt forged authority and nested mutation before claiming commit-only behavior.

- Preflight Checks: Run the receipt-boundary and command-adapter clusters before release claims.

- Regression Tests Added: test_commit_reloads_receipted_bytes_instead_of_using_a_mutable_loaded_projection; test_commit_reloads_and_rejects_receipted_operation_contract_drift_before_write; runtime-frontier coverage tests.

- Monitoring Updates: None; compiler receipt and transaction hash remain the operator-visible integrity evidence.

- Version/Build: Unreleased source branch 2026/freedom/v0.1.15

- Customer Comms: Not required; no released affected transaction identified.

- Related Incidents/Bugs: CB-271, CB-273

- GitHub Status: fixed_pending_release

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_create_commit.py
- src/odylith/runtime/domain_intelligence/greenfield_commit_transaction.py
- tests/unit/runtime/test_greenfield_transaction_provenance.py
