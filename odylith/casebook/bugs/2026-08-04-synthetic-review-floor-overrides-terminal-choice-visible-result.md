- Bug ID: CB-309

- Status: FixedPendingRelease

- Created: 2026-08-04

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: A temporal compare-before-select first path parses the terminal selection correctly, but semantic reconciliation replaces it with a broad action-history phrase generated for the synthetic three-event proof floor.

- Impact: Generated Project and governance surfaces can present the action history as the visible result instead of the user's selected outcome.

- Components Affected: domain-intelligence

- Environment(s): Odylith 0.1.15 source-local canonical validation at commit 3e650ce0f

- Detected By: Fresh-process canonical pytest shard 17 and isolated replay

- Failure Signature: Expected the terminal selected outcome; received the full compared-options clause ending in the selection.

- Trigger Path: Build a Greenfield semantic model from a first path shaped as compare several inputs before choosing one plan.

- Ownership: Greenfield first-path visible-result reconciliation

- Timeline: Detected after 3,199 prior shard tests passed; reproduced as the only shard-17 failure and in an isolated process.

- Blast Radius: Greenfield paths whose terminal choice follows a temporal comparison or preparation clause.

- SLO/SLA Impact: Blocks the semantic release floor and Project comprehension gate.

- Data Risk: No source bytes are lost, but the canonical visible result is semantically widened.

- Security/Compliance: No direct security exposure; review and audit meaning can be misleading.

- Invariant Violated: Synthetic event-floor prose must never outrank a source-derived terminal visible outcome.

- Root Cause: The three-event floor wraps an older broad outcome in a synthetic review event, and reconciliation treats that terminal wrapper as stronger than the parsed terminal choice already entailed by a prior event.

- Solution: When the terminal event is a synthetic wrapper around the current broad value, promote the parsed source result only when a prior real event both entails it and owns a typed choose/select action, including its finite and participial forms. Otherwise preserve the existing result. This keeps the repair structural and prevents shorter conditional or review phrases from gaining priority merely because they are shorter.

- Rollback/Forward Fix: Forward fix in the pre-confirm semantic compiler only; no post-confirm repair.

- Verification: The temporal-choice, finite-action, and conditional-outcome regressions passed together; the full 38-test semantic-model/provenance group passed; all 131 pre-confirm slop regressions passed; and all 10 cross-domain confirmed-body tests passed. The clean canonical shard suite remains the release re-entry gate.

- Prevention: Keep synthetic event-floor rows explicitly subordinate to source-derived semantic outcomes.

- Agent Guardrails: Do not fix this with domain words or by globally preferring every shorter phrase.

- Preflight Checks: Require zero semantic-model regressions before rebuilding the distribution.

- Regression Tests Added: Extend the temporal-choice regression to assert visible result and synthetic-event non-authority.

- Monitoring Updates: Release proof continues to report visible-result drift as a hard semantic failure.

- Version/Build: 0.1.15 branch 2026/freedom/v0.1.15

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_semantic_model.py
- tests/unit/runtime/test_greenfield_preconfirm_slop_regressions.py
