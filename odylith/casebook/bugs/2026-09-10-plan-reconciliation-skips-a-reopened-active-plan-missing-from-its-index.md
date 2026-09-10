- Bug ID: CB-339

- Status: InProgress

- One-Call Correction Accepted In Source (2026-09-10): Independent review first reproduces partial reconciliation on the initial registration call and a queued metadata write before table validation. The revised existing owner now prepares registration bytes and validates the complete affected batch before writes, then sends new and existing rows through the same lifecycle transition. Root's 91 maintained controls pass in 4.03 seconds; independent rereview passes 103 controls in 4.60 seconds, including all four former counterexamples. Read-only layout preparation accepts the actual B-145 row, but real application has not run: CB-305's failed Compass publication currently blocks writer admission. Do not hand-edit either index, create a successor, or report source proof as completed governance repair. Evidence: /Users/freedom/.codex/odylith-goal-recovery-20260910.wJE8mT/reconcile-integrated-root-v2.xml and /private/tmp/odylith-cb339-active-review.Zenbch/rereview-green.xml.

- End-to-End Reconciliation Gap (2026-09-10): After valid plan registration, selective sync fails because the reciprocal B-145 idea is implementation while its existing Radar index row is still finished and remains in Finished Workstreams. The existing row mover only searches Ranked Active Backlog; normalization does not relocate finished rows. No supported command currently completes this exact reconciliation. Extend that existing owner to relocate a unique row for an explicitly reciprocal active idea and correct stale execution status, with one prevalidated write. Preserve unrelated row cells, source bytes and modes, reject duplicates, malformed tables and aliases, and keep genuinely finished-idea successor behavior unchanged. Do not hand-edit the index or create a new workstream to conceal the gap.

- Accepted Bounded Proof (2026-09-10): Revised registration passes 58 focused controls including the original defect and all four independent counterexamples; renewed independent review passes 57 controls with no residual bounded finding. The canonical command then registers exactly one B-145 row in the real index, creates no successors, and a second call makes zero decisions. Real binding validation checks one touched active plan and passes; full traceability checks 26 plans and risk/mitigation checks 95 plans, both passing. Full-suite and rendered-governance qualification remain pending; no crash/concurrency guarantee is inferred from these tests.

- Independent Rejection (2026-09-10): The initial candidate passed 40 maintained controls but failed four independent synthetic controls: a pipe in a plan filename corrupts the table; duplicate reciprocal workstream metadata is accepted; an index symlink redirects the write; and a later invalid registration leaves an earlier row written. The candidate was not applied to the real plan index. The correction must validate all proposed rows and non-aliased index identity before the first write. Evidence: /private/tmp/odylith-cb339-review.TdlPwz/independent-red.xml and the same four reproduced failures in /private/tmp/odylith-populated-predecessor-proof.0JeIRw/plan-index-review-red.xml.

- Created: 2026-09-10

- Severity: P2

- Reproducibility: Always

- Type: Tooling

- Description: Reopening the existing B-145 plan under the supported in-progress directory with an explicit Backlog B-145 binding leaves it unregistered. The canonical reconciliation command exits zero with zero decisions, while the binding validator fails because the Active Plans row is missing. CLI-owned index guidance offers no supported registration command.

- Impact: Maintainers cannot complete a governed plan reopening through the advertised CLI workflow; bypassing the index owner would hide the integration gap.

- Components Affected: odylith

- Environment(s): Detached source-local bbe31214 proof checkout with B-145 reopened for published-predecessor migration assessment.

- Detected By: Actual canonical reconciliation followed by plan-workstream-binding validation.

- Failure Signature: Reconcile exits zero with decisions zero; validator reports touched active plan missing from Active Plans.

- Trigger Path: odylith governance reconcile-plan-workstream-binding --repo-root . followed by odylith validate plan-workstream-binding --repo-root .

- Ownership: Active plan registration and workstream reconciliation.

- Timeline: Captured 2026-09-10 through `odylith bug capture`.

- Blast Radius: New or reopened active plans absent from the technical-plan index; downstream governed refresh.

- SLO/SLA Impact: Blocks release assessment bookkeeping; no demonstrated Greenfield request latency change.

- Data Risk: No observed authored data loss; active work can be omitted from navigation.

- Security/Compliance: No demonstrated exploit; a repair must preserve explicit bindings and reject unsafe or conflicting registration rather than infer authority.

- Invariant Violated: The canonical governance writer must register explicitly bound active plans or report an actionable failure, not skip missing required index rows as success.

- Root Cause: The reconciliation loop continues when rows_by_plan has no entry for a touched active plan.

- Solution: Qualify a bounded registration correction in the existing owner, reusing authored plan and backlog identity; do not hand-edit the CLI-owned index.

- Verification: Reproduce with an independent private control, cover valid registration, idempotency, conflicting metadata and unsafe paths; rerun actual reopened plan validation.

- Related Incidents/Bugs: CB-104; CB-334; B-145.

- Code References: - src/odylith/runtime/governance/reconcile_plan_workstream_binding.py
