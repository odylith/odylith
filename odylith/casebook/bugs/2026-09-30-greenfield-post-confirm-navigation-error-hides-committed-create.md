- Bug ID: CB-352

- Status: FixedPendingRelease

- Fixed: 2026-09-30

- Created: 2026-09-30

- Severity: P1

- Reproducibility: Consistent

- Type: UX

- Description: After the exact sealed Greenfield create commits and the journal closes, a post-confirm navigation exception escapes the host decision handler. The operator sees failure even though the governed project and dashboard were published.

- Impact: A successful create can be reported as failed, misleading the operator into retrying or doubting the committed state.

- Components Affected: domain-intelligence

- Environment(s): Odylith 0.1.15 maintainer source-local injected-fault test on macOS

- Detected By: Read-only transaction gate audit with an injected RuntimeError in post_confirm_navigation

- Failure Signature: handle_greenfield_decision raises RuntimeError after create-journal state is closed and commit_result and dashboard exist

- Trigger Path: CONFIRM a sealed Greenfield transaction, then raise from post_confirm_navigation after commit

- Ownership: Greenfield host confirmation and CLI completion handoff

- Timeline: Captured 2026-09-30 through `odylith bug capture`.

- Blast Radius: Codex or CLI users whose post-commit navigation/pin step raises

- SLO/SLA Impact: Release completion truth is false despite durable publication; no transaction latency claim changes.

- Data Risk: No observed governed-data loss; risk is false failure reporting after durable write.

- Security/Compliance: No credential exposure observed; auditability requires the receipt to identify the committed outcome.

- Invariant Violated: Once the commit is durably closed, optional dashboard navigation must not turn success into a failure or trigger rollback.

- Root Cause: Post-confirm navigation executes outside the exception boundary that already handles browser-opening failure.

- Solution: Keep the committed receipt and return a truthful dashboard path and next action when navigation fails; preserve idempotent retry.

- Rollback/Forward Fix: Forward fix only; never roll back an observed committed generation.

- Verification: A real-commit injected navigation failure preserved the CLOSED response, closed journal, published dashboard, and same-hash retry. The focused fix suite passed 89/89, the wider handoff/write-set/browser-publication slice passed 112/112, and the Greenfield runtime unit suite passed 1,411/1,411. Independent read-only review found no P0/P1 in the patch. This is source-local proof; clean installed release qualification remains open.

- Prevention: Keep all optional post-commit UX calls behind a committed-outcome boundary with fault injection tests.

- Regression Tests Added: Host confirmation and create CLI fault injection for post-commit navigation, plus direct CLI browser-open failure; tests assert truthful committed output and same-hash retry.

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Related Incidents/Bugs: CB-307

- Code References: - src/odylith/runtime/surfaces/greenfield_host_confirmation.py
- src/odylith/runtime/domain_intelligence/greenfield_create_cli.py
