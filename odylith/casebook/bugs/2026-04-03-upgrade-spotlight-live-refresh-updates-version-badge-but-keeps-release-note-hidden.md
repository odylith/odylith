- Bug ID: CB-051

- Status: Open

- Created: 2026-04-03

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The consumer upgrade browser path can auto-refresh the shell
  strongly enough to swap the toolbar version label to the newly activated
  runtime, but still leave the upgrade spotlight hidden in the same page load.
  The release payload is present and the version badge proves the new runtime
  won, yet the operator never sees the intended post-upgrade release note
  moment.

- Impact: This breaks the core release UX that `B-030` was meant to harden.
  An incremental upgrade can look technically successful while silently losing
  the release announcement, which weakens the operator handoff, undermines the
  popup-to-note contract, and blocks end-to-end release validation in the
  browser proof lane.

- Components Affected: `src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js`,
  `src/odylith/runtime/surfaces/shell_onboarding.py`, upgrade spotlight
  dismissal/reopen contract, shell live-refresh browser path,
  `tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`.

- Environment(s): Consumer lane incremental upgrade flow, repo-local shell
  auto-refresh after a new release spotlight payload is written, headless
  browser validation during release prep.

- Root Cause: Current evidence shows the render path producing a valid upgrade
  spotlight payload for the new version, but the browser boot path can still
  land with `#shellUpgradeSpotlight` hidden after the shell auto-refresh. The
  version label and the spotlight visibility are therefore not staying in lock
  step across the same live refresh transition, which points to a client-side
  spotlight state or dismissal-state bug rather than a missing release payload.

- Solution: Make the live shell refresh path fail closed on spotlight
  visibility. If the shell reload detects a new upgrade spotlight payload for
  the current version pair, the refreshed page must reopen the spotlight unless
  the same version-scoped payload was explicitly dismissed in the new session.
  The browser proof lane should lock the version badge and spotlight together
  so a future refactor cannot update one without the other.

- Verification: `make dev-validate` on 2026-04-03 failed exactly one test:
  `tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py::test_open_shell_auto_reloads_after_dashboard_refresh_and_updates_version_label`.
  The failure proved `.toolbar-version` advanced to `v1.2.3` while
  `#shellUpgradeSpotlight` remained hidden. A focused local payload check in
  detached `source-local` also confirmed `build_release_spotlight(...)`
  returned a non-empty payload with `show: True`, current `recorded_utc`, and a
  future `expires_utc`.

- Prevention: Treat version-label refresh and release-spotlight visibility as
  one upgrade invariant, not two loosely related UI effects. Any browser path
  that proves a new upgraded version is visible must also prove the
  version-scoped spotlight behavior for the same page load.

- Detected By: Maintainer release-prep validation on 2026-04-03 while running
  the detached `source-local` `make dev-validate` lane after the `v0.1.7`
  release-surface and browser-regression fixes landed.

- Failure Signature: `page.wait_for_function(... 'v1.2.3' ...)` succeeds, but
  `page.locator("#shellUpgradeSpotlight").wait_for(...)` times out because the
  element remains present with `hidden=""` and `aria-hidden="true"`.

- Trigger Path: Start on a shell page with `v1.2.2` and no spotlight, write a
  real incremental upgrade state plus a `1.2.2 -> 1.2.3` spotlight payload,
  rerender the shell, let the browser auto-refresh, and observe the refreshed
  page.

- Ownership: Consumer upgrade spotlight UX, shell live-refresh browser
  contract, release-note first-paint guarantee.

- Timeline: The broader `B-030` upgrade spotlight slice already shipped
  dismiss/reopen behavior, separate release-note rendering, and browser proof
  for direct upgrade flows. During 2026-04-03 release prep, the fuller
  auto-refresh regression path exposed that one specific browser transition can
  still surface the new version badge without actually reopening the spotlight.

- Blast Radius: Incremental upgrade UX, release popup trust, browser proof for
  `B-030`, and any public release candidate that depends on the popup contract
  to explain what changed immediately after activation.

- SLO/SLA Impact: No runtime outage, but a release-surface regression on a
  first-impression product path.

- Data Risk: None.

- Security/Compliance: None directly.

- Invariant Violated: When the shell auto-refreshes onto a newly activated
  Odylith version with a valid upgrade spotlight payload, the operator must see
  the version-scoped release spotlight unless they explicitly dismissed that
  same payload.

- Workaround: Open the generated release-note page directly after upgrade or do
  a manual page reload, but neither restores the promised automatic
  post-upgrade spotlight contract.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not paper over this by deleting the spotlight or by
  weakening the browser proof. Fix the visibility contract so the browser shows
  the release note honestly on the real refresh path.

- Preflight Checks: Inspect `B-030`, the release spotlight payload in
  `shell_onboarding.py`, the client-side spotlight boot path in `control.js`,
  and the browser regression in
  `tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
  before changing upgrade refresh behavior.

- Regression Tests Added: Pending.

- Monitoring Updates: Keep the focused browser upgrade auto-refresh path in the
  detached maintainer validation lane until the spotlight and version badge are
  proven together again.

- Residual Risk: The direct upgrade and reopen flows can still look healthy
  while this one live refresh transition stays broken, so release polish can
  appear done before the real browser contract is actually safe.

- Related Incidents/Bugs:
  [2026-03-30-odylith-consumer-upgrade-release-spotlight-and-shell-refresh.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-03/2026-03-30-odylith-consumer-upgrade-release-spotlight-and-shell-refresh.md)
  [2026-04-01-product-repo-tooling-shell-hides-runtime-version-badge.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-01-product-repo-tooling-shell-hides-runtime-version-badge.md)

- Version/Build: `v0.1.7` release-prep pass in detached `source-local` on
  2026-04-03.

- Config/Flags: Consumer upgrade spotlight payload present, shell auto-refresh,
  release-note page generation enabled, detached maintainer `make dev-validate`
  browser lane.

- Customer Comms: Do not claim the release popup path is fully closed until
  the live auto-refresh transition shows the release note reliably again.

- Code References: `src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js`,
  `src/odylith/runtime/surfaces/shell_onboarding.py`,
  `src/odylith/runtime/surfaces/render_tooling_dashboard.py`,
  `tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Fix Commit/PR: Pending.
