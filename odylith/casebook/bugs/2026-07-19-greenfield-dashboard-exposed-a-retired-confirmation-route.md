- Bug ID: CB-287

- Status: Open

- Created: 2026-07-19

- Severity: P1

- Reproducibility: Always

- Type: OperatorUX

- Description: The unaccepted Project dashboard rendered Accept, Revise, and Reject action cards and asked the user to apply a proposal even though the CLI disables apply and the only valid confirmation contract is a hash-bound CONFIRM, EDIT, REJECT rail.

- Impact: Users could be directed to a nonexistent or semantically unsafe confirmation route instead of the reviewed transaction rail.

- Components Affected: dashboard

- Environment(s): Odylith project dashboard for unaccepted Greenfield proposals.

- Detected By: Independent consumer UX and materiality review

- Failure Signature: Dashboard host handoff emitted Accept it, Revise it, Reject it, and direct proposal-apply wording while greenfield apply exits with an error.

- Trigger Path: Open an unaccepted Greenfield proposal in the Project dashboard.

- Ownership: Greenfield project dashboard host handoff

- Timeline: Captured 2026-07-19 through `odylith bug capture`.

- Blast Radius: All users reviewing an unaccepted Greenfield proposal through the dashboard.

- SLO/SLA Impact: Confirmation comprehension and deterministic post-confirm behavior were undermined.

- Data Risk: No known writes occurred from the dashboard path; user decision integrity risk only.

- Security/Compliance: Security: no external security exposure. Privacy: no data collection or disclosure change. Accessibility: ambiguous action labels impaired clear command comprehension. Compliance: reviewed confirmation intent could be misrepresented.

- Invariant Violated: Every user-visible confirmation path must refer only to the canonical precompiled hash-bound CONFIRM, EDIT, REJECT contract.

- Root Cause: A legacy dashboard handoff survived after CLI apply was retired.

- Solution: Replace legacy action cards and stale instructions with one host-neutral pointer to the canonical proposal rail and explicitly name CONFIRM, EDIT, REJECT.

- Rollback/Forward Fix: Forward fix; no data migration required.

- Verification: Project intelligence tests assert obsolete accept/revise/apply copy is absent and canonical rail guidance is present.

- Prevention: Search dashboard and host-facing projections for retired confirmation vocabulary whenever the CLI confirmation contract changes.

- Agent Guardrails: Do not invent dashboard-local confirmation commands or buttons when transaction confirmation has one canonical rail.

- Preflight Checks: Run Project dashboard unit tests and rendered browser proof before release.

- Regression Tests Added: test_unaccepted_project_dashboard_handoff_uses_only_canonical_transaction_rail

- Monitoring Updates: Greenfield dashboard quality checks must reject retired confirmation vocabulary.

- Version/Build: 0.1.15 candidate

- Config/Flags: Default unaccepted proposal dashboard

- Customer Comms: Caught before release; no customer communication needed.

- GitHub Status: fixed_pending_release

- Public Response: pending

- Code References: - src/odylith/runtime/project_intelligence/greenfield.py
- src/odylith/runtime/project_intelligence/greenfield_project_text.py
