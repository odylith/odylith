- Bug ID: CB-331

- Status: FixedPendingRelease

- Fixed: 2026-09-08

- Fixed In: 0.1.15

- Created: 2026-09-08

- Severity: P2

- Reproducibility: Intermittent

- Type: UX

- Description: After closing Starter Guide, the shell schedules focus on its reopen button for a later animation frame. If the user focuses a child-surface search first, that callback takes focus away; insertion can be lost and the filtered-empty state never appears. Both Radar and Registry reproduce under a controlled callback schedule. An unchanged passive run also records actual focus theft after input. Historical timeout causality is not fully observed.

- Impact: First-time users can lose their first search input immediately after dismissing onboarding, leaving records visible despite attempting an unmatched search.

- Components Affected: dashboard

- Environment(s): Odylith 0.1.15 detached source-local dashboard, Chromium desktop, checkpoint ddb65494

- Detected By: Cross-surface browser timeout investigation under B-142; passive focus capture and four deterministic schedule controls

- Failure Signature: After child query focus, document.activeElement becomes welcomeReopen; insertion leaves query empty and rows unchanged, then the existing two-second filtered-empty wait expires.

- Trigger Path: Open shell on Radar or Registry, close Starter Guide, focus child search before the queued dismissal animation frame, then insert text after that frame executes.

- Ownership: Dashboard shell close/open focus ownership in templates/tooling_dashboard/control.js

- Timeline: Captured 2026-09-08 through `odylith bug capture`.

- Blast Radius: Starter Guide dismissal on child governance surfaces; upgrade spotlight uses the same deferred-focus pattern and needs preservation controls.

- SLO/SLA Impact: Blocks first-use input reliability and browser qualification; does not change Greenfield 60/90/120 generation budgets.

- Data Risk: Lost unsaved search input only in the observed path; no governed source or transaction mutation.

- Security/Compliance: No security incident observed; unexpected focus movement degrades keyboard interaction and accessibility.

- Invariant Violated: A completed shell action must not later steal focus from the user's next chosen input.

- Root Cause: Focus return is deferred by an unconditional requestAnimationFrame even though hiding the overlay and exposing its recovery control are synchronous.

- Solution: Keep focus return in the existing close/open action before subsequent user input; remove the superseded deferred-focus callbacks without changing filters, header or timeouts.

- Verification: Four controlled schedule cells pass as defect witnesses in 18.85 seconds: release after input focus loses insertion on both surfaces, release before input focus succeeds. Three passive 12-case owner runs pass but capture real focus theft. Reports and captures: /private/tmp/odylith-registry-empty-replay.Anv7ST/.

- Test Setup Learning: The first native-animation-frame regression run has four genuine Starter Guide focus failures and six invalid upgrade controls, not ten product failures. The Radar seeder created product-repository markers; shell_onboarding correctly suppresses consumer upgrade notes in a product repository. Separate that seeder's optional product markers from its governance records and assert upgrade-note eligibility before opening the browser. Preserve focus-regression-before.xml; do not weaken production eligibility or extend waits.

- Valid Red Controls: After correcting only fixture posture, all ten desktop/mobile cases fail on focus ownership in 26.14 seconds. Eight close controls lose the new Radar or Registry input focus to welcomeReopen or upgradeReopen; both upgrade-reopen controls override the newly focused release link. The native scheduler and rendered production callbacks are unchanged. Receipt: /private/tmp/odylith-registry-empty-replay.Anv7ST/focus-regression-valid-before.xml.

- Focused Repair Proof: Removing the three deferred focus callbacks makes all ten regressions and the twelve unchanged Radar/Registry empty-state cases pass: 22 passed in 60.99 seconds. The rendering, fixture-owner and frozen-header unit pack passes 86 in 1.88 seconds. Receipts: focus-and-empty-after.xml and focus-unit-after.xml under the same evidence root. Desktop screenshots show retained query and matching empty status; mobile screenshots show retained focused input, with empty details below the current viewport. Full browser and fresh bundled-render proof remain required; this is not release acceptance.

- Independent Review: The three corrections preserve synchronous visibility and focus ordering. Review found one equivalent pending owner in cheatsheet_drawer.js: opening the drawer schedules search focus and selection for the next animation frame. The parent toggle listener opens the drawer synchronously before the appended Cheatsheet listener runs. Add bounded child/drawer focus controls before deciding that owner; do not claim shell-wide removal from the first three fixes. Ordinary upgrade reopen now explicitly checks focus on Close. Welcome Escape/reopen focus behavior is unchanged and is not covered by a comprehensive accessibility claim.

- Cheatsheet Red Controls: All four child/drawer and desktop/mobile controls fail on lost focus in 9.98 seconds with the original Cheatsheet callback. Receipt: cheatsheet-focus-before.xml under the same evidence root. Remove that fourth deferred callback in its existing owner; preserve ordinary search focus, select-all on reopening, keyboard replacement, and Escape focus return.

- Combined Source Proof: All fourteen focus controls, twelve unchanged empty-state cases and three existing ordinary Cheatsheet/upgrade/storage-error controls pass in 74.16 seconds (all-focus-and-original-controls-after.xml). Independent read-only review accepts the final four-callback repair with no blocking source finding. It requests explicitly asserting retained search text before selection; that assertion is added for final proof. The two source owners now contain no delayed focus callbacks and shrink by eight lines. This structural claim excludes unrelated shell behavior and is not a full accessibility qualification.

- Retention Control Correction: The stronger retained-value assertion first fails four cases because Escape clears native HTML search input. A real-shell probe observes release becoming empty on Escape, while Close preserves release; a separate input-type-search page without product code also clears on Escape. This is not evidence against synchronous focus. The regression now checks Escape focus return separately and uses Close/reopen to prove value retention and select-all replacement. Preserve cheatsheet-focus-final.xml as the invalid retention expectation. The shell diagnostic recorded both values before a later attempt reused a page already closed by the clean-page helper; that late diagnostic error does not invalidate the recorded comparison and is not a product defect.

- Frozen Checkpoint Proof: The unchanged 3,159-file tree 61ad0f33f48b0f9cde14d675e92fd51992def91db2addae6633f47c82dcc4961 passes 4,500 runtime tests in 383.82 seconds and 1,382 unit/integration install tests in 958.44 seconds. The full browser selection passes 326 cases in 1049.05 seconds, including all fourteen focus regressions; one Radar maintainer-diagnostic case is skipped because its fixture contains no qualifying diagnostic. That skip supplies no positive coverage. The protected final-holdout regression is excluded before reads and collection. Full distribution build and canonical clean-install/upgrade/unavailable-author smoke both exit zero; the wheel contains the exact revised shell templates. Receipts, artifact hashes and scope are in /private/tmp/odylith-focus-release-proof.u1JhmF/README.md. Historical timeout causality, comprehensive accessibility, Greenfield semantic quality, native-host confirmation and 60/90/120 reliability remain separate unproved obligations. This bug is fixed in the development candidate, not released.

- Prevention: Browser regressions must choose a new input between the completed overlay action and the next animation frame, then verify focus, insertion, filtered state and recovery.

- Agent Guardrails: Do not increase timeouts, retry input, patch either filter or claim that controlled scheduling proves the exact historical failing interleaving.

- Related Incidents/Bugs: CB-305; CB-330; B-142

- Code References: src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js; src/odylith/runtime/surfaces/templates/tooling_dashboard/cheatsheet_drawer.js
