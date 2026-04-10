- Bug ID: CB-083

- Status: Closed

- Created: 2026-04-09

- Fixed: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Interactive `B-###` workstream buttons across product surfaces
  did not share one destination contract. Compass `Current Workstreams` had
  already been corrected to open Radar, but `Release Targets`,
  execution-wave member chips, and timeline workstream chips could still route
  back into Compass-local scope views instead of the canonical Radar
  workstream route. That made the same workstream button mean different things
  depending on which surface rendered it.

- Impact: Operators could click the same-looking `B-###` control and land in a
  local Compass scope on one surface or Radar on another. That reopened the
  same cross-surface confusion and made workstream navigation feel unstable.

- Components Affected:
  `src/odylith/runtime/surfaces/dashboard_shell_links.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-shared.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-waves.v1.js`,
  `src/odylith/runtime/surfaces/render_casebook_dashboard.py`,
  `src/odylith/runtime/surfaces/render_mermaid_catalog.py`,
  and the cross-surface browser route-proof lane.

- Environment(s): Odylith product shell surfaces in normal maintainer browsing,
  especially Compass `Current Workstreams`, Compass `Release Targets`,
  Compass execution waves, Compass timeline, Atlas workstream pills, and
  Registry workstream chips.

- Root Cause: Workstream-button destination semantics were not enforced as one
  shared contract. Dashboard owned the canonical shell route semantics, but
  Compass still kept local `compassScopeHref(...)` and timeline-scope helpers
  for some interactive `B-###` chips. Browser proof only covered part of the
  surface set, so release, execution-wave, and timeline regressions could ship
  even after `Current Workstreams` was corrected.

- Solution: Centralize Compass workstream-button routing through one shared
  `radarWorkstreamHref(...)` helper, route Radar plan links through the same
  helper, align server-rendered workstream routes with Dashboard's shared
  shell-link helper where practical, and expand browser proof so representative
  `B-###` controls in Compass, Atlas, and Registry must land on
  `tab=radar&workstream=B-###`.

- Verification: `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_dashboard_shell_links.py
  tests/unit/runtime/test_compass_dashboard_shell.py
  tests/unit/runtime/test_render_mermaid_catalog.py
  tests/unit/runtime/test_render_casebook_dashboard.py`
  passed; `PYTHONPATH=src python3 -m pytest -q
  tests/integration/runtime/test_surface_browser_ux_audit.py -k
  'registry_detail_action_chip_audit_round_trips_cleanly or
  atlas_surface_links_and_context_pills_round_trip_cleanly or
  compass_cross_surface_links_round_trip_cleanly'` passed; `git diff --check`
  passed after the fix.

- Prevention: Interactive `B-###` workstream controls across product surfaces
  are one governed navigation contract. They open Radar. Local Compass scoping
  remains row-selection and disclosure state, not the destination of those
  buttons. Browser proof must click representative workstream controls in
  Compass current/release/execution-wave views plus Atlas and Registry before
  shipping route-contract changes.

- Detected By: Operator screenshot and explicit correction on 2026-04-09 after
  the `Current Release` card fix regressed back to a `v0.1.11` shell and the
  neighboring workstream controls still behaved inconsistently.

- Failure Signature: Clicking a `B-###` button in Compass `Release Targets`,
  Compass execution waves, or Compass timeline lands on
  `tab=compass&scope=B-###` instead of `tab=radar&workstream=B-###`.

- Trigger Path: Open Compass and click a workstream chip rendered from
  release-member, execution-wave-member, or timeline workstream lists.

- Ownership: Dashboard shell-link contract, Compass shell frontend contract,
  and cross-surface browser route proof for shared workstream controls.

- Timeline: Individual surfaces already had some correct Radar routes, but the
  route semantics were still split across local helpers. On 2026-04-09 the
  remaining Compass-local scope paths were removed and the shared route memory
  plus browser proof were widened.

- Blast Radius: Compass workstream navigation, Atlas and Registry route-truth
  expectations, future shell link refactors, and operator trust in cross-surface
  workstream controls.

- SLO/SLA Impact: No outage, but repeated operator-navigation drift in the
  primary governed surfaces.

- Data Risk: None.

- Security/Compliance: None.

- Invariant Violated: Shared interactive `B-###` workstream buttons across the
  product must deep-link to Radar's canonical workstream route.

- Workaround: Manually switch to the Radar tab or rewrite the shell URL.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not use Compass-local scope URLs for shared interactive
  `B-###` controls. If a button represents a workstream entity rather than an
  in-surface expand/collapse action, the destination is Radar. Treat local
  scope changes as a separate interaction with separate controls.

- Preflight Checks: Click representative `B-###` controls in Compass current
  workstreams, Compass release targets, Compass execution waves, Atlas, and
  Registry; verify the shell lands on Radar with the correct `workstream`
  query. Inspect the active B-025 plan and Dashboard/Compass/Radar specs
  before changing workstream-link semantics again.

- Regression Tests Added:
  `tests/unit/runtime/test_dashboard_shell_links.py`,
  `tests/unit/runtime/test_compass_dashboard_shell.py`,
  `tests/integration/runtime/test_surface_browser_ux_audit.py`

- Monitoring Updates: None.

- Related Incidents/Bugs:
  [2026-04-09-shared-surface-contract-drift-reopens-workstream-button-and-release-layout-regressions.md](2026-04-09-shared-surface-contract-drift-reopens-workstream-button-and-release-layout-regressions.md)
  [2026-04-06-radar-topology-deep-links-fall-through-to-stale-filtered-selection-and-browser-proof-misses-disclosure-gated-routes.md](2026-04-06-radar-topology-deep-links-fall-through-to-stale-filtered-selection-and-browser-proof-misses-disclosure-gated-routes.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Shared shell surfaces in normal maintainer browsing; no special
  runtime flags required.

- Customer Comms: None. This is repo-local product memory and operator
  contract hardening.

- Code References:
  `src/odylith/runtime/surfaces/dashboard_shell_links.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-shared.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-waves.v1.js`,
  `tests/integration/runtime/test_surface_browser_ux_audit.py`

- Runbook References:
  `odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`,
  `odylith/registry/source/components/dashboard/CURRENT_SPEC.md`,
  `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/registry/source/components/radar/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: Pending.
