- Bug ID: CB-170

- Status: FixedPendingRelease

- Created: 2026-05-06

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: Release retargeting can corrupt prior release workstream filters

- Impact: Operators filtering Radar or Compass by prior releases can lose the historical workstream split when unrelated older workstreams are bulk-moved into the current release.

- Components Affected: release-planning

- Environment(s): Odylith product-repo maintainer mode on branch 2026/freedom/v0.1.15 with release assignment events under odylith/radar/source/releases.

- Detected By: Operator review after the target release was changed to 0.1.15 and older Radar release filters no longer showed their prior workstreams.

- Failure Signature: release-assignment-events.v1.jsonl contained broad move events at 2026-05-05T22:59:42Z through 2026-05-05T23:03:18Z that moved B-070, B-083, B-084, B-085, B-087, B-088, B-092, B-093, B-097, B-126, and B-118 through B-125 into release-0-1-15.

- Trigger Path: Change current target release to 0.1.15, then move all active release workstreams instead of only the current branch workstreams; open Radar or Compass and filter previous releases.

- Ownership: Release planning authoring, release assignment event-log discipline, Radar release filters, and Compass release target projection.

- Timeline: 2026-05-05: release-0-1-15 was made current; broad move events retargeted older workstreams; operator caught missing previous-release filters; event log was restored so release-0-1-12, release-0-1-14, and release-0-1-15 recover their intended membership.

- Blast Radius: Radar release filters, Compass release target cards, release notes, and governed release-history trust for any repo carrying older active or completed release work.

- SLO/SLA Impact: P0 governance-trust impact; no runtime outage, but primary release-planning surfaces become confidently wrong.

- Data Risk: High governance metadata risk: source-truth release history can be corrupted if old workstreams are retargeted instead of preserved.

- Security/Compliance: No direct security impact; governance auditability and release provenance are affected.

- Invariant Violated: Changing a target release or current alias must never bulk-retarget historical workstreams; only explicit current-slice workstream IDs may move.

- Root Cause: Operator-facing rule and release-planning guidance allowed target-release changes to be conflated with historical workstream retargeting.

- Solution: Remove the broad move events, keep release-0-1-15 limited to B-141 and B-142 active plus completed B-140 history, and add release-planning guidance plus tests proving alias updates do not retarget existing workstreams.

- Rollback/Forward Fix: Forward fix in v0.1.15; preserve old release assignments and refresh Radar plus Compass after correction.

- Verification: PYTHONPATH=src python - <<'PY' release-planning state check confirmed release-0-1-12 has B-070/B-083/B-084/B-085/B-087/B-088/B-092/B-093/B-097/B-126, release-0-1-14 has B-118-B-125, and release-0-1-15 has B-141/B-142; release-planning tests and backlog validation pass.

- Prevention: Treat release alias changes as selector changes only; add release-planning tests and guidance that forbid bulk retargeting older workstreams into a new current release.

- Agent Guardrails: When asked to set a target release, change only Radar/Compass release selector truth; do not move historical workstreams unless the operator explicitly names those workstream IDs.

- Preflight Checks: Before release retargeting, run release show/list and enumerate the exact workstream IDs to move; after mutation, prove the active workstream sets for the old and new releases.

- Regression Tests Added: tests/unit/runtime/test_release_planning.py::test_release_alias_update_does_not_bulk_retarget_existing_workstreams

- Monitoring Updates: Backlog validation and release state proof should report active assignment counts by release after target-release mutations.

- Version/Build: v0.1.15 branch

- Fixed In: 0.1.15

- Related Incidents/Bugs: B-141; B-142; CB-093; CB-112

- Code References: - odylith/radar/source/releases/release-assignment-events.v1.jsonl
- tests/unit/runtime/test_release_planning.py
