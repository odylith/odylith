- Bug ID: CB-300

- Status: Open

- Created: 2026-07-30

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A repaired typed intent required a final re-seal and one clean pre-confirm recompile. The second manifest replaced the first manifest, dropping the rescue tier, repaired issue code, and PatchSet proof even though the repaired package remained valid.

- Impact: Auditability of a successful high-trust onboarding transaction was incomplete and the natural rescue release proof failed.

- Components Affected: domain-intelligence

- Environment(s): Installed v0.1.15 natural structured-rescue matrix case

- Detected By: Installed pre-confirm matrix

- Failure Signature: natural rescue proof did not preserve the last repair PatchSet in the final manifest

- Trigger Path: greenfield create --confirm with structured rescue proof enabled

- Ownership: Greenfield transaction compiler and pre-confirm manifest boundary

- Timeline: Captured 2026-07-30 through `odylith bug capture`.

- Blast Radius: Any repair that changes typed facts and requires a final authority re-seal.

- SLO/SLA Impact: Release matrix fails despite no post-confirm write failure.

- Data Risk: No data loss: the failure remains before the atomic commit.

- Security/Compliance: Compliance assessed: audit and traceability evidence was incomplete, but policy, privacy, accessibility, and safety writes remained blocked until proof passed.

- Invariant Violated: The final transaction manifest must retain all pre-confirm repair evidence that contributed to the sealed package.

- Root Cause: The final clean recompile overwrote the earlier repair manifest instead of composing the two pre-confirm passes.

- Solution: Merge pass records, repaired issue codes, rescue activation, tier, budget, elapsed time, and the last repair PatchSet into the final manifest.

- Verification: Focused manifest composition test, pre-confirm engine tests, and the final installed natural-rescue matrix case passed.

- Prevention: Treat final authority re-seal as a pre-confirm compiler stage whose manifest must compose prior repair evidence.

- Agent Guardrails: Never describe a recompiled transaction as audit-complete unless its final manifest retains the repair history that changed typed facts.

- Preflight Checks: Run structured-rescue proof before release acceptance when final typed facts can be restaged.

- Regression Tests Added: test_final_recompile_preserves_preconfirm_rescue_evidence.

- Version/Build: 0.1.15 local release proof

- Related Incidents/Bugs: CB-299

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_proposals.py
- tests/unit/runtime/test_greenfield_transaction_intent_authority.py
