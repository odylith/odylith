- Bug ID: CB-217

- Status: FixedPendingRelease

- Created: 2026-07-02

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: An installed exact replay of the saved grn-sim confirmed intent completed post-confirm in 29.616s and committed governed records, but the independent release-matrix readback scored engineer quality 0 because model-evaluation-view/CURRENT_SPEC.md lacked the canonical Blocked input evidence proof row. This is a platform contract-custody defect, not a project-specific issue: semantic component contracts can be structurally complete while omitting the universal proof-floor row required by premium Registry evidence review.

- Impact: Post-confirm project creation succeeds, but generated governance artifacts can miss a required engineer proof contract and fail premium release-quality scoring.

- Components Affected: domain-intelligence

- Environment(s): Odylith maintainer source head 3779e4b5, local release dist odylith-local-release-0.1.15-3779e4b5, installed consumer replay against /Users/freedom/mock/grn-sim confirmed intent.

- Detected By: Installed exact grn-sim replay with release-matrix package collectors and brutal quality scoring.

- Failure Signature: Registry component spec odylith/registry/source/components/model-evaluation-view/CURRENT_SPEC.md is missing proof contract text: Blocked input evidence; engineer release-matrix lens failed.

- Trigger Path: odylith greenfield create --repo-root . --prompt 'building an AI-model that simulates gene expression prediction' --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1 --json

- Ownership: Greenfield Domain Intelligence semantic component contract and Registry spec generation.

- Timeline: 2026-07-01: exact installed replay committed records in 29.616s with complete counts; matrix readback found missing Blocked input evidence row and engineer lens failure.

- Blast Radius: Any greenfield component whose semantic contract path bypasses the generic proof-floor rows can produce a structurally complete but premium-quality-failing Registry spec.

- SLO/SLA Impact: No creation SLO breach in observed replay; quality SLO breach because premium engineer score is 0 despite a committed write.

- Data Risk: No data loss observed; governed records are written, but proof obligations can be incomplete and mislead implementation planning.

- Security/Compliance: Proof-row omission can weaken security, privacy, safety, and blocked-input review evidence where generated component specs guide implementation.

- Invariant Violated: Every generated Registry component spec must include successful-path, blocked-input, and replay proof obligations independent of domain and component profile.

- Root Cause: Semantic contract fields could be accepted as complete without a custody pass that guaranteed the universal local_proof floor survives semantic, specialized, and existing-contract paths. A second rendering-layer defect then rewrote canonical proof labels during narrative cleanup, so a recovered blocked-input row could still be normalized into generic "Input evidence" copy before the premium package scorer read it.

- Solution: Add a structured component-contract proof-floor completion helper at the contract normalization boundary, promote required successful-path, blocked-input, and replay rows before profile-specific proof rows, preserve canonical proof labels through Registry narrative rendering, and keep the release scorer strict. Also narrow completion-priority final-write debt so only typed mechanical projection-copy issues can commit as quality debt; substantive prompt, proof, semantic, release, domain-term, and quality-lens findings still roll back.

- Rollback/Forward Fix: Forward fix only; post-confirm completion-priority behavior remains correct and must not be reverted.

- Verification: Focused completion-priority custody tests passed (`tests/unit/runtime/test_greenfield_completion_priority_custody.py`, 3 passed). Focused component/narrative/post-confirm tests passed (`tests/unit/runtime/test_greenfield_component_spec_quality.py` selected proof/profile/narrative cases, `tests/unit/runtime/test_greenfield_post_confirm_engine.py` selected quality-debt/fail-closed cases, and the selected combined component/general pack). Exact source-local replay of the saved grn-sim confirmed intent completed post-confirm in 26.254s with a passed manifest, zero issues, no rescue, committed governed writes, 4 Radar workstreams, 5 Registry component specs, 6 Atlas sources, 12 rendered surface payloads, 5 project implementation prompts, and PM/architect/engineer/domain-expert lenses at 10/10. Browser proof and fresh installed dist proof remain required before release closeout.

- Prevention: Treat universal proof rows as structured contract custody, not rendered prose repair or project-specific exception. For completion-priority behavior, record non-critical projection debt durably and visibly, but never downgrade substantive semantic or engineering-quality blockers into debt.

- Agent Guardrails: Before fixing greenfield quality debt, preserve post-confirm write completion for repairable projection issues and avoid adding project-domain exceptions or regex towers.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_component_contract.py
- src/odylith/runtime/governance/component_spec_narrative.py
- src/odylith/runtime/domain_intelligence/greenfield_apply_write.py
- src/odylith/runtime/domain_intelligence/greenfield_cli_output.py
- scripts/release/greenfield_matrix_package_evidence.py
