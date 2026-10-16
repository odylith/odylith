- Bug ID: CB-307

- Status: Open

- Created: 2026-08-03

- Severity: P2

- Reproducibility: Consistent

- Type: UX

- Description: Confirmed-create tests rendered a temporary committed Project dashboard and invoked the operating-system browser, exposing pytest repository paths as unsolicited tabs. Interactive completion was applied without an automation boundary.

- Impact: Automated runs interrupted the operator with unsolicited browser tabs and made temporary pytest artifacts look like random product pages.

- Components Affected: domain-intelligence

- Environment(s): Odylith maintainer source-local pytest execution on macOS

- Detected By: Operator observed a pytest-generated odylith/index.html tab during the canonical source suite

- Failure Signature: greenfield_post_confirm_handoff.open_committed_dashboard called webbrowser.open without checking automation or CI posture

- Trigger Path: Run a confirmed Greenfield create test whose completion handoff resolves a committed dashboard

- Ownership: Greenfield completion handoff and shared runtime environment policy

- Timeline: Captured 2026-08-03 through `odylith bug capture`.

- Blast Radius: All automated confirmed-create paths on desktop hosts where webbrowser.open can launch a browser

- SLO/SLA Impact: Operational delivery risk: disruptive test side effects invalidate unattended release proof, although transaction integrity and product SLOs are unaffected.

- Data Risk: No governed-data loss risk; only a temporary repository path was displayed.

- Security/Compliance: Security posture: no credential or access exposure was observed. Compliance, privacy, accessibility, and safety posture are unchanged, but automated tests must not invoke ambient desktop applications.

- Invariant Violated: Automated validation may render browser surfaces for proof but must never open operator desktop tabs

- Root Cause: The completion handoff treated every non-JSON invocation as interactive and had no shared environment-policy guard before webbrowser.open.

- Solution: Centralize environment flag parsing, honor ODYLITH_NO_BROWSER plus standard CI flags before browser launch, and set ODYLITH_NO_BROWSER automatically for pytest.

- Rollback/Forward Fix: Forward fix only; preserve interactive dashboard opening while suppressing automation side effects.

- Verification: Five focused handoff/browser tests passed, including the automation opt-out regression; an actual confirmed-create test passed in 22.79 seconds with browser launch disabled.

- Prevention: Keep browser launch behind the shared automation-aware environment guard and retain the autouse pytest opt-out fixture.

- Agent Guardrails: Never run broad automated Greenfield suites without ODYLITH_NO_BROWSER; browser rendering proof and desktop launch are separate contracts.

- Preflight Checks: Verify ODYLITH_NO_BROWSER or CI posture before any test lane capable of completing Greenfield creation.

- Regression Tests Added: test_greenfield_completion_respects_automated_browser_opt_out plus explicit interactive-open tests that clear the automation flag

- Monitoring Updates: No runtime monitor required; deterministic test coverage owns this boundary.

- Version/Build: 0.1.15 source-local

- Config/Flags: ODYLITH_NO_BROWSER=1 under pytest; CI/GITHUB_ACTIONS/BUILD_BUILDID also suppress launch

- Customer Comms: Operator was told the test-triggered pages were unintended and the suite was stopped immediately.

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_post_confirm_handoff.py
- src/odylith/runtime/common/environment.py
- tests/conftest.py

- Fix Commit/PR: ff192d454
