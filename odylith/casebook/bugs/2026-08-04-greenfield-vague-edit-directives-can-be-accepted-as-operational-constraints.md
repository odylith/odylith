- Bug ID: CB-318

- Status: FixedPendingRelease

- Created: 2026-08-04

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: Plain-language EDIT evidence containing only, keep, or preserve could fall through additive boundary recovery. Requests such as Only change the actor name or Preserve the existing flow and add a calendar sync returned a rebuilt intent while leaving the first path unchanged and storing the request as an operational constraint.

- Impact: The user can believe an EDIT changed the reviewed transaction even though the requested mutation was silently dropped.

- Components Affected: domain-intelligence

- Environment(s): v0.1.15 source-local pre-confirm Greenfield materialization

- Detected By: Bounded adversarial review and direct function repro

- Failure Signature: Vague mutation directive returns success, preserves the prior first path, and appends the directive to operational_constraints.

- Trigger Path: Greenfield EDIT rebuild with an unsupported add, change, rename, replace, update, remove, only, keep, or preserve instruction.

- Ownership: Domain Intelligence EDIT evidence materialization

- Timeline: Captured 2026-08-04 through `odylith bug capture`.

- Blast Radius: Greenfield users correcting actor, path, dependency, or integration meaning in plain language.

- SLO/SLA Impact: Trust and completion risk before confirmation; post-confirm commit-only behavior remains intact.

- Data Risk: No committed data loss in the repro, but the rebuilt transaction can omit the requested correction.

- Security/Compliance: Policy and safety risk: a dropped boundary or dependency correction can produce an inaccurate reviewed package.

- Invariant Violated: EDIT must either rebuild the requested semantic fact or ask one focused question; it may never report success after discarding the requested mutation.

- Root Cause: Additive boundary fallback matched broad keep, preserve, and only tokens without first rejecting unsupported mutation directives.

- Solution: Reject additive fallback when a clause contains unsupported add, change, correct, remove, rename, replace, or update language unless that clause also states a concrete hard boundary.

- Verification: Two adversarial vague EDIT regressions now raise a focused correction question with zero staged Greenfield files; valid additive boundary and unchanged-path regressions still pass.

- Prevention: Keep mutation-intent detection ahead of additive boundary recovery and test both accepted and rejected EDIT shapes.

- Agent Guardrails: Never convert an unexecuted user correction into an assumption or operational constraint merely to avoid clarification.

- Regression Tests Added: tests/unit/runtime/test_greenfield_final_holdout_regressions.py::test_vague_edit_directives_require_a_concrete_correction

- Related Incidents/Bugs: CB-315, CB-316

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py
