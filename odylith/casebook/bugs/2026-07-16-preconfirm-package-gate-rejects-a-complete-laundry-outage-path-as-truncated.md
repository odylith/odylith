- Bug ID: CB-257

- Status: Open

- Created: 2026-07-16

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The installed 240-case campaign rejects the laundry-room-outage-queue request before confirmation because the typed package artifact gate reports that the greenfield scope boundary truncates the accepted first-path tail. The strict gate correctly prevents a broken transaction from reaching CONFIRM, but the accepted path is materially complete and should compile.

- Impact: A complete consumer utility request is blocked before the normal CONFIRM, EDIT, REJECT rail.

- Components Affected: domain-intelligence

- Environment(s): Fresh installed 0.1.15 seeded 240-case high-variance discovery campaign.

- Detected By: Installed campaign fail-fast cluster.

- Failure Signature: manifest.legacy-package-artifact-gate.typed-package-artifact-gate.preconfirm-package: greenfield scope boundary truncates the accepted first-path tail

- Trigger Path: laundry-room-outage-queue from tests/fixtures/greenfield-volume/consumer-creative-community.v1.json through bin/greenfield-matrix-campaign.

- Ownership: Domain Intelligence typed package artifact gate and accepted first-path scope projection.

- Timeline: Captured 2026-07-16 from installed 240-case discovery after one successful consumer case.

- Blast Radius: Long first-path prompts whose final branches carry a valid visible outcome, recovery path, or bounded maintenance action.

- SLO/SLA Impact: Pre-confirm compilation fails for otherwise usable prompts, delaying deterministic confirmation.

- Data Risk: No write occurred; transaction creation was not started and rollback guard remained enabled.

- Security/Compliance: No security or compliance impact.

- Invariant Violated: The complete accepted first path must survive into the sealed package before confirmation, or the compiler must repair it without burdening the user.

- Root Cause: The accepted first path compiles to six typed events. Scope compaction gave exactly six steps a 320-character budget, which emitted the first five actions but dropped the terminal maintenance repair closure. The scope helper then consulted its raw-path outcome, which was an earlier water-leak statement rather than the reconciled semantic visible result, so it did not restore the missing repair closure. The strict package gate correctly rejected the mismatch.

- Solution: Give exactly six-step scope boundaries the existing 420-character terminal-completion budget. Keep the typed package gate fail-closed; it must continue to reject a scope boundary that omits a material accepted tail.

- Verification: The named unit regression passes the public judgment gate with the complete laundry scope tail. The final fresh installed failed-subset replay passed `laundry-room-outage-queue` at 10/10 with no quality issues, a commit-only transaction, and a clean rollback guard; resume the 240-case discovery campaign.

- Prevention: Compare accepted first-path source, scope projection, typed tail events, and sealed package before classifying a tail as truncated. Exercise paths with exactly six steps, because their terminal action can fall between the short and long scope budgets.

- Agent Guardrails: Do not weaken the typed package gate or move scope repair after CONFIRM.

- Preflight Checks: No packaged transaction may drop a material accepted first-path branch before its visible outcome or recovery boundary.

- Regression Tests Added: `test_scope_fragment_preserves_six_step_laundry_repair_tail` asserts the terminal repair action remains in the scope boundary and the public package judgment gate accepts the complete path. A fresh installed failed-subset replay remains required before closure.

- Monitoring Updates: Track the package-gate fingerprint and affected path stressors in Compass.

- Version/Build: 0.1.15 local distribution built from the current 2026/freedom/v0.1.15 working tree.

- Config/Flags: GREENFIELD_MATRIX_REQUIRE_HIGH_VARIANCE_STRESSORS=1; seeded discovery; stop after one failure cluster.

- Customer Comms: No customer communication; no governed records were written.

- Related Incidents/Bugs: CB-255, CB-256

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_first_path_common.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_project_brief.py
- src/odylith/runtime/artifact_quality/greenfield_project_judgment.py

- Runbook References: - odylith/MAINTAINER_RELEASE_RUNBOOK.md
