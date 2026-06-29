- Bug ID: CB-207

- Status: Open

- Created: 2026-06-26

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Greenfield post-confirm package repair repeats risk prose across surfaces

- Impact: Confirmed create can fail before governed records are written when the package repeats the same risk sentence across multiple generated artifacts.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo maintainer source-local unit proof on branch 2026/freedom/v0.1.15; fresh installed release matrix against dist `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-e7bc3be3`.

- Detected By: Focused greenfield proposal regression tests after artifact quality hardening; maintained installed greenfield matrix for the v0.1.15 release gate.

- Failure Signature: greenfield rendered package repeats noncanonical prose across 3 artifact(s): Risks: Combining cart, payment, and order state would hide failure recovery.
  Fresh installed signature on 2026-06-29: `security disclosure council` failed before governed writes in 12.96s with `greenfield rendered package repeats noncanonical prose across 3 artifact(s)` for the repeated object-list tail beginning `Affected partner review, embargo decisions, evidence custody, legal signoff, and public advisory release readiness...`.

- Trigger Path: .venv/bin/python -m pytest tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_shapes_radar_specs_with_domain_intelligence_substrate tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_commits_records_with_dashboard_warning_when_refresh_fails -q

- Ownership: Greenfield post-confirm semantic package repair, package repetition gate, and artifact projection boundaries.

- Timeline: Captured 2026-06-26 through `odylith bug capture`; reopened as release-blocking installed proof on 2026-06-29 against dist `odylith-local-release-0.1.15-e7bc3be3`.

- Blast Radius: Confirmed greenfield create, Radar/project/package previews, operator release-readiness proof, and arbitrary domains where one semantic risk is projected into multiple surfaces.

- SLO/SLA Impact: Blocks governed writes and can consume rescue-loop time instead of repairing within the standard path.

- Data Risk: No data loss; governance records are correctly not written, but product intent remains unmaterialized.

- Security/Compliance: No direct security exploit; repeated risk prose can weaken review clarity for compliance or safety-sensitive projects.

- Invariant Violated: Post-confirm repair must repair repeated semantic projection at the model/projection layer before the final fail-closed write gate.

- Root Cause: The package repair path flags repeated noncanonical prose but does not yet repair the affected semantic projection, so the same risk sentence survives across three rendered artifacts. The fresh installed failure narrows the generic owner: first-path canonical projection facts carry full actor/action/object facts, but do not carry typed custody for action-complement or object-list tails rendered without the leading action/object. The package repetition gate therefore treats legitimate cross-surface first-path reuse as noncanonical.

- Solution: Repair semantic projection custody so compact action-complement and object-list tail variants preserve canonical fact identity, semantic node/source path, projection id, and sanctioned surface roles before package repetition scoring. Do not add disclosure/security vocabulary, regex allowlists, or weaker repetition thresholds.

- Verification: Focused greenfield proposal tests must pass, followed by broad post-confirm quality tests and fresh live simulations. Release proof must rerun the installed thirteen-case matrix against a rebuilt dist, including `security disclosure council`, with governed writes, hard 10/10 standard cases, synthetic rescue smoke, and temp matrix cleanup.

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
