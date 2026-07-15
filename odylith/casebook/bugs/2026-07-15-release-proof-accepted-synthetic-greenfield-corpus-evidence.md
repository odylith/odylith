- Bug ID: CB-248

- Status: Open

- Created: 2026-07-15

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The installed Greenfield matrix could label a small hand-authored or generated synthetic case file as release-ready because release policy checked runtime options but not source provenance, corpus scale, duplicate resistance, or independent audit evidence.

- Impact: Maintainers could make an unsupported post-confirm reliability release claim; consumer workflows are not affected at runtime.

- Components Affected: odylith

- Environment(s): Odylith product-repo maintainer release matrix

- Detected By: Adversarial corpus-governance and release-system review

- Failure Signature: A release tier could complete from an arbitrary small synthetic case file without source records or an independent audit.

- Trigger Path: scripts/release/greenfield_preconfirm_matrix.py --proof-tier release --case-file <synthetic.json>

- Ownership: Greenfield release proof and commit-only transaction quality boundary

- Timeline: Captured 2026-07-15 through `odylith bug capture`.

- Blast Radius: Release documentation, automated campaign readiness, and maintainer confidence

- SLO/SLA Impact: Blocks any release-readiness claim until source-provenanced corpus proof exists.

- Data Risk: No consumer data loss; evidence integrity and claim provenance are at risk.

- Security/Compliance: No direct security impact; source and audit provenance are required for defensible release evidence.

- Invariant Violated: Release proof must be source-provenanced, independently audited, diverse, and fail closed before installation; synthetic discovery coverage must never be promoted.

- Root Cause: Release tiers relied on runtime quality options and raw case counts, while case metadata lacked provenance and audit contracts.

- Solution: Add typed case provenance, source-artifact hash validation, corpus diversity and duplicate gates, independent audit validation, direct API enforcement, and shell-wrapper release gating.

- Rollback/Forward Fix: Forward fix only; existing synthetic 240-case catalog remains discovery-only and cannot support a release claim.

- Verification: Focused provenance, matrix, campaign, shard, and failure-response suites pass; an exact installed source-provenanced 200-case proof remains required before release readiness.

- Prevention: Keep release policy in both CLI and callable paths, require audited source records in campaign shards, and label discovery output distinctly.

- Agent Guardrails: Do not equate prompt-grounded synthetic fixtures or a zero exit code with source-provenanced release proof.

- Preflight Checks: Run release-corpus preflight before any install and require browser, rescue, natural rescue, cleanup, source provenance, diversity, and audit evidence.

- Regression Tests Added: tests/unit/install/test_greenfield_matrix_corpus_provenance.py and tests/unit/install/test_greenfield_preconfirm_release_provenance.py

- Monitoring Updates: Persist corpus provenance status in matrix output and campaign failure clusters.

- Version/Build: 0.1.15 development branch

- Config/Flags: proof-tier release; release-audit-file; GREENFIELD_MATRIX_RELEASE_AUDIT_FILE

- Customer Comms: Internal maintainer claim-correction; no consumer action required.

- GitHub Status: fixed_pending_release

- Code References: - scripts/release/greenfield_matrix_corpus_provenance.py
- scripts/release/greenfield_preconfirm_matrix.py
- scripts/release/greenfield_matrix_campaign_shard_runner.py
