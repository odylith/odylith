- Bug ID: CB-207

- Status: Open

- Created: 2026-06-26

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Greenfield post-confirm package repair repeats risk prose across surfaces

- Impact: Confirmed create can fail before governed records are written when the package repeats the same risk sentence across multiple generated artifacts.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo maintainer source-local unit proof on branch 2026/freedom/v0.1.15.

- Detected By: Focused greenfield proposal regression tests after artifact quality hardening.

- Failure Signature: greenfield rendered package repeats noncanonical prose across 3 artifact(s): Risks: Combining cart, payment, and order state would hide failure recovery.

- Trigger Path: .venv/bin/python -m pytest tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_shapes_radar_specs_with_domain_intelligence_substrate tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_commits_records_with_dashboard_warning_when_refresh_fails -q

- Ownership: Greenfield post-confirm semantic package repair, package repetition gate, and artifact projection boundaries.

- Timeline: Captured 2026-06-26 through `odylith bug capture`.

- Blast Radius: Confirmed greenfield create, Radar/project/package previews, operator release-readiness proof, and arbitrary domains where one semantic risk is projected into multiple surfaces.

- SLO/SLA Impact: Blocks governed writes and can consume rescue-loop time instead of repairing within the standard path.

- Data Risk: No data loss; governance records are correctly not written, but product intent remains unmaterialized.

- Security/Compliance: No direct security exploit; repeated risk prose can weaken review clarity for compliance or safety-sensitive projects.

- Invariant Violated: Post-confirm repair must repair repeated semantic projection at the model/projection layer before the final fail-closed write gate.

- Root Cause: The package repair path flags repeated noncanonical prose but does not yet repair the affected semantic projection, so the same risk sentence survives across three rendered artifacts.

- Solution: Repair the semantic projection or package repair owner so one risk fact can be expressed once canonically or projected with surface-specific wording without weakening the repetition gate.

- Verification: Focused greenfield proposal tests must pass, followed by broad post-confirm quality tests and fresh live simulations.

- Prevention: Before future repetition fixes, search Casebook for prior package-repetition guardrails and avoid adding local regex token loops or domain-specific risk exceptions.

- Agent Guardrails: Use semantic projection ownership and package repair, not project-specific wording or gate weakening; do not repeat failed local token-loop approaches from prior post-confirm guardrails.

- Preflight Checks: Read CB-205 and the May 15 confirmed-create bug guardrails before editing post-confirm semantic repetition code.

- Regression Tests Added: Existing failing tests identify the escaped mechanism; add or update focused package-repair coverage with the fix.

- Related Incidents/Bugs: CB-205; 2026-05-15-confirmed-greenfield-create-must-fail-closed-without-accepted-product-narrative

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_post_confirm_package_repair.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_completion.py
- tests/unit/runtime/test_greenfield_proposals.py
