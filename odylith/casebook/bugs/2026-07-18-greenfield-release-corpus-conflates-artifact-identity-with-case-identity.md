- Bug ID: CB-279

- Status: Open

- Created: 2026-07-18

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The release provenance policy permits two cases to share one retained artifact hash while each claims a unique source ID and source URI. The only passing metamorphic fixture relies on that relabeling. The audit schema also accepts a self-asserted independent reviewer flag without recording whether the review is automated or human, and generator tests allow source spans the release validator cannot resolve.

- Impact: Maintainers can mistake relabeled artifact records and opaque automated review for independent release evidence, blocking a truthful release-ready claim.

- Components Affected: odylith

- Environment(s): Odylith product-repo maintainer Greenfield release corpus validation

- Detected By: Independent adversarial release-policy review

- Failure Signature: A 200-case fixture passes while 40 cases reuse 20 artifact files with fresh source IDs and source URIs; review records contain only a boolean independent flag and opaque reviewer ID.

- Trigger Path: scripts/release/greenfield_matrix_corpus_provenance.py evaluate_release_corpus()

- Ownership: Greenfield release provenance and audit boundary

- Timeline: Captured 2026-07-18 through `odylith bug capture`.

- Blast Radius: All future source-provenanced Greenfield release campaigns

- SLO/SLA Impact: Blocks credible release readiness until identity and audit semantics are corrected.

- Data Risk: Evidence-integrity risk; no consumer governed records are written.

- Security/Compliance: Provenance and audit claims are insufficiently precise for defensible compliance evidence.

- Invariant Violated: A release corpus must preserve one truthful source identity per retained artifact, bind metamorphic variants explicitly, and label review authority honestly.

- Root Cause: The policy treats source ID and source URI as uniqueness tokens while metamorphic completeness uses artifact hash, without defining their relationship; audit metadata lacks reviewer type and structured evidence binding.

- Solution: Make source identity artifact-level; permit at most one explicitly paired metamorphic variant under the same identity; require distinct-source and artifact floors; add reviewer kind, method, and structured evidence binding; validate supported source spans at writer boundaries.

- Rollback/Forward Fix: Forward fix only. Existing synthetic corpus and the current passing provenance fixture remain non-release evidence.

- Verification: Add adversarial regression cases for source relabeling, review-kind ambiguity, invalid serializable spans, and the corrected release corpus shape; rerun corpus, generator, shard, and installed release proof.

- Prevention: Do not create corpus records or label release readiness until source identity and review-kind semantics are machine-validated.

- Agent Guardrails: Never manufacture fresh source IDs or URIs for a reused artifact, and never call automated audit evidence human review.

- Preflight Checks: Evaluate corpus identity, structured review evidence, span validity, and full installed matrix before acquisition or release execution.

- Monitoring Updates: Expose distinct artifact/source counts and review-kind distribution in corpus summaries.

- Version/Build: 0.1.15 development branch

- Config/Flags: proof-tier release; release-audit-file

- Customer Comms: Internal maintainer claim correction; no consumer action.

- Related Incidents/Bugs: CB-248, CB-252, CB-275, CB-278

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_matrix_corpus_provenance.py
- tests/unit/install/test_greenfield_matrix_corpus_provenance.py
