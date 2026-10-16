- Bug ID: CB-349

- Status: Open

- Created: 2026-09-30

- Severity: P2

- Reproducibility: Intermittent

- Type: Tooling

- Description: Queued Compass refresh loses source-local dependency environment

- Impact: A queued Compass refresh reports failure after a governance checkpoint even though the same refresh succeeds synchronously, making operator-facing freshness unreliable.

- Components Affected: compass

- Environment(s): Odylith product repository, detached source-local maintainer posture, 2026-09-29

- Detected By: Greenfield release-checkpoint governance refresh

- Failure Signature: Queued refresh terminal_reason=render_failed with ModuleNotFoundError: No module named 'httpx'; synchronous standalone --wait refresh passed immediately afterward.

- Trigger Path: odylith compass refresh --repo-root . followed by odylith compass refresh --repo-root . --status

- Ownership: Compass queued refresh worker runtime environment

- Timeline: Captured 2026-09-30 through `odylith bug capture`.

- Blast Radius: Queued source-local Compass refreshes; no evidence of impact on Greenfield transactions or synchronous surface sync

- SLO/SLA Impact: Governance freshness can be delayed or falsely reported failed; not a Greenfield timing result

- Data Risk: No observed data loss; prior rendered Compass state was retained

- Security/Compliance: No observed security or compliance exposure

- Invariant Violated: A queued refresh must use the same viable runtime dependency environment as a synchronous refresh

- Workaround: Run odylith compass refresh --repo-root . --runtime-mode standalone --wait; this completed successfully in 2.9 seconds

- Verification: Compare queued refresh status with synchronous standalone --wait in detached source-local posture; verify both resolve dependencies and render the same source truth

- Related Incidents/Bugs: Earlier httpx environment miss noted in CB-303, but this trigger is the queued Compass worker
