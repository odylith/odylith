- Bug ID: CB-264

- Status: Open

- Created: 2026-07-17

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: The shared first-path parser can retain an automated actor prefix such as AI reviewer in material_action, even though downstream product truth needs the action clause without host or automation identity.

- Impact: Pre-confirm artifacts can carry an automated actor label into the material action and drift from the accepted human product path.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo source-local runtime validation

- Detected By: Full runtime shard replay

- Failure Signature: test_first_path_clause_rendering_stays_in_dedicated_owner expected Record follow-up notes but received The AI reviewer record follow-up notes

- Trigger Path: hatch run pytest tests/unit/runtime/test_greenfield_preconfirm_slop_regressions.py::test_first_path_clause_rendering_stays_in_dedicated_owner -q --tb=short -p no:cacheprovider

- Ownership: Greenfield first-path semantic compiler

- Timeline: Captured 2026-07-17 through `odylith bug capture`.

- Blast Radius: All pre-confirm proposal projections that consume FirstPathModel.material_action

- SLO/SLA Impact: No post-confirm impact; blocks release-quality proof

- Data Risk: No data loss; typed product truth can be semantically contaminated

- Security/Compliance: Privacy, accessibility, compliance, policy, and safety are not directly affected; the failure is semantic product-truth contamination before confirmation.

- Invariant Violated: Material action must preserve the accepted action while excluding automated or host actor identity from product truth.

- Root Cause: The recent material-action preference path concatenates any recognized actor with its action, including automated actors.

- Solution: Centralize automated-actor detection and return the action clause alone for automated actor prefixes while preserving human actor action ownership.

- Rollback/Forward Fix: Forward fix only; do not weaken first-path semantic or pre-confirm quality gates.

- Verification: Run the focused first-path regression, nonhuman clarification cases, and the full runtime shard matrix.

- Prevention: Keep automated actor classification in the shared actor-term owner and test human versus automated material-action rendering.

- Agent Guardrails: Do not add host-name exceptions or repair rendered artifacts; fix the shared typed first-path parser.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_first_path_semantics.py
- src/odylith/runtime/domain_intelligence/greenfield_actor_terms.py
