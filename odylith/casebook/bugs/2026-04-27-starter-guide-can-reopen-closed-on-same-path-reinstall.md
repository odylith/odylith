- Bug ID: CB-131

- Status: Closed

- Created: 2026-04-27

- Fixed: 2026-04-27

- Severity: P1

- Reproducibility: Consistent

- Type: UX regression

- Description: A fresh consumer install can show only the bottom-right Starter Guide recovery pill when the browser still has a dismissal bit from an older install at the same filesystem path. The guide markup is present, but the shell dismissal key did not include an install-instance token, so the old browser key matched the new first-run shape.

- Impact: First install can hide onboarding, making Odylith look empty or broken at the exact moment a new user needs guidance.

- Components Affected: dashboard

- Environment(s): Consumer dashboard first-run shell, file-served or static-served index.html, same repo path reused after reinstall.

- Detected By: Operator screenshot of /Users/freedom/mock/mockrepo/odylith/index.html showing Compass with only the Starter Guide recovery pill.

- Failure Signature: #shellWelcomeState is hidden and #welcomeReopen is visible on first install because odylith.welcome.dismissed:<pathname>:welcome-v2|... matched stale browser storage.

- Trigger Path: Install or reinstall Odylith into a repo path where the browser previously dismissed the same welcome-v2 onboarding shape, then open odylith/index.html.

- Ownership: Dashboard shell first-run onboarding

- Timeline: Captured 2026-04-27 through `odylith bug capture`.

- Blast Radius: Any consumer repo opened in a browser profile that previously dismissed Odylith onboarding at the same path.

- SLO/SLA Impact: Early-adoption UX and branding trust regression; no runtime data loss.

- Data Risk: No data risk.

- Security/Compliance: No security impact.

- Invariant Violated: A fresh install must open with first-run onboarding visible unless the current install instance itself was dismissed.

- Root Cause: The welcome dismissal storage key was scoped to browser pathname plus onboarding shape, but not to the install instance or installed timestamp.

- Solution: Include the active install version and installed_utc token in the welcome dismiss key so stale same-path dismissals do not suppress a fresh install, while reloads inside one install still respect dismissal.

- Rollback/Forward Fix: Forward fix in shell_onboarding dismiss-key generation and browser regression coverage.

- Verification: PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_shell_onboarding.py tests/unit/runtime/test_render_tooling_dashboard.py; PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py -k 'first_install_launchpad_reopens_after_same_path_reinstall or first_install_launchpad'

- Prevention: Keep same-path reinstall browser coverage in the onboarding suite and preserve install-instance scoping in the dismissal contract.

- Agent Guardrails: Do not treat first-run onboarding as optional chrome; verify visible state in a real browser when dashboard first-run behavior changes.

- Preflight Checks: Render shell and run browser onboarding regression before release.

- Regression Tests Added: tests/unit/runtime/test_shell_onboarding.py::test_build_welcome_state_dismiss_key_changes_when_install_instance_changes; tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py::test_first_install_launchpad_reopens_after_same_path_reinstall

- Monitoring Updates: None.

- Version/Build: 0.1.12

- Config/Flags: Default dashboard shell onboarding.

- Customer Comms: No external customer comms yet; fix before 0.1.12 adoption push.

- Code References: - src/odylith/runtime/surfaces/shell_onboarding.py
- tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py
