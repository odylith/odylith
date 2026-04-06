- Bug ID: CB-025

- Status: Closed

- Created: 2026-04-01

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: In the Odylith product repo, the tooling shell computed
  `shell_version_label` and self-host posture correctly, but the frozen header
  template no longer rendered any visible runtime/version badge. Maintainers
  could switch into detached `source-local` and lose the top-right runtime tag
  that should make pinned dogfood versus detached dev posture obvious.

- Impact: Product-repo dashboard users could not verify the active maintainer
  lane from the shell header. That weakened the self-host posture contract and
  made detached `source-local` sessions look visually identical to pinned
  dogfood in the place operators glance first.

- Components Affected: `src/odylith/runtime/surfaces/render_tooling_dashboard.py`,
  `src/odylith/runtime/surfaces/tooling_dashboard_template_context.py`,
  `src/odylith/runtime/surfaces/templates/tooling_dashboard/page.html.j2`,
  `src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css`,
  dashboard header contract.

- Environment(s): Odylith product repo maintainer checkout in pinned dogfood or
  detached `source-local` posture.

- Root Cause: The lane-boundary hardening slice froze the dashboard header
  contract after the visible runtime badge had already been dropped. The shell
  kept populating `shell_version_label`, but the template never rendered it, so
  the payload signal stopped reaching the product surface.

- Solution: Restore one compact product-repo runtime/version badge as an
  explicit part of the frozen header contract, keep it hidden for consumer
  repos, and format detached product-repo state as `source-local (pin vX.Y.Z)`
  so the pin stays visible during maintainer dev posture.

- Verification: Focused dashboard rendering, template-context, and frozen
  header-contract tests pass, and the product-repo shell render now emits the
  expected top-right badge for both pinned and detached source-local posture.

- Prevention: Treat the product-repo runtime badge as part of the frozen header
  contract, not as optional shell polish. Any future header freeze or refactor
  must prove that the badge still renders for product-repo self-host posture.

- Detected By: Maintainer local verification immediately after switching this
  repo into detached `source-local`.

- Failure Signature: The tooling shell payload carried `shell_version_label`,
  but `odylith/index.html` had no `.toolbar-version` element and the top-right
  header showed only the tab row.

- Trigger Path: Product-repo maintainer lane switch followed by shell open.

- Ownership: Dashboard header contract and self-host surface clarity.

- Timeline: Self-host posture work added the payload-level truth in `B-004`,
  then the header-freeze work in `B-027` locked the template without preserving
  a visible product-repo badge.

- Blast Radius: Product-repo maintainers, release-proof posture checks, and any
  shell-driven debugging of pinned versus detached self-host state.

- SLO/SLA Impact: Maintainer observability regression only.

- Data Risk: None.

- Security/Compliance: None.

- Invariant Violated: The product repo must surface its live self-host posture
  clearly enough that pinned dogfood and detached `source-local` do not look
  identical in the main shell.

- Workaround: Read `odylith version --repo-root .` from the CLI. That bypasses
  the broken shell affordance but does not restore the promised in-product
  signal.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not reintroduce broad header churn. Keep the fix scoped
  to one compact product-repo runtime badge and preserve the fail-closed header
  contract checks.

- Preflight Checks: Inspect `B-027`, the dashboard component spec, and the
  frozen header contract before changing shell header behavior again.

- Regression Tests Added: `tests/unit/runtime/test_render_tooling_dashboard.py`,
  `tests/unit/runtime/test_tooling_dashboard_template_context.py`

- Monitoring Updates: None.

- Related Incidents/Bugs:
  `2026-03-27-odylith-self-hosting-posture-hardening.md`,
  `2026-03-29-compass-live-self-host-risk-was-hidden-by-utc-date-and-kpi-omission.md`

- Version/Build: `v0.1.6` product repo maintainer surface.

- Config/Flags: detached `source-local` maintainer lane, tooling shell render.

- Customer Comms: None. This is a product-repo maintainer surface regression.

- Code References: `src/odylith/runtime/surfaces/render_tooling_dashboard.py`,
  `src/odylith/runtime/surfaces/tooling_dashboard_template_context.py`,
  `src/odylith/runtime/surfaces/templates/tooling_dashboard/page.html.j2`,
  `src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Fix Commit/PR: Pending.
