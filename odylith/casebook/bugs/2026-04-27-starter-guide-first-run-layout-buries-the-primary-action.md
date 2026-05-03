- Bug ID: CB-132

- Type: UX








- Status: Closed

- Created: 2026-04-27

- Fixed: 2026-04-27

- Severity: P1

- Reproducibility: Always


- Description: Starter Guide first-run layout buries the primary action

- Impact: New operators can see a full-screen first-run guide that feels like a brochure instead of an actionable product handoff, weakening trust at install time.

- Components Affected: dashboard

- Environment(s): 0.1.12 consumer dashboard first-run shell, including Git-missing mock repos opened from odylith/index.html.

- Detected By: Operator screenshot of the Starter Guide showing oversized hero copy, a separated Git warning, and a partially clipped surface explainer section.

- Failure Signature: Starter Guide opens but the first action and Odylith mental model compete with a two-column hero layout, generic quick steps, and low-density surface cards.

- Trigger Path: Install Odylith into a consumer repo, open odylith/index.html, and view the first-run Starter Guide.

- Ownership: Dashboard shell first-run onboarding

- Timeline: Captured 2026-04-27 through `odylith bug capture`.

- Blast Radius: First-time consumer repo onboarding in Codex, Claude Code, and browser-opened local shell flows.

- SLO/SLA Impact: Early-adoption trust and activation quality regress; users may abandon before running the intended show prompt.

- Data Risk: No user data mutation risk; generated dashboard and browser-local onboarding state only.

- Security/Compliance: No direct security impact.

- Invariant Violated: First-run onboarding must make one primary action obvious, teach the repo mental model in the first view, and keep warnings compact and close to the decision they affect.

- Root Cause: The launchpad carried a marketing-style split hero with viewport-scaled type and no desktop regression for the Git-missing first-run layout.

- Solution: Reworked the Starter Guide into a compact guided panel with a status header, one prominent prompt card, a short what-happens-next list, compact top notice placement, and a five-surface mental model that fits in the first desktop view.

- Rollback/Forward Fix: Forward fix in dashboard welcome presenter, onboarding state copy, shell CSS, generated shell artifacts, and browser layout regression coverage.

- Verification: PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_shell_onboarding.py tests/unit/runtime/test_render_tooling_dashboard.py; PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py -k 'first_install_launchpad'

- Prevention: Keep browser assertions for first-run desktop clarity, Git-missing notice placement, and mental-model visibility.

- Agent Guardrails: Do not treat first-run branding complaints as cosmetic; prove the rendered shell in browser and keep the first action visible before surface education.

- Preflight Checks: Run focused unit and browser onboarding tests before 0.1.12 release proof.

- Regression Tests Added: tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py::test_first_install_launchpad_keeps_git_notice_and_mental_model_visible plus updated first-install launchpad layout assertions.

- Monitoring Updates: No runtime monitoring change; covered by browser regression tests.

- Version/Build: 0.1.12

- Config/Flags: Default dashboard shell onboarding.

- Customer Comms: No external customer comms yet; release note should mention the cleaner first-run Starter Guide.

- Related Incidents/Bugs: CB-131

- Code References: - src/odylith/runtime/surfaces/tooling_dashboard_welcome_presenter.py
- src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css
- tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py
