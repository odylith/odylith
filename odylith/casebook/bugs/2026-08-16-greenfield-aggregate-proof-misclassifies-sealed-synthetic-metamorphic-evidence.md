- Bug ID: CB-327

- Status: Open

- Created: 2026-08-16

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: A 24/24 installed disclosed replay remains failed because frozen-contract tracked-corpus lookup is rooted at the sealed input directory, discovery synthetic cases are forced through source-provenance requirements, role ownership is checked by literal ontology token, and raw full-field Jaccard reports semantically equivalent render variants as drift.

- Impact: Correct installed product behavior cannot advance to the authorized replacement holdout, while genuine projection drift is obscured among evaluator false positives.

- Components Affected: release

- Environment(s): 0.1.15 exact local release assets from commit 987814a75, disclosed-v3 discovery campaign

- Detected By: Installed greenfield aggregate metamorphic and frozen semantic release gates

- Failure Signature: 24/24 cases score 10/10 but result status is failed with 45 metamorphic issues and frozen evaluation contract tracked corpus unavailable under sealed-input root

- Trigger Path: greenfield_preconfirm_matrix.py with disclosed v3 case file, annotations, manifest, and sealed-release-input-root

- Ownership: Release evaluator frozen-contract authority and metamorphic comparison

- Timeline: Captured after commit 987814a75 produced 24/24 individual passes but aggregate failure.

- Blast Radius: Synthetic discovery replays and final release proof using external sealed holdout inputs

- SLO/SLA Impact: Delivery SLO impact: release readiness and holdout authorization blocked; no production outage

- Data Risk: Domain risk: none. Delivery risk: false release stops mixed with real projection failures. Operational risk: expensive 24-case reruns. No data mutation or loss.

- Security/Compliance: Trust-boundary impact: evaluator must not self-attest provenance or skip a failed frozen contract. Privacy, accessibility, safety, and customer data are unaffected; provenance remains fail-closed.

- Invariant Violated: Tracked-corpus authority must remain repo-rooted, sealed inputs must validate independently, and metamorphic scoring must distinguish semantic equivalence from real typed-fact drift without fabricated provenance

- Root Cause: Caller conflates sealed-input containment root with tracked-corpus authority; metamorphic tier handling lacks discovery-synthetic semantics; question grounding is lexical; comparator uses raw field-token Jaccard.

- Solution: Separate authority roots, retain strict release provenance while recognizing unclaimed discovery synthetic cases, ground role through ownership semantics, and compare typed semantic axes with real-drift negative controls.

- Rollback/Forward Fix: Forward fix evaluator only; do not rerun product campaign until retained-result re-evaluation is clean.

- Verification: Focused authority, tier, role, and comparator tests; full evaluator and security/proof suites; then in-memory re-evaluation of the retained 24-case result with exactly the genuine product issues remaining.

- Prevention: Pin split authority roots and false-positive/real-drift paired controls.

- Agent Guardrails: Do not relabel tracked fixtures as independent holdout, invent source IDs or hashes, lower frozen floors, add case IDs or fixture phrase allowlists, or rerun the untouched holdout.

- Preflight Checks: Exact retained result and both input hashes must remain unchanged; replacement holdout remains sealed.

- Regression Tests Added: test_frozen_contract_uses_repo_tracked_corpus_authority; test_synthetic_regression_metamorphic_identity_requires_no_source_claim; test_role_field_grounding_accepts_ownership_language; test_typed_metamorphic_equivalence_preserves_real_drift_failures

- Version/Build: 0.1.15 / 987814a75

- Related Incidents/Bugs: CB-316, CB-323, CB-326, B-142

- Code References: - scripts/release/greenfield_preconfirm_matrix.py
- scripts/release/greenfield_evaluation_contract.py
- scripts/release/greenfield_matrix_metamorphic.py
- scripts/release/greenfield_matrix_clarification.py
