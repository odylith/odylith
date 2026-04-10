- Bug ID: CB-092

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass Timeline Audit could show a transaction headline that
  clearly anchored on one workstream, while the visible chip row underneath
  omitted that same workstream. On 2026-04-09 this surfaced as a checkpoint
  card headed by `B-071` while the chips showed only `B-001`, `B-003`,
  `B-004`, `B-025`, and `B-027`.

- Impact: The card could say what the most important fix was, then visually
  bury that same fix in the supporting workstream pills. That makes Timeline
  Audit harder to trust because the strongest scope signal does not stay
  visible where the operator expects to click.

- Components Affected: `src/odylith/runtime/surfaces/compass_transaction_runtime.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-timeline.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`,
  `tests/unit/runtime/test_compass_transaction_runtime.py`,
  `tests/integration/runtime/test_surface_browser_deep.py`, Compass component
  spec, `B-025`, and `B-071`.

- Environment(s): Odylith product-repo maintainer mode, bundled Compass
  surface, and any Timeline Audit transaction whose headline or checkpoint text
  names a primary workstream while the raw linked-workstream list is longer
  than the visible chip budget.

- Root Cause: Compass had split priority logic. The timeline headline and
  narrative could infer an anchor workstream from checkpoint text like
  `Captured B-071 checkpoint`, but the chip row was still built from the raw
  linked-workstream array, then trimmed to five visible pills. That let the
  anchor workstream exist in the payload narrative while disappearing from the
  visible chip row.

- Solution: Carry ordered inferred workstreams into the transaction payload
  itself, not just the narrative path. Summary- or context-mentioned
  workstream ids now lead both transaction-level and nested-event workstream
  arrays, with broader linked scopes appended after them. The Timeline Audit
  chip renderer also treats the transaction's primary inferred workstream as
  the visible anchor, so the headline scope stays present and first in the
  chip row.

- Verification: `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_compass_transaction_runtime.py
  tests/unit/runtime/test_render_compass_dashboard.py
  tests/unit/runtime/test_compass_dashboard_runtime.py`
  passed (`59 passed`). `PYTHONPATH=src python3 -m pytest -q
  tests/integration/runtime/test_surface_browser_deep.py -k
  'checkpoint_anchor_workstream or compass_scope_window_and_detail_behavior_in_compact_viewport or compass_quiet_catalog_scope_reports_quiet_window_instead_of_missing_brief'`
  passed (`3 passed`). `env PYTHONPATH=src /usr/bin/time -p python3 -m odylith.cli compass refresh --repo-root . --wait`
  passed with bounded refresh (`elapsed_seconds: 0.9`, `real 1.49`).

- Prevention: Timeline Audit must keep its strongest scope signal visible. If a
  transaction headline, checkpoint, or primary narrative anchors on a
  workstream, the visible chip row must include that workstream and put it
  first before any broader linked scope list is trimmed.

- Detected By: User review of a live Compass timeline card headed by `B-071`
  whose visible workstream pills did not include `B-071`.

- Failure Signature: A Timeline Audit card headline or checkpoint narrative
  names one workstream, but the visible workstream chips omit it because other
  linked scopes consumed the visible chip budget first.

- Trigger Path: 1. Capture or render a transaction whose checkpoint or summary
  names `B-###` in text. 2. Attach a broader linked-workstream list with more
  items than the visible chip budget. 3. Open Compass Timeline Audit and
  inspect the first card.

- Ownership: Compass transaction payload ordering, Timeline Audit chip
  prominence, and browser proof for anchor-scope visibility.

- Timeline: This surfaced during the same cross-surface focus and low-signal
  cleanup that introduced `B-071`. Earlier fixes made the right scope visible
  in headlines and narratives, but the visual chip row was still using older
  ordering rules.

- Blast Radius: Any Timeline Audit card whose inferred anchor scope is not also
  first in the raw linked-workstream list can hide its own primary fix from the
  visible chip row.

- SLO/SLA Impact: No outage, but a direct operator-priority regression in the
  core execution audit surface.

- Data Risk: Low source-truth corruption risk; medium operator-readout
  integrity risk.

- Security/Compliance: None directly.

- Invariant Violated: Compass Timeline Audit must not headline one workstream
  while hiding that same anchor scope from the visible chip row.

- Workaround: Read the headline and expanded narrative instead of trusting the
  visible chip row. That is not acceptable product behavior.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not let raw linked-scope arrays outrank the transaction's
  own explicit anchor scope. If the headline, checkpoint text, or primary
  narrative names a workstream, carry it through into visible chip ordering.

- Preflight Checks: Inspect
  `src/odylith/runtime/surfaces/compass_transaction_runtime.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-timeline.v1.js`,
  and `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`
  before changing Timeline Audit prominence rules.

- Regression Tests Added: `tests/unit/runtime/test_compass_transaction_runtime.py`,
  `tests/integration/runtime/test_surface_browser_deep.py`.

- Monitoring Updates: Watch for any Timeline Audit transaction whose visible
  headline mentions `B-###` while the first visible chip row omits that same
  token.

- Residual Risk: Very broad transactions can still carry many linked scopes,
  but the primary anchor scope now stays present and first instead of getting
  trimmed away.

- Related Incidents/Bugs:
  [2026-04-09-compass-scoped-selector-can-advertise-unverified-window-activity-and-leak-global-audit-cards.md](2026-04-09-compass-scoped-selector-can-advertise-unverified-window-activity-and-leak-global-audit-cards.md)
  [2026-04-09-low-signal-governance-churn-can-outrank-real-execution-across-governance-surfaces.md](2026-04-09-low-signal-governance-churn-can-outrank-real-execution-across-governance-surfaces.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Default Compass Timeline Audit behavior; no special flag
  required.

- Customer Comms: Tell operators that Timeline Audit now keeps the card's
  anchor workstream visible and first in the chip row, so the most important
  fix stays clickable instead of getting buried by broader linked scopes.

- Code References: `src/odylith/runtime/surfaces/compass_transaction_runtime.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-timeline.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`

- Runbook References: `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`,
  `odylith/technical-plans/in-progress/2026-04/2026-04-09-odylith-scope-signal-ladder-cross-surface-focus-gating-and-low-signal-suppression.md`

- Fix Commit/PR: Pending.
