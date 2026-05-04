- Bug ID: CB-164

- Status: FixedPendingRelease

- Fixed: Pending

- Fixed In: 0.1.14

- Created: 2026-05-04

- Severity: P2

- Reproducibility: Always

- Type: UX

- Description: In a project folder that is intentionally not a Git repository, the tooling dashboard repeatedly opened an Odylith Notice modal on refresh with the Git missing warning. The notice was non-actionable for greenfield or scratch folders and made the shell feel broken even though Odylith can operate in reduced repo-intelligence mode without interrupting the user.

- Impact: Operators in non-Git project folders get an interrupting notice on every dashboard refresh instead of staying in the normal shell workflow.

- Components Affected: dashboard

- Environment(s): Consumer lane or dogfood shell opened in an Odylith-installed folder without a .git directory.

- Detected By: Operator screenshot from 2026-05-04 showing the repeated Odylith Notice modal with Git missing.

- Failure Signature: Dashboard renders Odylith needs attention in this repository with Git missing and repo intelligence stays reduced until this folder is backed by Git.

- Trigger Path: Open or refresh odylith/index.html in an installed project folder that does not contain .git.

- Ownership: Tooling dashboard welcome/onboarding surface and shell notice payload generation.

- Timeline: Captured 2026-05-04 through `odylith bug capture`.

- Blast Radius: All installed non-Git folders, including greenfield, scratch, extracted, or local-only project workspaces.

- SLO/SLA Impact: No data-plane outage, but repeated modal interruption degrades first-run and refresh UX.

- Data Risk: No source data loss; risk is misleading durable UI state and user habituation to warnings.

- Security/Compliance: No security exposure; warning removal must not weaken actionable legacy-upgrade notices.

- Invariant Violated: Non-actionable environmental limitations must not render as blocking attention notices on every refresh.

- Root Cause: shell_onboarding._welcome_notices converted absence of .git into a warning notice, and the dashboard presenter rendered any notice while show=false as a compact modal.

- Solution: Remove the Git-missing warning from welcome notices while preserving actionable legacy-upgrade notices.

- Rollback/Forward Fix: Forward fix in v0.1.14; no consumer source migration needed because the notice is generated from runtime shell payload logic.

- Verification: `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_shell_onboarding.py tests/unit/runtime/test_render_tooling_dashboard.py::test_render_tooling_dashboard_hides_welcome_state_once_truth_exists tests/unit/runtime/test_render_tooling_dashboard.py::test_render_tooling_dashboard_shows_compact_legacy_upgrade_notice` (`17 passed`); `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py::test_first_install_launchpad_hides_git_notice_and_keeps_mental_model_visible` (`1 passed`); `./.odylith/bin/odylith casebook validate --repo-root .` passed.

- Prevention: Keep welcome notices reserved for actionable conditions, not passive capability limitations.

- Agent Guardrails: Do not convert missing Git into a modal warning when working in greenfield or non-repository folders.

- Preflight Checks: Search existing Casebook bugs for Git missing notice before capture; validate Casebook after writing.

- Regression Tests Added: tests/unit/runtime/test_shell_onboarding.py and tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py

- Monitoring Updates: Casebook regression coverage plus browser layout test for non-Git first install.

- Version/Build: v0.1.14 development branch

- Config/Flags: No config flag; behavior removed from product default.

- Customer Comms: No public incident required; release note can mention reduced non-Git notice noise.

- GitHub Status: needs_info

- Public Response: pending

- Code References: - src/odylith/runtime/surfaces/shell_onboarding.py
