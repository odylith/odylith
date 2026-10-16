- Bug ID: CB-253

- Status: InProgress

- Created: 2026-07-15

- Severity: P1

- Reproducibility: Always

- Type: Tooling

- Description: A fresh installed Greenfield matrix shard can complete every case successfully and emit payload status discovery-passed, but the campaign shard runner accepts only literal passed. The wrapper then marks the shard failed and emits a false failure-threshold stop.

- Impact: Release and discovery proof report a failed campaign after a successful installed user-flow replay, blocking trustworthy evidence and wasting operator time.

- Components Affected: odylith

- Environment(s): Fresh installed v0.1.15 Greenfield failed-subset discovery campaign

- Detected By: Fresh installed replay of cell-therapy-chain-of-identity

- Failure Signature: Matrix result score=10/10, create exit code=0, zero writes, and payload_status=discovery-passed, while the campaign result is status=failed with failure-threshold:1:shard.

- Trigger Path: TEMP_PARENT=/private/tmp/odylith-greenfield-replay-campaign-3bb677894 GREENFIELD_MATRIX_FAILED_CASE_FILES=/private/tmp/odylith-greenfield-replay-cases/cell-therapy.v1.json GREENFIELD_MATRIX_STOP_AFTER_FAILURES=1 GREENFIELD_MATRIX_STOP_AFTER_CLUSTER_FAILURES=1 ./bin/greenfield-matrix-campaign 0.1.15 /private/tmp/odylith-greenfield-replay-3bb677894

- Ownership: Greenfield matrix campaign shard runner

- Timeline: Captured 2026-07-15 through `odylith bug capture`.

- Blast Radius: All discovery-tier Greenfield campaigns whose completed matrix payload uses discovery-passed.

- SLO/SLA Impact: Release proof remains untrustworthy because a passed user path can be reported as failed.

- Data Risk: No consumer or governed records are changed by the defect, but evidence is falsely negative.

- Security/Compliance: No security boundary is weakened; the defect is proof classification only.

- Invariant Violated: A successful discovery matrix payload must produce a successful campaign shard and must not trigger a failure stop.

- Root Cause: ShardRunResult.passed and shard classification require payload_status equal to passed, while successful discovery matrices intentionally emit discovery-passed.

- Solution: Classify discovery-passed only for discovery-tier shards with zero failed cases and no failure clusters. Keep release-tier acceptance restricted to passed.

- Rollback/Forward Fix: Forward fix only; no product transaction was incorrectly committed.

- Verification: The campaign, shard, stale-telemetry, and preconfirm-campaign suite passed 64 tests, including the threshold path, zero-failure requirement, failure-cluster rejection, and release-tier rejection. The exact fresh installed replay cannot be repeated on this machine until enough disk is available to extract the managed context-engine feature pack.

- Prevention: Keep discovery-passed and release-passed payload statuses as explicit accepted outcomes in runner tests, with tier, zero-failure, and no-cluster assertions.

- Agent Guardrails: Do not equate proof-tier outcome labels with failure when the underlying matrix reports zero failed cases and exit code zero.

- Related Incidents/Bugs: CB-251, CB-252

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_matrix_campaign_shard_runner.py
- scripts/release/greenfield_preconfirm_matrix.py
