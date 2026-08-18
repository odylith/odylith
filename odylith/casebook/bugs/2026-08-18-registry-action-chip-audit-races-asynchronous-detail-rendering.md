- Bug ID: CB-345

- Status: Open

- Created: 2026-08-18

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The browser UX audit waits for the Registry list selection to become active after navigation, then immediately queries detail action chips. Registry detail rendering finishes asynchronously, so the chip may not exist yet even though the selected list button is active. Delivery risk is a false release-validation failure; the runtime domain route itself remains intact.

- Impact: Canonical dev validation fails despite the Registry route and action-chip data being valid once detail rendering settles; this blocks delivery evidence.

- Components Affected: registry

- Environment(s): Odylith maintainer source-local validation on macOS with Python 3.13 and Playwright Chromium

- Detected By: Untouched make dev-validate shard 3, then exact global-interpreter reproduction

- Failure Signature: Locator.evaluate raises missing anchor for href ../index.html?tab=radar&workstream=B-009

- Trigger Path: python3 -m pytest -q tests/integration/runtime/test_surface_browser_ux_audit.py::test_registry_detail_action_chip_audit_round_trips_cleanly

- Ownership: Registry browser UX audit synchronization

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: Registry detail action-chip browser proof and canonical maintainer validation

- SLO/SLA Impact: Blocks release validation; no runtime availability impact

- Data Risk: No persistent data is read incorrectly, mutated, or lost; the defect is confined to test timing.

- Security/Compliance: No security or compliance boundary is changed; the proof fails before navigation.

- Invariant Violated: Browser proof must wait for the user-visible detail surface it is asserting, not a different synchronously rendered selection signal.

- Root Cause: The audit waits for button[data-component].active, which is rendered before asynchronous loadDetail and renderDetail populate #detail action chips.

- Solution: Wait for the exact href-bearing detail action chip before invoking the existing click-and-route assertion.

- Rollback/Forward Fix: Forward-fix the audit synchronization only; do not change Registry production routing.

- Verification: Run the exact node and the full surface browser UX audit under global python3.

- Prevention: Browser audits must synchronize on the exact asynchronously rendered element under test.

- Agent Guardrails: Do not weaken the route assertion or add sleeps; wait on the exact typed href target.

- Preflight Checks: Reproduce under the canonical global interpreter and confirm the production action chip appears after detail settlement.

- Regression Tests Added: tests/integration/runtime/test_surface_browser_ux_audit.py::test_registry_detail_action_chip_audit_round_trips_cleanly

- Related Incidents/Bugs: CB-062

- Code References: - tests/integration/runtime/test_surface_browser_ux_audit.py
