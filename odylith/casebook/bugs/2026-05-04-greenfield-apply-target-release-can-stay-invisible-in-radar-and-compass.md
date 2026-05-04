- Bug ID: CB-166

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-04

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Greenfield apply target release can stay invisible in Radar and Compass

- Impact: Operators applying a confirmed greenfield proposal can get backlog and wave records without a visible target release lane, so Radar and Compass fail to show the release-planning power promised by the proposal.

- Components Affected: domain-intelligence

- Environment(s): Consumer greenfield apply flow and generated Radar/Compass surfaces in v0.1.14 post-release hardening.

- Detected By: Operator screenshot from 2026-05-04 showing Compass with touched workstreams but no visible Release Targets after greenfield apply.

- Failure Signature: Greenfield creates workstreams and program waves, but the default 0.0.1 release target is not surfaced as Target Release in Radar or Release Targets in Compass.

- Trigger Path: Run odylith greenfield apply for a confirmed proposal without an explicit release selector, then refresh/open odylith/index.html?tab=radar or tab=compass.

- Ownership: Greenfield domain intelligence release targeting, release-planning aliases, and Compass release-target visibility.

- Timeline: Captured 2026-05-04 through `odylith bug capture`.

- Blast Radius: New consumer greenfield projects and any proposal-first repo where the first target release should be visible immediately after apply.

- SLO/SLA Impact: No runtime outage; release-planning UX and first-run governance demonstration are materially degraded.

- Data Risk: No data loss; risk is missing or hidden governance truth that makes release targeting look absent.

- Security/Compliance: No direct security impact.

- Invariant Violated: Confirmed greenfield apply must create a concrete first target release, assign first-wave workstreams, and make that target visible in Radar and Compass without extra manual repair.

- Root Cause: Greenfield ensured the 0.0.1 selector but did not mark it as the current target release when no current alias existed, and Compass hid explicit release groups with members whenever a current or next alias was present.

- Solution: Alias the first greenfield release as current when no current alias exists, keep the 0.0.1 selector, and let Compass show explicit release groups with targeted workstreams even when current or next aliases exist.

- Rollback/Forward Fix: Forward fix in v0.1.14 post-release fixes; existing consumers can rerun upgrade/migration or release targeting refresh to pick up generated surface behavior.

- Verification: Greenfield apply unit proof asserts 0.0.1 and current aliases point at the generated first release and that B-001/B-002 are active release workstreams; Compass shell/render tests assert member-bearing release groups remain visible; bundle mirror and browser tests cover generated assets.

- Prevention: Keep Greenfield release alias proof and Compass release visibility tests so default 0.0.1 target releases cannot become invisible again.

- Agent Guardrails: When changing greenfield apply, prove release registry aliases, assignment events, Radar/Compass generated visibility, and first-wave workstream targeting together.

- Preflight Checks: Search existing release-planning and greenfield Casebook records before capture; verify release planning through view model rather than only checking files exist.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_bootstraps_first_release_selector; tests/unit/runtime/test_compass_dashboard_shell.py; tests/unit/runtime/test_render_compass_dashboard.py

- Monitoring Updates: Watch consumer greenfield Compass screenshots for Release Targets and Radar summary/workstream release chips after apply.

- Version/Build: v0.1.14 post-release fixes branch

- Config/Flags: Default greenfield release selector 0.0.1; no feature flag.

- Customer Comms: Release note should state that greenfield apply now surfaces the first 0.0.1 target release in Radar and Compass.

- Related Incidents/Bugs: CB-160, CB-165

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.14

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_proposals.py
- src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js
