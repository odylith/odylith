- Bug ID: CB-322

- Status: FixedPendingRelease

- Created: 2026-08-05

- Severity: P0

- Reproducibility: Always

- Type: Test

- Description: The semantic final-holdout contract accepted cases whose required_terms and leakage_terms overlapped, making successful domain custody mathematically impossible and wasting the one-shot release run.

- Impact: Release proof can report zero quality for a package that no implementation can satisfy, obscuring real Greenfield defects and consuming blinded holdout capacity.

- Components Affected: release

- Environment(s): v0.1.15 exact revision ba25fbd9e clean installed one-shot holdout

- Detected By: Independent post-run adversarial adjudication

- Failure Signature: All 24 cases declared at least one term as both required product vocabulary and forbidden source leakage; 0/24 run terminalized failed.

- Trigger Path: greenfield_matrix_campaign_runner.py semantic release proof with final-holdout.v1.json SHA-256 2a6dea8c58ebb05400f03faf7ad1bf37c13972a651eeaeb7ff721b0f41bf4eff

- Ownership: Release evaluation contract and holdout annotation governance

- Timeline: Captured 2026-08-05 through `odylith bug capture`.

- Blast Radius: Any semantic release holdout using contradictory custody term sets

- SLO/SLA Impact: Blocks trustworthy v0.1.15 release readiness and consumes one-shot evaluation time

- Data Risk: No consumer data loss; hidden evaluation capacity and result integrity are compromised

- Security/Compliance: Security posture assessed: no credential exposure; audit integrity is at risk because a sealed proof can have an unsatisfiable oracle.

- Invariant Violated: No release case may require and forbid the same product term; final annotations must be independently reviewable before product execution

- Root Cause: The frozen evaluation contract validates grounding and hashes but did not compare required_terms and leakage_terms with the same token-containment semantics used by downstream leakage scoring or verify that leakage terms are non-product source sentinels.

- Solution: Reject exact, morphological, and contiguous containment overlap between required and forbidden term sets during frozen evaluation preflight by using the downstream leakage matcher's term semantics. Keep distinctive source-only sentinels and independent semantic review as holdout-authoring obligations rather than weakening product scoring after execution.

- Verification: Frozen-contract regressions reject both a case requiring `Archive` while forbidding `archive` and a case requiring `archive ledger` while forbidding the contained term `archive`. The disclosed failed corpus is now a 24-case retired regression fixture and cannot be reused as blinded evidence. Clean installed proof with a newly authored, independently reviewed holdout remains pending.

- Prevention: Encode custody-set disjointness and independent-review provenance in the final-holdout preflight.

- Agent Guardrails: Never tune product code to a holdout term that the same oracle both requires and forbids.

- Preflight Checks: Validate disjoint term sets, accepted-fact compatibility, tracked-corpus leakage, checksum inventory, browser runtime, and dist provenance before ledger claim.

- Related Incidents/Bugs: CB-258, CB-321

- Code References: - scripts/release/greenfield_evaluation_contract.py
- scripts/release/greenfield_matrix_leakage.py
- scripts/release/greenfield_matrix_case_file.py

- Fixed In: pending 0.1.15
