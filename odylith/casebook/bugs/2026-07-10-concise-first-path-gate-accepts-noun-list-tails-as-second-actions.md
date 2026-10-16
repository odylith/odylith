- Bug ID: CB-235

- Status: Open

- Created: 2026-07-10

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: The concise first-path completeness helper accepted a noun-list tail because a word ending in s after and was treated as a coordinated action. This could allow a one-step capture list to avoid required first-path completion before transaction compilation.

- Impact: Consumer-utility risk: a thin first path can appear complete and reduce the quality of the confirmation a user is asked to accept.

- Components Affected: odylith

- Environment(s): Source semantic regression suite.

- Detected By: Focused greenfield confirmed-intent recovery suite

- Failure Signature: reviewer capture notes, approvals, and status satisfies has_concise_coordinated_first_path

- Trigger Path: confirmed intent first-path completion and validation

- Ownership: Domain Intelligence first-path completeness

- Timeline: Captured 2026-07-10 through `odylith bug capture`.

- Blast Radius: Any comma-separated evidence noun list ending with and plus a plural noun.

- SLO/SLA Impact: Product quality and delivery risk: weak intent can advance pre-confirm validation.

- Data Risk: No data loss or privacy risk; defect is semantic admission only.

- Security/Compliance: No security, compliance, policy, accessibility, or safety impact; quality validation remains local and deterministic.

- Invariant Violated: A concise accepted first path must contain two concrete coordinated actions, not one action followed by a noun list.

- Root Cause: A suffix-based regex treated status as a finite action after and.

- Solution: Split coordinated clauses and require each trailing clause to satisfy the shared finite-action or action-clause parser.

- Rollback/Forward Fix: Forward fix only; retain fail-closed path completion rules.

- Verification: The weak noun-list regression now fails completion while valid coordinated action tests pass.

- Prevention: Use shared prose-grammar action predicates instead of suffix heuristics for coordinated paths.

- Agent Guardrails: Do not loosen first-path completion to satisfy sparse prompts; require real actor-led action progression or retain the pre-confirm block.

- Preflight Checks: Run concise first-path negative and high-variance action tests before packaging.

- Regression Tests Added: test_single_step_action_only_paths_do_not_satisfy_completion_or_validation

- Monitoring Updates: High-variance campaign records first-path quality gate outcomes before release claims.

- Version/Build: 0.1.15

- Config/Flags: Default first-path completion gate

- Customer Comms: No customer communication required; caught before release.

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_first_path_completeness.py
- tests/unit/runtime/test_greenfield_confirmed_intent_recovery.py
