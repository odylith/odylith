- Bug ID: CB-108

- Status: Closed

- Created: 2026-04-12

- Fixed: 2026-04-12

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass `Programs` can regress back to a redundant nested inner
  card, rendering the repeated program-summary focus band as another rounded
  bordered panel inside the grouped outer box even after the operator
  explicitly removed that chrome. The grouped outer `Programs` container
  should own the section shell by itself; the repeated inner summary card only
  adds noise and makes the hierarchy look wrong.

- Impact: Operators lose the intended grouped-surface hierarchy in Compass.
  The same program summary reads like two stacked cards for one concept, which
  is visually noisy and makes the operator-owned `Programs` grouping feel
  unstable.

- Components Affected:
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-shared.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-waves.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-execution-waves.v1.css`,
  `tests/integration/runtime/test_surface_browser_layout_audit.py`,
  `tests/unit/runtime/test_compass_dashboard_shell.py`,
  live checked-in Compass shell assets, bundled Compass shell mirrors, and the
  `B-025` UX/browser-hardening plan.

- Environment(s): Compass `Programs` in normal desktop and compact shell
  browsing.

- Root Cause: The earlier flattening work removed the outer disclosure shell
  chrome, but the repeated program-summary band still rendered through
  `.execution-wave-focus` inside the section body. That meant the visible
  nested card lived one layer deeper than the first fix targeted, so the UI
  could still look like a card-inside-a-card even with a flat outer
  disclosure shell.

- Solution: Give the `Programs` disclosure an explicit flat-section class,
  remove the repeated `.execution-wave-focus` panel entirely from the Programs
  body path, and prove the contract in both source-level unit assertions and
  headless browser layout checks. The browser audit now fails if Programs
  renders either card shell or focus-panel markup.

- Verification:
  `python -m pytest tests/unit/runtime/test_compass_dashboard_shell.py -k 'workstream_and_registry_links_stay_cross_surface_and_without_footer_actions'`
  and
  `python -m pytest tests/integration/runtime/test_surface_browser_layout_audit.py -k 'programs_do_not_render_nested_inner_card_chrome or governance_disclosures_survive_runtime_rerender'`
  plus a clean headless Compass load showing the `Programs` section carries
  `execution-wave-section-flat` with `borderTopWidth=0px`,
  `backgroundImage=none`, and `borderRadius=0px`.

- Prevention: The Compass `Programs` disclosure must use an explicit flat
  section contract. Do not rely on outer card ancestry or generic shared
  section chrome to keep this surface flat.

- Detected By: Operator screenshot and explicit regression report on
  2026-04-12.

- Failure Signature: Compass `Programs` shows a second rounded bordered card
  inside the grouped outer box, usually as a repeated program-summary focus
  panel with the same title/copy already present in the section summary.

- Trigger Path: Shared execution-wave section styling changes, renderer
  refactors that drop the ancestor-specific override, or stale asset chains
  that serve older generic section chrome.

- Ownership: Compass execution-wave shell contract and browser-proof
  ownership under `B-025`.

- Timeline: The operator removed the redundant inner card earlier on
  2026-04-12, but the regression resurfaced later the same day. The durable
  fix moved the invariant from incidental CSS ancestry to explicit section
  markup plus browser proof.

- Blast Radius: Compass `Programs` layout in live and bundled shell assets.

- SLO/SLA Impact: No outage, but a repeated operator-facing shell regression in
  a high-visibility Compass lane.

- Data Risk: None.

- Security/Compliance: None.

- Invariant Violated: The grouped outer `Programs` box must not regrow a
  second nested card shell around the same program disclosure.

- Workaround: Reloading into a fresher asset chain may hide the symptom, but
  the contract was still weak until the Programs section owned an explicit
  flat-shell class.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Before changing Compass execution-wave section chrome,
  inspect this bug, `CB-080`, and the active `B-025` plan. Do not reintroduce
  nested card chrome for `Programs`, and do not implement Programs flattening
  through outer-card ancestry alone.

- Preflight Checks: Confirm the Programs disclosure emits
  `execution-wave-section-flat`, confirm the flat class owns zero border,
  background, and radius, confirm the Programs section renders no
  `.execution-wave-focus` node at all, and rerun desktop plus compact browser
  proof for the Programs section.

- Regression Tests Added:
  `tests/unit/runtime/test_compass_dashboard_shell.py`,
  `tests/integration/runtime/test_surface_browser_layout_audit.py`

- Monitoring Updates: Keep the browser layout audit asserting the explicit flat
  class plus zero border/background/radius on the Programs section.

- Related Incidents/Bugs:
  [2026-04-09-shared-surface-contract-drift-reopens-workstream-button-and-release-layout-regressions.md](2026-04-09-shared-surface-contract-drift-reopens-workstream-button-and-release-layout-regressions.md)

- Version/Build: Odylith product repo working tree on 2026-04-12.

- Config/Flags: Standard Compass shell browsing; no special flags required.

- Customer Comms: Tell operators the grouped outer `Programs` section is the
  only intended card shell; the product now treats that as an explicit
  contract and will fail browser proof if the inner card returns.

- Code References:
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-shared.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-waves.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-execution-waves.v1.css`,
  `tests/unit/runtime/test_compass_dashboard_shell.py`,
  `tests/integration/runtime/test_surface_browser_layout_audit.py`

- Runbook References:
  `odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`,
  `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: Pending.
