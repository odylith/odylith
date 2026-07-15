- Bug ID: CB-240

- Status: Open

- Created: 2026-07-11

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The installed 240-case campaign started the create latency timer before compile-transaction, then reported the combined compile-plus-create duration as a post-confirm create failure. Three cases exceeded 60 seconds under six workers even though their post-confirm manifests reported commit-only execution under 0.2 seconds.

- Impact: Release proof falsely claims post-confirm determinism or latency failure and blocks volume discovery even when the sealed commit path succeeds within budget.

- Components Affected: odylith

- Environment(s): Maintainer local-release v0.1.15 95e787539, 240-case discovery with six workers

- Detected By: Fresh installed 240-case campaign

- Failure Signature: post-confirm create exceeded 60s: 69.496s; manifest whole_project_elapsed_seconds: 0.148

- Trigger Path: greenfield-matrix-campaign 240-case-discovery using GREENFIELD_MATRIX_DEEP_VOLUME_MAX_WORKERS=6

- Ownership: Installed greenfield post-confirm matrix timing boundary

- Timeline: Captured 2026-07-11 through `odylith bug capture`.

- Blast Radius: All concurrent volume and release proofs can misclassify pre-confirm compilation latency as a post-confirm commit failure.

- SLO/SLA Impact: Creates false red release gates and hides the actual performance boundary that should be optimized or explained before confirm.

- Data Risk: No data loss or privacy exposure observed; evidence attribution and release readiness are incorrect.

- Security/Compliance: No direct security exposure observed.

- Invariant Violated: The post-confirm latency gate must measure only hash-verified commit, readback, and refresh work; pre-confirm compilation must be measured separately.

- Root Cause: _run_compiled_greenfield_create started its timer before invoking compile-transaction and returned the combined elapsed duration as create_seconds to the post-confirm quality gate.

- Solution: Start the post-confirm timer only after compilation returns a transaction hash, and add a regression with a slow compile and fast commit.

- Rollback/Forward Fix: Forward fix only. Do not relax the post-confirm budget or conceal a genuine commit-only latency regression.

- Verification: Focused matrix timing regression, full installed matrix unit suite, exact failed-subset replay, and resumed volume discovery.

- Prevention: Keep pre-confirm compile and post-confirm commit telemetry distinct in every release proof harness.

- Agent Guardrails: Never use a combined compile-and-create timer to claim post-confirm failure; inspect the sealed manifest duration before attributing a breach.

- Preflight Checks: Run the commit-only timing regression before any concurrent volume campaign.

- Regression Tests Added: test_compiled_greenfield_create_times_commit_only_phase

- Monitoring Updates: Record pre-confirm compile and post-confirm create timing independently in campaign evidence.

- Version/Build: 0.1.15 local-release 95e787539

- Config/Flags: GREENFIELD_MATRIX_DEEP_VOLUME_MAX_WORKERS=6; stop after 3 failures

- Customer Comms: Internal maintainer evidence only until resumed installed proof passes.

- Related Incidents/Bugs: CB-239, CB-222

- GitHub Status: fixed_pending_release

- Public Response: pending

- Code References: - scripts/release/greenfield_preconfirm_matrix.py
- tests/unit/install/test_greenfield_preconfirm_matrix.py
