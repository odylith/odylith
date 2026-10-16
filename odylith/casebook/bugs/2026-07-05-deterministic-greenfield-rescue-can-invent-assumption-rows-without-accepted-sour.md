- Bug ID: CB-218

- Status: Open

- Created: 2026-07-05

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: A deterministic post-confirm rescue fallback could synthesize generic assumption rows when ArtifactPlanIR.assumptions was empty, while its ledger claimed unsupported assumptions were rejected. That can turn a missing source fact into generated governance truth instead of failing closed or asking the host planner for a structured patch.

- Impact: Repairable greenfield quality failures can be masked by invented assumption content, weakening semantic custody and scientific artifact trust even when governed writes succeed.

- Components Affected: domain-intelligence

- Environment(s): Odylith maintainer worktree during greenfield post-confirm rescue hardening before release dist rebuild.

- Detected By: Read-only release-readiness reviewer and focused source-level regression probe.

- Failure Signature: _assumptions_patch_value returned ASM-001: The first release records evidence only and a synthesized review-only assumption for a proposal that only carried a proof boundary and no accepted assumptions.

- Trigger Path: Greenfield post-confirm quality-lens repair for proposal.assumptions with an empty ArtifactPlanIR assumption source.

- Ownership: Domain Intelligence post-confirm rescue planner and ArtifactPlanIR assumption patch custody.

- Timeline: Captured on 2026-07-05 after reviewer falsified the deterministic assumptions rescue behavior during the 0.1.15 greenfield release checkpoint.

- Blast Radius: Any greenfield create whose final quality lens targets assumption coverage while the accepted intent carries no explicit assumption rows.

- SLO/SLA Impact: No direct latency breach; rescue can appear to progress while semantic custody is wrong.

- Data Risk: Low data-loss risk; high governance-trust risk because generated records may contain unsupported assumptions.

- Security/Compliance: Security posture: no direct exploit path or secret exposure observed. Compliance and safety posture is weakened if unsupported assumptions influence proof boundaries, safety review, or release readiness.

- Invariant Violated: Post-confirm repair must patch sanctioned semantic or artifact-plan facts from accepted source evidence; it must not invent assumption rows to satisfy a quality gate.

- Root Cause: The deterministic fallback treated proof-boundary presence as enough to fabricate an assumption patch and used a generic evidence-only assumption when the proposal had no accepted assumption source rows.

- Solution: Change deterministic assumption rescue to return no source patch when accepted assumptions are absent, add tests that prevent invented assumptions, and keep host-planned structured repair or fail-closed blocker behavior for unsupported assumption gaps.

- Rollback/Forward Fix: Forward fix only; do not weaken quality gates or hand-edit generated proposals.

- Verification: Focused source tests must cover missing-assumption refusal, no generic boundary insertion without source boundary, assumption metadata preservation, and executable PatchSet gating before rebuilt installed proof.

- Prevention: Treat assumption repair as source-fact custody, not filler prose. Existing assumption rows may be clarified; absent assumption rows are not a license to synthesize governance truth.

- Agent Guardrails: Before adding deterministic rescue fallbacks, prove the replacement fact is grounded in accepted intent or existing ArtifactPlanIR rows; otherwise fail closed or route to structured host planning.

- Preflight Checks: Search Casebook for prior structured-rescue and replacement_fact failures; run focused post-confirm PatchSet and artifact-plan executor tests.

- Regression Tests Added: tests/unit/runtime/test_greenfield_preconfirm_patch_payload.py covers missing-assumption refusal; tests/unit/runtime/test_greenfield_artifact_plan_patch_executor.py preserves assumption metadata by id; tests/unit/runtime/test_greenfield_preconfirm_executable_patchset.py guards executable PatchSet semantics.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_preconfirm_rescue_planner.py
- src/odylith/runtime/domain_intelligence/greenfield_artifact_plan_patch_executor.py
- tests/unit/runtime/test_greenfield_preconfirm_patch_payload.py
- tests/unit/runtime/test_greenfield_artifact_plan_patch_executor.py
