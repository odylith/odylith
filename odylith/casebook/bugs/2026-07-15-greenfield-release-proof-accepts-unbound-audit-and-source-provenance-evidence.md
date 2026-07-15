- Bug ID: CB-252

- Status: FixedPendingRelease

- Created: 2026-07-15

- Severity: P1

- Fixed: Pending

- Fixed In: v0.1.15

- Reproducibility: Always

- Type: Product

- Description: Release-corpus validation accepts truthy non-boolean reviewer independence, checks only the shape of a review digest, and accepts source excerpts found anywhere in a local artifact without resolving the declared span. The release launcher can also downgrade incomplete release intent into discovery success.

- Impact: A future release could claim source-provenanced independent evidence without a verified review artifact, source-span binding, or fail-closed release-intent path.

- Components Affected: odylith

- Environment(s): Greenfield release corpus validator and installed-matrix launcher

- Detected By: Adversarial release-proof contract review

- Failure Signature: JSON independent="false" is truthy; review_evidence_sha256 is never bound to a file; source excerpt is checked outside declared span; partial release launcher inputs select discovery tier.

- Trigger Path: Validate release corpus or invoke bin/greenfield-preconfirm-matrix with incomplete release prerequisites.

- Ownership: Greenfield release provenance validator and release matrix launchers

- Timeline: Captured 2026-07-15 through `odylith bug capture`.

- Blast Radius: All future greenfield release-readiness claims and source-provenanced corpus campaigns.

- SLO/SLA Impact: Release-readiness evidence can reach false green states; no release claim is admissible until corrected.

- Data Risk: Privacy: no customer data is written. Integrity: audit and provenance claims can be forged by self-reported metadata.

- Security/Compliance: Security: supply-chain and provenance controls are insufficient because the validator can accept unbound evidence metadata. Compliance: release evidence cannot support an auditable provenance claim.

- Invariant Violated: Release proof must bind every independent review and declared source span to hashed stored evidence, and intended release runs must fail closed when prerequisites are incomplete.

- Root Cause: Policy validation treats metadata as self-asserted rather than as linked, typed, and hash-verified artifacts; shell launcher infers discovery when release inputs are incomplete.

- Solution: Require strict JSON booleans, repository-contained review-evidence paths with byte hashes, source spans resolved against captured artifacts, URI and source-ID diversity checks, and an explicit release-intent flag that rejects partial input. Release campaigns now validate each case file with only its own audits and then validate the full union with the complete audit set.

- Rollback/Forward Fix: Forward fix only; synthetic discovery and any current release corpus remain non-release evidence.

- Verification: 2026-07-15: 181 focused release-proof tests passed. They reject truthy audit booleans, missing, mismatched, and repo-escaping review artifacts, unresolved and off-span excerpts, repeated source IDs or URIs, incomplete declared release intent, and release files that fail independently despite a passing union. Fresh installed replay also confirmed a materially incomplete CAR-T request receives one focused no-write first-path question rather than a failed create. An independently auditable 200+ source corpus remains required before any release-readiness claim.

- Prevention: Never call a corpus release-provenanced based on self-reported metadata or discovery output.

- Agent Guardrails: Do not manufacture a source corpus or relax the validator to pass a release campaign; preserve evidence binding and fail closed.

- Related Incidents/Bugs: CB-248

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_matrix_corpus_provenance.py
- bin/greenfield-preconfirm-matrix
- scripts/release/greenfield_matrix_campaign_shard_runner.py
