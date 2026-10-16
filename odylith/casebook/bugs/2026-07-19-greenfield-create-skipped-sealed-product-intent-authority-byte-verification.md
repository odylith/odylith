- Bug ID: CB-286

- Status: Open

- Created: 2026-07-19

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The post-confirm create path required a nonempty Product Intent authority snapshot but did not prove that the compact authority used at commit was byte-identical to the pre-confirm authority embedded in the sealed proposal. A re-sealed transaction could therefore pass the old presence check before the governed write boundary.

- Impact: A confirmed transaction could execute with authority data not proven identical to the pre-confirmed authority.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repository source-local candidate and installed create contract.

- Detected By: Independent adversarial post-confirm boundary review

- Failure Signature: require_sealed_commit_transaction accepted nonempty intent_authority without byte-exact comparison against proposal product_intent_authority.

- Trigger Path: greenfield propose to sealed ProductCreateTransaction then greenfield create --transaction-file ... --transaction-hash ... --confirm

- Ownership: Greenfield precompiled create transaction commit boundary

- Timeline: Captured 2026-07-19 through `odylith bug capture`.

- Blast Radius: All Greenfield confirmed-create transactions.

- SLO/SLA Impact: The post-confirm product-path integrity guarantee was incomplete.

- Data Risk: No known partial write or data loss; integrity and audit provenance risk before the write boundary.

- Security/Compliance: Integrity and audit provenance risk; no external security exposure identified.

- Invariant Violated: CONFIRM commits the exact authority and compiled package reviewed before confirmation.

- Root Cause: The post-confirm loader retained only a presence check and did not carry a parser-free sealed authority comparison into the commit-only projection.

- Solution: Use a parser-free byte-exact sealed-authority verifier before write, bind its runtime identity into the compiler receipt, and reject stale identities.

- Rollback/Forward Fix: Forward fix required; old compiler identities must fail closed and no governed write may begin after authority verification failure.

- Verification: Focused provenance and create-transaction tests prove malformed or re-sealed authority fails before GreenfieldApplyTransaction and no new pre-confirm authority runtime loads during create.

- Prevention: Every post-confirm authority consumer must be listed in the explicit allowed-operation contract and compiler runtime identity inventory.

- Agent Guardrails: Never treat a nonempty authority hash as proof of sealed authority identity; do not import Markdown-normalizing pre-confirm verifiers into create.

- Preflight Checks: Run transaction provenance, create-transaction, commit recovery, and fresh installed proof before release.

- Regression Tests Added: test_commit_rejects_malformed_or_resealed_authority_before_write and canonical create runtime trace coverage.

- Monitoring Updates: Installed matrix receipt provenance must record the sealed Product Intent facts hash observed from each recovery phase.

- Version/Build: 0.1.15 candidate

- Config/Flags: Default hash-bound greenfield create path

- Customer Comms: Caught before release; no customer communication needed.

- Related Incidents/Bugs: CB-273

- GitHub Status: fixed_pending_release

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_commit_transaction.py
- src/odylith/runtime/domain_intelligence/greenfield_sealed_product_intent_authority.py
