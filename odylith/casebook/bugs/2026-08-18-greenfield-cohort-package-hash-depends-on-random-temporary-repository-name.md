- Bug ID: CB-333

- Status: Open

- Created: 2026-08-18

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: Recompiling the same frozen Semantic Intent packet twice at revision 14c4c454 produces proposals that differ only at observed_source.repo_name because the development cohort uses a randomly named TemporaryDirectory as the repository root. The candidate bundle therefore binds a package hash that cannot be reproduced after the temporary directory is removed, and independent reviewers cannot inspect the exact proved package bytes.

- Impact: The semantic release evaluator can claim package proof without preserving reproducible reviewer-visible package bytes, weakening independent utility review and release evidence attribution.

- Components Affected: release

- Environment(s): Odylith maintainer source-local development cohort at revision 14c4c4543a7c5676342244adc514ceb8ae035f16

- Detected By: Deterministic regeneration before independent semantic review

- Failure Signature: Same candidate packet yields proposal hashes c4a40e... and 55878f...; recursive diff contains only $.observed_source.repo_name with two random tmp directory basenames.

- Trigger Path: greenfield_semantic_development_cohort._transaction_proof -> TemporaryDirectory -> build_verified_semantic_proposal_for_repo

- Ownership: Greenfield semantic development cohort and release evidence

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: All commit candidates compiled in temporary repositories for development or holdout evidence

- SLO/SLA Impact: Blocks trustworthy release adjudication; no shipped consumer transaction corruption observed

- Data Risk: No user data loss; evidence reproducibility and auditability risk

- Security/Compliance: No direct security breach; provenance integrity is weakened

- Invariant Violated: A release proof must bind reproducible exact package bytes that independent reviewers can inspect.

- Root Cause: The cohort derives observed_source.repo_name from a randomly named temporary repository and hashes the resulting proposal, then deletes the repository without preserving the package.

- Solution: Compile each case in a deterministic case-scoped repository identity, prove recompile equality, and persist the exact reviewer package bytes or a canonical review package bound to the candidate.

- Rollback/Forward Fix: Forward fix the release harness; do not normalize or ignore the differing field in adjudication.

- Verification: Compile one packet twice under the deterministic case root, require identical package hashes, preserve package bytes, and validate that the stored hash equals transaction_proof.package_sha256.

- Prevention: Add an exact recompile-stability test and require reviewer-visible package evidence before package utility can be adjudicated.

- Agent Guardrails: Do not treat a hash as review evidence when the hashed bytes were discarded or contain random environment identity.

- Preflight Checks: Frozen revision, clean worktree, exact packet/corpus hashes, deterministic repository identity, no final holdout access

- Code References: - scripts/release/greenfield_semantic_development_cohort.py:_transaction_proof
