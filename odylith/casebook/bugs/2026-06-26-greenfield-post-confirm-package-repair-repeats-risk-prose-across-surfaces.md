- Bug ID: CB-207

- Status: Closed

- Created: 2026-06-26

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Greenfield post-confirm package repair repeats risk prose across surfaces

- Impact: Confirmed create can fail before governed records are written when the package repeats the same risk sentence across multiple generated artifacts.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo maintainer source-local unit proof on branch 2026/freedom/v0.1.15; fresh installed release matrix against dist `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-e7bc3be3`.

- Environment Update: 2026-07-01 fresh installed variance against `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-925545d8` persisted proof at `/tmp/greenfield-post-confirm-fresh-variance-925545d8.v1.json`. Seven of eight new domains passed with hard 10/10 scores, browser proof, complete governed records, standard create times of 24.648-25.706s, leakage proof across 114 generated terms, clean temp cleanup, synthetic rescue at 33.170s, and natural structured rescue at 64.368s. One document/status-style dispute workflow failed before governed writes in 12.336s because all three Registry component specs repeated the same generated `The product failure to guard against` sentence and the blocker surfaced as `legacy_package_artifact_gate`.

- Closure Update: 2026-07-01 rebuilt dist `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-5b94bd8f` passed both final installed proof lanes. Fresh high-variance proof passed 8/8 standard cases at 10/10 with zero issues, browser proof, platform leakage proof across 131 generated terms, temp cleanup, max standard create time 25.701s, synthetic rescue at 33.288s, and natural structured rescue at 56.548s. Maintained release proof passed 13/13 standard cases at 10/10 with zero issues, browser proof, platform leakage proof across 213 generated terms, temp cleanup, max standard create time 28.062s, synthetic rescue at 33.620s, and natural structured rescue at 56.311s.

- Detected By: Focused greenfield proposal regression tests after artifact quality hardening; maintained installed greenfield matrix for the v0.1.15 release gate.

- Failure Signature: greenfield rendered package repeats noncanonical prose across 3 artifact(s): Risks: Combining cart, payment, and order state would hide failure recovery.
  Fresh installed signature on 2026-06-29: a coordinated disclosure workflow failed before governed writes in 12.96s with `greenfield rendered package repeats noncanonical prose across 3 artifact(s)` for the repeated object-list tail beginning with affected review scope, decision scope, evidence custody, signoff, and release-readiness terms.
  Fresh installed signature on 2026-07-01: a document/status-style dispute workflow failed before governed writes with `greenfield rendered package repeats noncanonical prose across 3 artifact(s)` for the repeated generated Registry proof/risk sentence beginning `The product failure to guard against: Explanation context can be attached to the wrong review record...`.

- Trigger Path: .venv/bin/python -m pytest tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_shapes_radar_specs_with_domain_intelligence_substrate tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_commits_records_with_dashboard_warning_when_refresh_fails -q

- Ownership: Greenfield post-confirm semantic package repair, package repetition gate, and artifact projection boundaries.

- Timeline: Captured 2026-06-26 through `odylith bug capture`; reopened as release-blocking installed proof on 2026-06-29 against dist `odylith-local-release-0.1.15-e7bc3be3`; closed on 2026-07-01 after rebuilt installed proof passed fresh high-variance and maintained release matrices.

- Blast Radius: Confirmed greenfield create, Radar/project/package previews, operator release-readiness proof, and arbitrary domains where one semantic risk is projected into multiple surfaces.

- SLO/SLA Impact: Blocks governed writes and can consume rescue-loop time instead of repairing within the standard path.

- Data Risk: No data loss; governance records are correctly not written, but product intent remains unmaterialized.

- Security/Compliance: No direct security exploit; repeated risk prose can weaken review clarity for compliance or safety-sensitive projects.

- Invariant Violated: Post-confirm repair must repair repeated semantic projection at the model/projection layer before the final fail-closed write gate.

- Root Cause: The package repair path flags repeated noncanonical prose but does not yet repair the affected semantic projection, so the same risk sentence survives across three rendered artifacts. The 2026-06-29 installed failure narrowed one generic owner: first-path canonical projection facts carried full actor/action/object facts, but did not carry typed custody for action-complement or object-list tails rendered without the leading action/object. The 2026-07-01 installed failure narrowed a separate generic owner: `ensure_component_contract` rebuilt complete semantic component contracts through specialized document/status profiles and replaced each component-local `unique_failure` with the same profile-level proof/risk failure. The Registry narrative renderer then repeated that shared generated failure sentence across three component specs, and package repetition surfaced the raw string as `legacy_package_artifact_gate` because package-level semantic repetition metadata is still not typed.

- Solution: Repair semantic projection custody so compact action-complement and object-list tail variants preserve canonical fact identity, semantic node/source path, projection id, and sanctioned surface roles before package repetition scoring. Preserve component-local semantic contract failure facts when applying specialized component profiles, so profile structure does not stamp one shared generated risk sentence across siblings. Do not add disclosure/security, temporary-case vocabulary, profile-phrase vocabulary, regex allowlists, or weaker repetition thresholds.

- Verification: Focused greenfield proposal tests must pass, followed by broad post-confirm quality tests and fresh live simulations. Source proof for the 2026-07-01 profile-contract fix passed 53 component/Registry/package tests and exact source-local replay of the saved failed intent committed governed records in 14.989s with zero final issues. Final release proof passed on rebuilt dist `odylith-local-release-0.1.15-5b94bd8f`: fresh high-variance installed matrix at `/tmp/greenfield-post-confirm-fresh-variance-5b94bd8f.v1.json` passed 8/8 standard cases at hard 10/10 with zero issues, max standard create 25.701s, browser proof, leakage proof, temp cleanup, synthetic rescue, and natural structured rescue; maintained installed matrix at `/tmp/greenfield-post-confirm-matrix-5b94bd8f.v1.json` passed 13/13 standard cases at hard 10/10 with zero issues, max standard create 28.062s, browser proof, leakage proof, temp cleanup, synthetic rescue, and natural structured rescue.

- Prevention: Before future repetition fixes, search Casebook for prior package-repetition guardrails and avoid adding local regex token loops, domain-specific risk/security exceptions, or rendered-string allowances that bypass typed projection custody.

- Agent Guardrails: Use semantic projection ownership and package repair, not project-specific wording or gate weakening; do not repeat failed local token-loop approaches from prior post-confirm guardrails. Treat action-complement and object-list tails as first-class canonical projection facts when they can be rendered without their lead action/object.

- Preflight Checks: Read CB-205 and the May 15 confirmed-create bug guardrails before editing post-confirm semantic repetition code.

- Regression Tests Added: Existing failing tests identify the escaped mechanism; add or update focused package-repair coverage with the fix.

- Related Incidents/Bugs: CB-205; 2026-05-15-confirmed-greenfield-create-must-fail-closed-without-accepted-product-narrative

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_post_confirm_package_repair.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_completion.py
- src/odylith/runtime/domain_intelligence/greenfield_canonical_projection_facts.py
- src/odylith/runtime/artifact_quality/greenfield_package_quality.py
- tests/unit/runtime/test_greenfield_proposals.py
