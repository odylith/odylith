- Bug ID: CB-154

- Status: FixedPendingRelease

- Created: 2026-05-02

- Fixed: Pending

- Severity: P2

- Reproducibility: Always

- Type: UX

- Description: When Compass skipped or failed a fresh standup narration pass, the dashboard could replace the Standup Brief body with a large warning card. Operators lost the last validated brief exactly when the better UX was to keep the previous brief visible and move the provider/retry status into the existing header status banner.

- Impact: Compass made provider-skip or provider-failure state look like the primary brief content, reducing operator trust in the Standup Brief surface.

- Components Affected: compass

- Environment(s): Odylith product repo Compass dashboard on the v0.1.13 maintainer branch.

- Detected By: Operator screenshot of the Compass Standup Brief panel showing a large provider-skip warning card.

- Failure Signature: Standup Brief body rendered provider-status copy such as skipped_not_worth_calling or invalid_batch/Brief needs another provider pass instead of the previous validated brief sections.

- Trigger Path: Open Compass with a ready cached standup brief whose provider_decision is skipped_not_worth_calling, or with a provider failure/retry state such as provider_error or invalid_batch after a previous ready brief exists.

- Ownership: Compass runtime and dashboard renderer.

- Timeline: Captured 2026-05-02 through `odylith bug capture`; refreshed 2026-05-04 after operator screenshot showed invalid_batch/Brief needs another provider pass still occupying the Standup Brief body.

- Blast Radius: Compass Standup Brief users when provider narration is skipped for non-material fact churn or fails during a retryable narration pass.

- SLO/SLA Impact: No data loss; UX trust degradation in dashboard review.

- Data Risk: None

- Security/Compliance: None

- Invariant Violated: Provider-spend warnings must not displace the last validated standup brief when a replayable brief is available.

- Root Cause: The skipped_not_worth_calling and retryable provider-failure paths produced unavailable/status-style briefs and the runtime patcher could overwrite a ready brief slot instead of preserving the last usable narrative with a header-status notice.

- Solution: Reuse the last validated or alternate ready brief when the selected brief fails, preserve same-window ready global and scoped briefs during provider failure patching, suppress body notices for status-only provider failures, and surface provider/retry text through the header status banner as a warning.

- Rollback/Forward Fix: Forward fix in v0.1.13.

- Verification: Focused unit tests, Compass render tests, full browser smoke, Compass regression matrix, and browser deep/layout/UX/filter audits.

- Prevention: Keep browser and runtime regressions that assert skipped/failure narration notices appear in the header status banner while the brief body retains rendered sections whenever a last ready brief exists.

- Agent Guardrails: Do not replace a useful live brief with a provider-spend explanation card; status belongs in status surfaces.

- Preflight Checks: Confirm Type, Status, Fixed, and Reproducibility are compact tokens before refreshing Casebook.

- Regression Tests Added: tests/integration/runtime/test_surface_browser_smoke.py::test_compass_skipped_narration_notice_uses_header_status_not_brief_body, tests/integration/runtime/test_surface_browser_smoke.py::test_compass_failed_global_brief_uses_header_status_and_previous_brief, tests/integration/runtime/test_surface_browser_smoke.py::test_compass_failed_same_window_brief_uses_header_status_and_keeps_last_ready_body, tests/unit/runtime/test_compass_standup_brief_maintenance.py::test_stamp_request_runtime_input_fingerprint_keeps_ready_brief_on_provider_failure, and tests/unit/runtime/test_compass_standup_brief_batch.py::test_build_brief_bundle_skips_provider_for_nonwinner_summary_churn

- Monitoring Updates: Compass browser regression coverage now checks this state.

- Version/Build: 0.1.13

- Config/Flags: No feature flag.

- Customer Comms: Internal maintainer fix pending v0.1.13 release.

- Related Incidents/Bugs: CB-020

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.13

- Public Response: pending

- Code References: - src/odylith/runtime/surfaces/compass_standup_brief_batch.py
- src/odylith/runtime/surfaces/compass_standup_brief_runtime_patch.py
- src/odylith/runtime/surfaces/templates/compass_dashboard/compass-shared.v1.js
- src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js
- src/odylith/runtime/surfaces/templates/compass_dashboard/compass-summary.v1.js
- tests/integration/runtime/test_surface_browser_smoke.py
