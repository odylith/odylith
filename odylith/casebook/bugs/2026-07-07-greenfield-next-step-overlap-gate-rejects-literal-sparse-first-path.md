- Bug ID: CB-221

- Status: Open

- Created: 2026-07-07

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Installed greenfield replay reached post-confirm package validation and failed before governed writes because the operator next-step overlap gate rejected an implementation prompt that literally preserved the accepted first path. The accepted path was intentionally generic after sparse intent normalization, while the contrastive semantic overlap signature collapsed source terms to gerunds that did not overlap the finite verbs in the prompt.

- Impact: Users can confirm sparse or heavily normalized product intent and still receive a post-confirm create failure before Radar, Registry, Atlas, and project records are written.

- Components Affected: domain-intelligence

- Environment(s): Maintainer installed local-release v0.1.15 dist c3274ff5 on 2026-07-07

- Detected By: Installed greenfield failed-subset replay under /private/tmp/odv120-c3274ff5-word-sense-replay

- Failure Signature: operator next-steps implementation prompt must overlap the accepted first path; manifest.legacy-package-artifact-gate.typed-package-artifact-gate.post-confirm-package; create_returncode=2; no governed records written

- Trigger Path: greenfield propose -> confirmed-intent.md -> greenfield create --confirm --release 0.0.1 through greenfield_matrix_campaign_runner.py failed-subset replay

- Ownership: Domain Intelligence next-steps preview package gate and first-path preservation overlap metric

- Timeline: Captured 2026-07-07 through `odylith bug capture`.

- Blast Radius: Sparse, vague, edited, or normalized greenfield intents whose accepted first path is generic but literally preserved in the next-step implementation prompt.

- SLO/SLA Impact: Violates the non-negotiable post-confirm success invariant and blocks release matrix readiness.

- Data Risk: No private-data exposure observed; risk is no governed records and user-facing post-confirm failure.

- Security/Compliance: No direct security exposure observed; regulated or scientific productization handoff can be blocked before proof artifacts are written.

- Invariant Violated: After confirmation, package validation must not reject an implementation prompt that literally preserves the accepted first path.

- Root Cause: The next-step overlap gate reused contrastive semantic-drift token signatures for literal preservation. Generic sparse accepted paths collapse under contrastive stopword filtering, so finite verbs in the implementation prompt can score zero overlap even when the exact accepted first path is present.

- Solution: Add a literal first-path preservation fast path over the accepted `raw_path` before falling back to semantic overlap; keep visible-result-only, mutation-only, omission, and substitution failures gated.

- Rollback/Forward Fix: Forward fix only. Do not patch generated projects, weaken post-confirm quality gates, or ask the user for another confirmation after a compiler false negative.

- Verification: Focused unit regression plus exact installed failed-subset replay for /private/tmp/odv120-c3274ff5-word-sense-replay/failed-subset-replay/failed-subset-001.cases.json against the rebuilt local release.

- Prevention: Keep literal-preservation checks separate from contrastive drift metrics and add sparse-path regressions for finite verb versus gerund morphology.

- Agent Guardrails: When post-confirm fails after confirmed intent, treat it as a platform/compiler bug unless there is a true IO or environment failure; do not route it back to user clarification.

- Preflight Checks: Run focused next-step package tests and exact installed failed-subset replay before resuming volume or release-proof campaigns.

- Regression Tests Added: tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py::test_operator_next_steps_accept_literal_sparse_first_path_preservation; tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py::test_operator_next_steps_reject_visible_result_only_first_path_fragment; tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py::test_operator_next_steps_reject_mutation_only_first_path_fragment

- Monitoring Updates: Track this signature in failed-subset replay clustering before release readiness.

- Version/Build: 0.1.15 local-release c3274ff5 failure; fixed by pending follow-up commit

- Config/Flags: Provider-free installed matrix replay; failed-subset max workers 1; stop after first failure

- Customer Comms: Internal maintainer evidence only until fixed release proof passes.

- Related Incidents/Bugs: CB-209, CB-219, CB-220, B-142

- GitHub Status: needs_info

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_post_confirm_completion.py
- tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py
