- Bug ID: CB-299

- Status: Open

- Created: 2026-07-30

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The pre-confirm semantic slop gate treated the noun modifier support in Lab Support Owner as an action clause. A valid quantum communication lab proposal then failed before transaction creation.

- Impact: A valid detailed onboarding prompt could stop before confirmation with no governed package.

- Components Affected: domain-intelligence

- Environment(s): Installed v0.1.15 release matrix

- Detected By: Installed pre-confirm matrix

- Failure Signature: semantic slop: action clause leaked into actor label lab support owner

- Trigger Path: greenfield create --confirm for the quantum communication lab matrix case

- Ownership: Greenfield domain-intelligence pre-confirm quality boundary

- Timeline: Captured 2026-07-30 through `odylith bug capture`.

- Blast Radius: Any actor label with a verb-like modifier before a valid role suffix.

- SLO/SLA Impact: Release matrix fails closed before governed writes.

- Data Risk: No data risk: the transaction remains uncommitted.

- Security/Compliance: Compliance assessed: no policy, privacy, accessibility, or safety impact because the gate stops before any write.

- Invariant Violated: Quality gates must reject malformed actor labels without rejecting valid human roles.

- Root Cause: The embedded-action detector accepted any verb-like token without recognizing a role-bearing terminal label.

- Solution: Skip embedded-action detection when the actor label ends in a recognized role; retain dangling-relation and malformed-label checks.

- Verification: Focused semantic-quality tests and the final 14-case installed matrix passed, including quantum communication lab.

- Prevention: Keep paired tests for malformed action-bearing labels and valid role-ending labels.

- Agent Guardrails: Do not accept a matrix score as proof until generated actor labels are inspected and both false-positive and false-negative cases are covered.

- Preflight Checks: Run actor-label quality tests before the installed matrix.

- Regression Tests Added: test_generated_semantic_slop_gate_rejects_malformed_actor_labels and test_generated_semantic_slop_gate_keeps_role_ending_actor_labels.

- Version/Build: 0.1.15 local release proof

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_semantic_quality.py
- tests/unit/runtime/test_greenfield_preconfirm_quality_repairs.py
