- Bug ID: CB-151

- Type: UX


- Status: FixedPendingRelease

- Created: 2026-05-01

- Severity: P2

- Reproducibility: Always


- Description: The default Compass governance area showed completed execution-wave programs and shipped completed-only release history next to active release targets, making old work look current. In the same migration session, a stale browser view also showed 0.1.12 as current after 0.1.13 had become the source-truth current/next release.

- Impact: Operators lose the live-work signal in Compass because historical programs and shipped release history compete with the active target release.

- Components Affected: dashboard

- Environment(s): Odylith product repo Compass dashboard during v0.1.13 migration hardening.

- Detected By: Operator screenshot feedback on 2026-05-01.

- Failure Signature: Programs card listed B-072, B-096, B-099, and B-110 as 100% complete; Release Targets listed shipped 0.1.11 and stale-current 0.1.12 in the default view.

- Trigger Path: Open odylith/compass/compass.html or odylith/index.html?tab=compass with completed execution programs and historical release targets present.

- Ownership: Compass dashboard governance renderer.

- Timeline: 2026-05-01: operator screenshot showed old programs and past releases; source release truth confirmed 0.1.13 current/next; renderer rules were tightened. Follow-up feedback rejected the synthetic completed-program history card, so the placeholder was removed and the default live view now omits completed-only programs entirely.

- Blast Radius: Operators reading the product repo Compass dashboard during release migration or governance triage.

- SLO/SLA Impact: No runtime SLO impact; operator triage latency and release-state confidence degrade.

- Data Risk: No data loss; display classification risk only.

- Security/Compliance: None.

- Invariant Violated: Default Compass should prioritize live current work and keep completed-only governance history out of the primary live-work readout unless scoped.

- Root Cause: Release rendering kept completed_member groups visible by default, and program rendering used every execution_waves.programs row even when all waves were complete.

- Solution: Filter default release groups to current, next, active, planned, draft, or targeted-member releases; filter default program rows to live current/next/active wave programs; leave completed-only program history available through real scoped workstream drill-in instead of inventing a synthetic archive card.

- Rollback/Forward Fix: Forward fix in v0.1.13 renderer templates and regenerated Compass assets.

- Verification: Focused Compass renderer tests, focused browser governance-section checks, source-local Compass refresh, casebook validation, backlog and plan validators, and git diff --check.

- Prevention: Keep default Compass governance sections anchored to live-work visibility; require scoped drill-in for completed-only history.

- Agent Guardrails: Do not treat historical governance catalog rows as live-work evidence when explaining release or program state.

- Regression Tests Added: tests/unit/runtime/test_render_compass_dashboard.py, tests/unit/runtime/test_compass_dashboard_shell.py, and focused test_surface_browser_layout_audit.py governance checks.

- Monitoring Updates: Compass source/runtime truth still records release current/next and program catalog counts for drift diagnosis.

- Version/Build: 0.1.13 target release

- Config/Flags: None.

- Customer Comms: Internal operator feedback only.

- Related Incidents/Bugs: B-141, CB-150

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.13

- Public Response: pending

- Code References: - src/odylith/runtime/surfaces/templates/compass_dashboard/compass-waves.v1.js
- src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js
